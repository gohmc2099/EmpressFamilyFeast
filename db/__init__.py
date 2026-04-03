"""Database layer — auto-selects Google Sheets or SQLite.

If GOOGLE_SHEET_ID is set, uses Google Sheets as primary storage.
Falls back to SQLite if Sheets is unavailable or not configured.
"""

from __future__ import annotations

import os


def get_db():
    """Get the database instance — Google Sheets if configured, else SQLite."""
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")

    if sheet_id:
        try:
            from db.google_sheets import get_sheets_db
            return get_sheets_db(sheet_id)
        except Exception as e:
            print(f"[ERIC] Google Sheets unavailable ({e}), falling back to SQLite.")

    from db.database import get_db as get_sqlite_db
    return get_sqlite_db()
