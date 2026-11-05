from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from calendar_app.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "calendar.db")

    def tearDown(self):
        self.temp.cleanup()

    def _event(self, title="会议", start="2026-11-06T15:00"):
        return {
            "title": title,
            "start": start,
            "end": start[:11] + "16:00",
            "all_day": False,
            "location": "",
            "notes": "",
        }

    def test_create_and_list(self):
        created = self.store.create_event(self._event())
        self.assertIsNotNone(created["id"])
        events = self.store.list_events("2026-11-01T00:00", "2026-12-01T00:00")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["title"], "会议")

    def test_update(self):
        created = self.store.create_event(self._event())
        updated = self.store.update_event(created["id"], self._event("改期会议", "2026-11-07T09:00"))
        self.assertEqual(updated["title"], "改期会议")
        self.assertEqual(updated["start"], "2026-11-07T09:00")

    def test_delete(self):
        created = self.store.create_event(self._event())
        self.assertTrue(self.store.delete_event(created["id"]))
        self.assertFalse(self.store.delete_event(created["id"]))

    def test_range_filter(self):
        self.store.create_event(self._event("一号", "2026-11-01T09:00"))
        self.store.create_event(self._event("十号", "2026-11-10T09:00"))
        events = self.store.list_events("2026-11-05T00:00", "2026-11-20T00:00")
        self.assertEqual([event["title"] for event in events], ["十号"])

    def test_bulk(self):
        events = self.store.create_events([self._event("A"), self._event("B", "2026-11-08T09:00")])
        self.assertEqual(len(events), 2)

    def test_backup_contains_events(self):
        self.store.create_event(self._event())
        backup_path = Path(self.temp.name) / "backup.db"

        self.store.backup_to(backup_path)

        self.assertTrue(backup_path.exists())
        connection = sqlite3.connect(backup_path)
        try:
            count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            title = connection.execute("SELECT title FROM events").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(count, 1)
        self.assertEqual(title, "会议")


if __name__ == "__main__":
    unittest.main()
