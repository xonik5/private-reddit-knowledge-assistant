from __future__ import annotations

import unittest
from datetime import UTC, datetime

import httpx

from private_reddit_knowledge_assistant.client import (
    RedditClient,
    RedditConfig,
    parse_submission_id,
)


class RedditClientTests(unittest.TestCase):
    def test_parse_submission_id_from_full_url(self) -> None:
        url = "https://www.reddit.com/r/n8n/comments/1t9u0rh/example/?tl=pl"
        self.assertEqual(parse_submission_id(url), "1t9u0rh")

    def test_parse_submission_id_from_short_url(self) -> None:
        self.assertEqual(parse_submission_id("https://redd.it/1t9u0rh"), "1t9u0rh")

    def test_rejects_non_reddit_host(self) -> None:
        with self.assertRaisesRegex(ValueError, "allowed Reddit domain"):
            parse_submission_id("https://example.com/comments/1t9u0rh")

    def test_fetches_bounded_privacy_reduced_document(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url == httpx.URL("https://www.reddit.com/api/v1/access_token"):
                return httpx.Response(
                    200,
                    json={"access_token": "test-token", "token_type": "bearer"},
                )
            self.assertEqual(request.headers["authorization"], "Bearer test-token")
            return httpx.Response(
                200,
                json=[
                {
                    "kind": "Listing",
                    "data": {
                        "children": [
                            {
                                "kind": "t3",
                                "data": {
                                    "title": "Example post",
                                    "selftext": "Example body",
                                    "subreddit": "n8n",
                                    "permalink": "/r/n8n/comments/1t9u0rh/example/",
                                    "url": "https://www.reddit.com/r/n8n/comments/1t9u0rh/example/",
                                    "score": 12,
                                    "author": "post_author_is_not_persisted",
                                },
                            }
                        ]
                    },
                },
                {
                    "kind": "Listing",
                    "data": {
                        "children": [
                            {
                                "kind": "t1",
                                "data": {
                                    "body": "Useful comment",
                                    "score": 8,
                                    "depth": 0,
                                    "permalink": "/r/n8n/comments/1t9u0rh/example/comment1/",
                                    "created_utc": 1_700_000_000,
                                    "author": "comment_author_is_not_persisted",
                                    "replies": "",
                                },
                            },
                            {
                                "kind": "t1",
                                "data": {
                                    "body": "[deleted]",
                                    "score": 100,
                                    "depth": 0,
                                    "author": "deleted_user",
                                    "replies": "",
                                },
                            },
                        ]
                    },
                },
                ],
            )

        config = RedditConfig(
            client_id="client-id",
            client_secret="client-secret",
            user_agent="windows:private-reddit-knowledge-assistant:v0.1.0 (by /u/example)",
            max_comments=5,
        )
        client = RedditClient(
            config,
            transport=httpx.MockTransport(handler),
            now=lambda: datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
        )
        document = client.fetch_submission(
            "https://www.reddit.com/r/n8n/comments/1t9u0rh/example/?tl=pl"
        )

        self.assertEqual(document.title, "Example post")
        self.assertEqual(document.subreddit, "n8n")
        self.assertEqual(
            [comment.body for comment in document.comments],
            ["Useful comment"],
        )
        analysis_text = document.to_analysis_text()
        self.assertIn("Useful comment", analysis_text)
        self.assertNotIn("post_author_is_not_persisted", analysis_text)
        self.assertNotIn("comment_author_is_not_persisted", analysis_text)

    def test_placeholder_user_agent_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "descriptive Reddit User-Agent"):
            RedditConfig(
                client_id="id",
                client_secret="secret",
                user_agent="windows:app:v0.1.0 (by /u/REPLACE_ME)",
            )


if __name__ == "__main__":
    unittest.main()
