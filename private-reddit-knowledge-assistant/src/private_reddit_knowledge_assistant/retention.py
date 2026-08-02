"""Retention decisions used by the host application's scheduled cleanup job."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


RAW_CONTENT_MAX_AGE = timedelta(hours=48)


def raw_content_expired(retrieved_at: datetime, now: datetime | None = None) -> bool:
    """Return True when raw Reddit content must be purged."""

    current = now or datetime.now(tz=UTC)
    if retrieved_at.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware.")
    return current - retrieved_at >= RAW_CONTENT_MAX_AGE


def delete_derived_content(source_available: bool) -> bool:
    """Delete derived Reddit data when the original source is unavailable."""

    return not source_available

