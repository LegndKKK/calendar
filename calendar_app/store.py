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

CREATE TABLE IF NOT EXISTS companies (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    info       TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS interview_stages (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT    NOT NULL UNIQUE,
    position INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS interview_cells (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    stage      TEXT    NOT NULL,
    link       TEXT    NOT NULL DEFAULT '',
    content    TEXT    NOT NULL DEFAULT '',
    status     TEXT    NOT NULL DEFAULT '待安排',
    updated_at TEXT    NOT NULL,
    UNIQUE(company_id, stage),
    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_interview_cells_company ON interview_cells(company_id);
"""

DEFAULT_STAGES = ("HR 面", "一面", "二面", "三面", "终面", "Offer")

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
            if conn.execute("SELECT COUNT(*) FROM interview_stages").fetchone()[0] == 0:
                for position, name in enumerate(DEFAULT_STAGES):
                    conn.execute(
                        "INSERT INTO interview_stages (name, position) VALUES (?, ?)",
                        (name, position),
                    )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
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

    # ---------- 面试时间线 ----------

    def list_interviews(self) -> dict:
        with closing(self._connect()) as conn:
            companies = [
                dict(row)
                for row in conn.execute(
                    "SELECT id, name, info, created_at, updated_at FROM companies ORDER BY id"
                )
            ]
            stages = [
                dict(row)
                for row in conn.execute(
                    "SELECT id, name, position FROM interview_stages ORDER BY position, id"
                )
            ]
            cells = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, company_id, stage, link, content, status, updated_at
                      FROM interview_cells
                     ORDER BY company_id, id
                    """
                )
            ]
        return {"companies": companies, "stages": stages, "cells": cells}

    def get_company(self, company_id: int) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT id, name, info, created_at, updated_at FROM companies WHERE id = ?",
                (company_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_company(self, name: str, info: str = "") -> dict:
        name = str(name).strip()
        if not name:
            raise ValueError("公司名称不能为空")
        now = datetime.now().isoformat(timespec="seconds")
        try:
            with closing(self._connect()) as conn, conn:
                cursor = conn.execute(
                    """
                    INSERT INTO companies (name, info, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, str(info).strip(), now, now),
                )
                company_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError:
            raise ValueError("公司名称已存在") from None
        company = self.get_company(company_id)
        assert company is not None
        return company

    def update_company(
        self, company_id: int, name: str | None = None, info: str | None = None
    ) -> dict | None:
        existing = self.get_company(company_id)
        if existing is None:
            return None
        new_name = existing["name"] if name is None else str(name).strip()
        if not new_name:
            raise ValueError("公司名称不能为空")
        new_info = existing["info"] if info is None else str(info).strip()
        now = datetime.now().isoformat(timespec="seconds")
        try:
            with closing(self._connect()) as conn, conn:
                conn.execute(
                    """
                    UPDATE companies
                       SET name = ?, info = ?, updated_at = ?
                     WHERE id = ?
                    """,
                    (new_name, new_info, now, company_id),
                )
        except sqlite3.IntegrityError:
            raise ValueError("公司名称已存在") from None
        return self.get_company(company_id)

    def delete_company(self, company_id: int) -> bool:
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        return cursor.rowcount > 0

    def get_stage(self, stage_id: int) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT id, name, position FROM interview_stages WHERE id = ?",
                (stage_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_stage(self, name: str) -> dict:
        name = str(name).strip()
        if not name:
            raise ValueError("阶段名称不能为空")
        now_position = 0
        try:
            with closing(self._connect()) as conn, conn:
                now_position = conn.execute(
                    "SELECT COALESCE(MAX(position), -1) + 1 FROM interview_stages"
                ).fetchone()[0]
                cursor = conn.execute(
                    "INSERT INTO interview_stages (name, position) VALUES (?, ?)",
                    (name, now_position),
                )
                stage_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError:
            raise ValueError("阶段已存在") from None
        stage = self.get_stage(stage_id)
        assert stage is not None
        return stage

    def get_interview_cell(self, company_id: int, stage: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT id, company_id, stage, link, content, status, updated_at
                  FROM interview_cells
                 WHERE company_id = ? AND stage = ?
                """,
                (company_id, stage),
            ).fetchone()
        return dict(row) if row else None

    def upsert_interview_cell(
        self,
        company_id: int,
        stage: str,
        link: str = "",
        content: str = "",
        status: str = "待安排",
    ) -> dict:
        stage = str(stage).strip()
        now = datetime.now().isoformat(timespec="seconds")
        with closing(self._connect()) as conn, conn:
            company = conn.execute(
                "SELECT 1 FROM companies WHERE id = ?", (company_id,)
            ).fetchone()
            if company is None:
                raise ValueError("公司不存在")
            stage_row = conn.execute(
                "SELECT 1 FROM interview_stages WHERE name = ?", (stage,)
            ).fetchone()
            if stage_row is None:
                raise ValueError("阶段不存在")
            conn.execute(
                """
                INSERT INTO interview_cells
                    (company_id, stage, link, content, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_id, stage) DO UPDATE SET
                    link = excluded.link,
                    content = excluded.content,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (company_id, stage, str(link).strip(), str(content).strip(), status, now),
            )
        cell = self.get_interview_cell(company_id, stage)
        assert cell is not None
        return cell

    def delete_interview_cell(self, company_id: int, stage: str) -> bool:
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                "DELETE FROM interview_cells WHERE company_id = ? AND stage = ?",
                (company_id, stage),
            )
        return cursor.rowcount > 0
