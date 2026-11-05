"""SQLite 存储层。"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .event_utils import row_to_event

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    start_at   TEXT    NOT NULL,
    end_at     TEXT    NOT NULL,
    all_day    INTEGER NOT NULL DEFAULT 0,
    location   TEXT    NOT NULL DEFAULT '',
    notes      TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_at);
"""

_FIELDS = ("title", "start_at", "end_at", "all_day", "location", "notes")


def _row_to_dict(row) -> dict:
    event = row_to_event(row)
    event["created_at"] = row["created_at"]
    event["updated_at"] = row["updated_at"]
    return event


class Store:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def list_events(self, start: str | None = None, end: str | None = None) -> list[dict]:
        clauses: list[str] = []
        params: list[str] = []
        if start:
            clauses.append("COALESCE(end_at, start_at) > ?")
            params.append(start)
        if end:
            clauses.append("start_at < ?")
            params.append(end)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM events {where} ORDER BY start_at ASC, id ASC LIMIT 5000"
        with closing(self._connect()) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(row) for row in rows]

    def get_event(self, event_id: int) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return _row_to_dict(row) if row else None

    def create_event(self, event: dict) -> dict:
        return self.create_events([event])[0]

    def create_events(self, events: list[dict]) -> list[dict]:
        now = datetime.now().isoformat(timespec="seconds")
        created_ids: list[int] = []
        with closing(self._connect()) as conn, conn:
            for event in events:
                cursor = conn.execute(
                    """
                    INSERT INTO events
                        (title, start_at, end_at, all_day, location, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["title"],
                        event["start"],
                        event["end"],
                        1 if event["all_day"] else 0,
                        event["location"],
                        event["notes"],
                        now,
                        now,
                    ),
                )
                created_ids.append(int(cursor.lastrowid))
        return [self.get_event(event_id) for event_id in created_ids]  # type: ignore[list-item]

    def update_event(self, event_id: int, event: dict) -> dict | None:
        existing = self.get_event(event_id)
        if existing is None:
            return None
        now = datetime.now().isoformat(timespec="seconds")
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                UPDATE events
                   SET title = ?, start_at = ?, end_at = ?, all_day = ?,
                       location = ?, notes = ?, updated_at = ?
                 WHERE id = ?
                """,
                (
                    event["title"],
                    event["start"],
                    event["end"],
                    1 if event["all_day"] else 0,
                    event["location"],
                    event["notes"],
                    now,
                    event_id,
                ),
            )
        return self.get_event(event_id)

    def delete_event(self, event_id: int) -> bool:
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        return cursor.rowcount > 0

    def backup_to(self, destination: Path) -> None:
        """用 SQLite 在线备份 API 生成一致性的数据库副本。"""
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as source, closing(sqlite3.connect(destination)) as target:
            source.backup(target)
            target.commit()
