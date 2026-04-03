"""Persistent SQLite database for Empress Family Feast delivery operations.

Replaces the in-memory dicts with durable storage that survives between sessions.
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "empress.db"
)


class Database:
    """SQLite wrapper for delivery operations data."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS drivers (
                name        TEXT PRIMARY KEY,
                status      TEXT NOT NULL DEFAULT 'available',
                vehicle     TEXT NOT NULL,
                vehicle_ok  INTEGER NOT NULL DEFAULT 1,
                phone       TEXT NOT NULL,
                route       TEXT NOT NULL,
                last_seen   TEXT
            );

            CREATE TABLE IF NOT EXISTS deliveries (
                id              TEXT PRIMARY KEY,
                driver          TEXT NOT NULL REFERENCES drivers(name),
                customer        TEXT NOT NULL,
                address         TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'pending',
                photo_verified  INTEGER NOT NULL DEFAULT 0,
                photo_path      TEXT,
                vision_analysis TEXT,
                timestamp       TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS incidents (
                id          TEXT PRIMARY KEY,
                type        TEXT NOT NULL,
                severity    TEXT NOT NULL,
                driver      TEXT,
                description TEXT NOT NULL,
                logged_at   TEXT NOT NULL,
                resolved    INTEGER NOT NULL DEFAULT 0,
                resolved_at TEXT,
                FOREIGN KEY (driver) REFERENCES drivers(name)
            );

            CREATE TABLE IF NOT EXISTS ops_messages (
                id      TEXT PRIMARY KEY,
                level   TEXT NOT NULL,
                subject TEXT NOT NULL,
                body    TEXT NOT NULL,
                sent_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS photo_verifications (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                delivery_id     TEXT NOT NULL REFERENCES deliveries(id),
                photo_path      TEXT NOT NULL,
                expected_address TEXT NOT NULL,
                vision_result   TEXT NOT NULL,
                address_found   TEXT,
                match_result    TEXT NOT NULL,
                confidence      REAL,
                details         TEXT,
                verified_at     TEXT NOT NULL
            );
        """)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Drivers
    # ------------------------------------------------------------------

    def get_all_drivers(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM drivers ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def get_driver(self, name: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM drivers WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None

    def update_driver_last_seen(self, name: str, timestamp: str) -> None:
        self.conn.execute(
            "UPDATE drivers SET last_seen = ? WHERE name = ?", (timestamp, name)
        )
        self.conn.commit()

    def update_driver_status(self, name: str, status: str) -> None:
        self.conn.execute(
            "UPDATE drivers SET status = ? WHERE name = ?", (status, name)
        )
        self.conn.commit()

    def driver_exists(self, name: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM drivers WHERE name = ?", (name,)).fetchone()
        return row is not None

    def count_drivers(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM drivers").fetchone()[0]

    # ------------------------------------------------------------------
    # Deliveries
    # ------------------------------------------------------------------

    def get_all_deliveries(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM deliveries ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def get_deliveries_by_driver(self, driver: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM deliveries WHERE driver = ? ORDER BY id", (driver,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_delivery(self, delivery_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM deliveries WHERE id = ?", (delivery_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_delivery_status(
        self, delivery_id: str, status: str, timestamp: str
    ) -> None:
        self.conn.execute(
            "UPDATE deliveries SET status = ?, timestamp = ? WHERE id = ?",
            (status, timestamp, delivery_id),
        )
        self.conn.commit()

    def update_delivery_photo(
        self,
        delivery_id: str,
        verified: bool,
        photo_path: str | None = None,
        vision_analysis: str | None = None,
    ) -> None:
        self.conn.execute(
            "UPDATE deliveries SET photo_verified = ?, photo_path = ?, vision_analysis = ? WHERE id = ?",
            (int(verified), photo_path, vision_analysis, delivery_id),
        )
        self.conn.commit()

    def get_delivery_summary(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0]
        completed = self.conn.execute(
            "SELECT COUNT(*) FROM deliveries WHERE status = 'delivered'"
        ).fetchone()[0]
        failed = self.conn.execute(
            "SELECT COUNT(*) FROM deliveries WHERE status IN ('photo_mismatch', 'failed')"
        ).fetchone()[0]
        pending = self.conn.execute(
            "SELECT COUNT(*) FROM deliveries WHERE status = 'pending'"
        ).fetchone()[0]
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
        }

    # ------------------------------------------------------------------
    # Incidents
    # ------------------------------------------------------------------

    def add_incident(
        self, incident_id: str, incident_type: str, severity: str,
        driver: str, description: str, logged_at: str
    ) -> dict:
        self.conn.execute(
            "INSERT INTO incidents (id, type, severity, driver, description, logged_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (incident_id, incident_type, severity, driver, description, logged_at),
        )
        self.conn.commit()
        return dict(self.conn.execute(
            "SELECT * FROM incidents WHERE id = ?", (incident_id,)
        ).fetchone())

    def get_all_incidents(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM incidents ORDER BY logged_at DESC").fetchall()
        return [dict(r) for r in rows]

    def count_incidents(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]

    # ------------------------------------------------------------------
    # Ops messages
    # ------------------------------------------------------------------

    def add_ops_message(
        self, msg_id: str, level: str, subject: str, body: str, sent_at: str
    ) -> dict:
        self.conn.execute(
            "INSERT INTO ops_messages (id, level, subject, body, sent_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (msg_id, level, subject, body, sent_at),
        )
        self.conn.commit()
        return dict(self.conn.execute(
            "SELECT * FROM ops_messages WHERE id = ?", (msg_id,)
        ).fetchone())

    def get_all_ops_messages(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM ops_messages ORDER BY sent_at DESC").fetchall()
        return [dict(r) for r in rows]

    def count_ops_messages(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM ops_messages").fetchone()[0]

    # ------------------------------------------------------------------
    # Photo verifications
    # ------------------------------------------------------------------

    def add_photo_verification(
        self, delivery_id: str, photo_path: str, expected_address: str,
        vision_result: str, address_found: str | None, match_result: str,
        confidence: float | None, details: str | None, verified_at: str,
    ) -> int:
        cursor = self.conn.execute(
            "INSERT INTO photo_verifications "
            "(delivery_id, photo_path, expected_address, vision_result, "
            "address_found, match_result, confidence, details, verified_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (delivery_id, photo_path, expected_address, vision_result,
             address_found, match_result, confidence, details, verified_at),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_verifications_for_delivery(self, delivery_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM photo_verifications WHERE delivery_id = ? ORDER BY verified_at DESC",
            (delivery_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self.conn.close()


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_db_instance: Database | None = None


def get_db(db_path: str = DEFAULT_DB_PATH) -> Database:
    """Get or create the global Database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
    return _db_instance
