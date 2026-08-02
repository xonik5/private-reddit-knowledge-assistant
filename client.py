"""Bounded, read-only access to a manually submitted Reddit post.

This module must not be configured or used until Reddit has explicitly approved
the application's Data API access request.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable
from urllib.parse import urlparse

import httpx


TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE_URL = "https://oauth.reddit.com"
ALLOWED_HOSTS = {
    "reddit.com",
    "www.reddit.com",
    "old.reddit.com",
    "new.reddit.com",
    "np.reddit.com",
    "redd.it",
    "www.redd.it",
}
POST_ID_RE = re.compile(r"^[a-z0-9]{5,10}$", re.IGNORECASE)
REMOVED_BODIES = {"[deleted]", "[removed]"}


class RedditApiError(RuntimeError):
    """Raised when Reddit returns an invalid or unsuccessful API response."""


@dataclass(frozen=True, slots=True)
class RedditConfig:
    client_id: str
    client_secret: str
    user_agent: str
    max_comments: int = 30
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.client_id.strip() or not self.client_secret.strip():
            raise ValueError("Reddit OAuth credentials are required after approval.")
        if "REPLACE_ME" in self.user_agent or "by /u/" not in self.user_agent:
            raise ValueError("A descriptive Reddit User-Agent with a username is required.")
        if not 1 <= self.max_comments <= 100:
            raise ValueError("max_comments must be between 1 and 100.")
        if not 5 <= self.timeout_seconds <= 120:
            raise ValueError("timeout_seconds must be between 5 and 120.")

    @classmethod
    def from_env(cls) -> "RedditConfig":
        return cls(
            client_id=os.environ.get("REDDIT_CLIENT_ID", ""),
            client_secret=os.environ.get("REDDIT_CLIENT_SECRET", ""),
            user_agent=os.environ.get("REDDIT_USER_AGENT", ""),
            max_comments=int(os.environ.get("REDDIT_MAX_COMMENTS", "30")),
            timeout_seconds=float(os.environ.get("REDDIT_TIMEOUT_SECONDS", "30")),
        )


@dataclass(frozen=True, slots=True)
class RedditComment:
    body: str
    score: int
    depth: int
    permalink: str
    created_utc: datetime | None


@dataclass(frozen=True, slots=True)
class RedditDocument:
    source_url: str
    submission_id: str
    title: str
    body: str
    subreddit: str
    permalink: str
    external_url: str
    score: int
    retrieved_at: datetime
    comments: tuple[RedditComment, ...]

    def to_analysis_text(self) -> str:
        """Create privacy-reduced input for the local inference model."""

        parts = [
            f"TITLE:\n{self.title}",
            f"SUBREDDIT:\nr/{self.subreddit}" if self.subreddit else "SUBREDDIT:\n",
            f"POST SCORE AT RETRIEVAL:\n{self.score}",
            f"POST BODY:\n{self.body}" if self.body else "POST BODY:\n[link post]",
        ]
        if self.external_url and self.external_url != self.permalink:
            parts.append(f"LINK TARGET:\n{self.external_url}")

        if self.comments:
            rendered = []
            for index, comment in enumerate(self.comments, start=1):
                rendered.append(
                    f"COMMENT {index} (score {comment.score}, depth {comment.depth}):\n"
                    f"{comment.body}"
                )
            parts.append("SELECTED PUBLIC COMMENTS:\n\n" + "\n\n".join(rendered))

        return "\n\n".join(parts).strip()


def parse_submission_id(url: str) -> str:
    """Extract a submission ID without requesting a user-controlled host."""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP(S) Reddit URLs are supported.")
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError("The URL is not hosted by an allowed Reddit domain.")

    parts = [part for part in parsed.path.split("/") if part]
    candidate = ""
    if host in {"redd.it", "www.redd.it"} and parts:
        candidate = parts[0]
    elif "comments" in parts:
        index = parts.index("comments")
        if index + 1 < len(parts):
            candidate = parts[index + 1]

    if not POST_ID_RE.fullmatch(candidate):
        raise ValueError("The URL does not contain a valid Reddit submission ID.")
    return candidate.lower()


def _utc_datetime(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def _children(listing: Any) -> list[dict[str, Any]]:
    if not isinstance(listing, dict):
        return []
    data = listing.get("data")
    if not isinstance(data, dict):
        return []
    children = data.get("children")
    return [item for item in children if isinstance(item, dict)] if isinstance(children, list) else []


def _collect_comments(listing: Any, result: list[RedditComment]) -> None:
    for child in _children(listing):
        if child.get("kind") != "t1":
            continue
        data = child.get("data")
        if not isinstance(data, dict):
            continue
        body = str(data.get("body") or "").strip()
        if body and body.lower() not in REMOVED_BODIES:
            permalink = str(data.get("permalink") or "")
            result.append(
                RedditComment(
                    body=body,
                    score=int(data.get("score") or 0),
                    depth=max(0, int(data.get("depth") or 0)),
                    permalink=(f"https://www.reddit.com{permalink}" if permalink.startswith("/") else permalink),
                    created_utc=_utc_datetime(data.get("created_utc")),
                )
            )
        replies = data.get("replies")
        if isinstance(replies, dict):
            _collect_comments(replies, result)


class RedditClient:
    """Small OAuth client for one manually submitted public post at a time."""

    def __init__(
        self,
        config: RedditConfig,
        transport: httpx.BaseTransport | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self._transport = transport
        self._now = now or (lambda: datetime.now(tz=UTC))

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.config.timeout_seconds,
            headers={"User-Agent": self.config.user_agent},
            transport=self._transport,
            follow_redirects=False,
        )

    def _access_token(self, client: httpx.Client) -> str:
        response = client.post(
            TOKEN_URL,
            auth=(self.config.client_id, self.config.client_secret),
            data={"grant_type": "client_credentials"},
        )
        if response.status_code != 200:
            raise RedditApiError(f"OAuth token request failed with HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise RedditApiError("OAuth token response was not valid JSON.") from exc
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            raise RedditApiError("OAuth token response did not include an access token.")
        return token

    def fetch_submission(self, url: str) -> RedditDocument:
        submission_id = parse_submission_id(url)
        with self._client() as client:
            token = self._access_token(client)
            response = client.get(
                f"{API_BASE_URL}/comments/{submission_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "raw_json": 1,
                    "sort": "top",
                    "depth": 5,
                    "limit": self.config.max_comments,
                },
            )
        if response.status_code != 200:
            raise RedditApiError(f"Submission request failed with HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise RedditApiError("Submission response was not valid JSON.") from exc
        if not isinstance(payload, list) or len(payload) < 2:
            raise RedditApiError("Submission response did not contain a post and comment listing.")

        post_children = _children(payload[0])
        if not post_children or not isinstance(post_children[0].get("data"), dict):
            raise RedditApiError("Submission response did not contain a valid post.")
        post = post_children[0]["data"]
        body = str(post.get("selftext") or "").strip()
        if body.lower() in REMOVED_BODIES:
            raise RedditApiError("The submitted Reddit post has been deleted or removed.")

        comments: list[RedditComment] = []
        _collect_comments(payload[1], comments)
        comments.sort(key=lambda item: item.score, reverse=True)
        selected = tuple(comments[: self.config.max_comments])

        permalink_path = str(post.get("permalink") or "")
        permalink = (
            f"https://www.reddit.com{permalink_path}"
            if permalink_path.startswith("/")
            else permalink_path
        )
        return RedditDocument(
            source_url=url,
            submission_id=submission_id,
            title=str(post.get("title") or "Untitled Reddit post").strip(),
            body=body,
            subreddit=str(post.get("subreddit") or "").strip(),
            permalink=permalink,
            external_url=str(post.get("url") or permalink).strip(),
            score=int(post.get("score") or 0),
            retrieved_at=self._now(),
            comments=selected,
        )

    def source_is_available(self, url: str) -> bool:
        """Return False when a source is absent, deleted, or removed."""

        try:
            self.fetch_submission(url)
        except RedditApiError as exc:
            message = str(exc).lower()
            if "deleted or removed" in message or "http 404" in message:
                return False
            raise
        return True

