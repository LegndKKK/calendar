from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from calendar_app.paths import migrate_legacy_data, resolve_data_dir, system_data_dir


class DataDirTests(unittest.TestCase):
    def test_override_is_resolved(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"CALENDAR_DATA_DIR": temp}):
                self.assertEqual(system_data_dir(), Path(temp).resolve())

    def test_migrate_moves_files(self):
        with tempfile.TemporaryDirectory() as temp:
            legacy = Path(temp) / "legacy"
            target = Path(temp) / "target"
            legacy.mkdir()
            target.mkdir()
            (legacy / "calendar.db").write_bytes(b"database")
            (legacy / "config.json").write_text('{"api_key": "x"}', encoding="utf-8")

            migrated = migrate_legacy_data(legacy, target)

            self.assertEqual(sorted(migrated), ["calendar.db", "config.json"])
            self.assertTrue((target / "calendar.db").exists())
            self.assertFalse((legacy / "calendar.db").exists())

    def test_existing_target_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            legacy = Path(temp) / "legacy"
            target = Path(temp) / "target"
            legacy.mkdir()
            target.mkdir()
            (legacy / "config.json").write_text("old", encoding="utf-8")
            (target / "config.json").write_text("new", encoding="utf-8")

            migrated = migrate_legacy_data(legacy, target)

            self.assertEqual(migrated, [])
            self.assertEqual((target / "config.json").read_text(encoding="utf-8"), "new")

    def test_resolve_creates_and_migrates(self):
        with tempfile.TemporaryDirectory() as temp:
            legacy = Path(temp) / "legacy"
            target = Path(temp) / "data"
            legacy.mkdir()
            (legacy / "calendar.db").write_bytes(b"database")

            with patch.dict(os.environ, {"CALENDAR_DATA_DIR": str(target)}):
                resolved, migrated = resolve_data_dir(legacy)

            self.assertEqual(resolved, target)
            self.assertEqual(migrated, ["calendar.db"])
            self.assertTrue((target / "calendar.db").exists())


if __name__ == "__main__":
    unittest.main()
