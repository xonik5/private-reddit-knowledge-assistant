import unittest
from datetime import UTC, datetime, timedelta

from private_reddit_knowledge_assistant.retention import (
    delete_derived_content,
    raw_content_expired,
)


class RetentionTests(unittest.TestCase):
    def test_raw_content_expires_at_48_hours(self) -> None:
        retrieved = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
        self.assertFalse(
            raw_content_expired(
                retrieved,
                retrieved + timedelta(hours=47, minutes=59),
            )
        )
        self.assertTrue(raw_content_expired(retrieved, retrieved + timedelta(hours=48)))

    def test_derived_content_is_deleted_when_source_is_unavailable(self) -> None:
        self.assertTrue(delete_derived_content(False))
        self.assertFalse(delete_derived_content(True))


if __name__ == "__main__":
    unittest.main()
