"""Google Sheets database adapter for Empress Family Feast.

Implements the same interface as Database (SQLite) but reads/writes to
Google Sheets. Your team can view and edit data directly in the spreadsheet.

SETUP:
1. Go to https://console.cloud.google.com/
2. Create a project (or use existing)
3. Enable the "Google Sheets API" and "Google Drive API"
4. Create a Service Account (APIs & Services → Credentials → Create Credentials)
5. Download the JSON key file → save as 'credentials.json' in the project root
6. Create a Google Sheet and share it with the service account email
7. Set the GOOGLE_SHEET_ID env var to the spreadsheet ID from the URL

The spreadsheet will have these tabs (auto-created if missing):
  - Drivers
  - Schedule
  - Stops
  - Deliveries
  - Incidents
  - OpsMessages
  - PhotoVerifications
"""

from __future__ import annotations

import datetime
import json
import os
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CREDENTIALS_FILE = os.environ.get(
    "GOOGLE_CREDENTIALS_FILE",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json"),
)

GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")

# If credentials are passed as a JSON string (for Render env var)
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")

# ---------------------------------------------------------------------------
# Sheet column definitions (order matters — must match header rows)
# ---------------------------------------------------------------------------

DRIVERS_COLS = ["name", "status", "vehicle", "vehicle_ok", "phone", "route", "whatsapp_group", "last_seen"]
SCHEDULE_COLS = ["driver", "day_of_week", "active"]
STOPS_COLS = ["id", "driver", "stop_order", "customer", "address", "notes"]
DELIVERIES_COLS = ["id", "driver", "customer", "address", "status", "photo_verified", "photo_path", "vision_analysis", "timestamp", "created_at"]
INCIDENTS_COLS = ["id", "type", "severity", "driver", "description", "logged_at", "resolved", "resolved_at"]
OPS_COLS = ["id", "level", "subject", "body", "sent_at"]
PHOTO_COLS = ["id", "delivery_id", "photo_path", "expected_address", "vision_result", "address_found", "match_result", "confidence", "details", "verified_at"]


class GoogleSheetsDatabase:
    """Google Sheets adapter — same interface as the SQLite Database class."""

    DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def __init__(self, sheet_id: str = GOOGLE_SHEET_ID) -> None:
        self.sheet_id = sheet_id
        self.client = self._authenticate()
        self.spreadsheet = self.client.open_by_key(sheet_id)
        self._ensure_worksheets()

    def _authenticate(self) -> gspread.Client:
        if GOOGLE_CREDENTIALS_JSON:
            info = json.loads(GOOGLE_CREDENTIALS_JSON)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        return gspread.authorize(creds)

    def _ensure_worksheets(self) -> None:
        """Create tabs and headers if they don't exist."""
        existing = [ws.title for ws in self.spreadsheet.worksheets()]
        sheets_config = {
            "Drivers": DRIVERS_COLS,
            "Schedule": SCHEDULE_COLS,
            "Stops": STOPS_COLS,
            "Deliveries": DELIVERIES_COLS,
            "Incidents": INCIDENTS_COLS,
            "OpsMessages": OPS_COLS,
            "PhotoVerifications": PHOTO_COLS,
        }
        for title, cols in sheets_config.items():
            if title not in existing:
                ws = self.spreadsheet.add_worksheet(title=title, rows=1000, cols=len(cols))
                ws.update([cols], "A1")
            else:
                ws = self.spreadsheet.worksheet(title)
                header = ws.row_values(1)
                if not header:
                    ws.update([cols], "A1")

    def _ws(self, name: str) -> gspread.Worksheet:
        return self.spreadsheet.worksheet(name)

    def _get_all_records(self, sheet_name: str) -> list[dict]:
        ws = self._ws(sheet_name)
        return ws.get_all_records()

    def _find_row(self, sheet_name: str, col: int, value: str) -> int | None:
        """Find row number (1-indexed) where column col matches value."""
        ws = self._ws(sheet_name)
        cells = ws.col_values(col)
        for i, cell_val in enumerate(cells):
            if i == 0:
                continue  # skip header
            if str(cell_val) == str(value):
                return i + 1
        return None

    def _append_row(self, sheet_name: str, values: list) -> None:
        ws = self._ws(sheet_name)
        ws.append_row(values, value_input_option="USER_ENTERED")

    def _now(self) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # Drivers
    # ------------------------------------------------------------------

    def get_all_drivers(self) -> list[dict]:
        records = self._get_all_records("Drivers")
        for r in records:
            r["vehicle_ok"] = int(r.get("vehicle_ok", 1))
        return sorted(records, key=lambda d: d.get("name", ""))

    def get_driver(self, name: str) -> dict | None:
        for d in self.get_all_drivers():
            if d["name"] == name:
                return d
        return None

    def driver_exists(self, name: str) -> bool:
        return self.get_driver(name) is not None

    def count_drivers(self) -> int:
        return len(self.get_all_drivers())

    def add_driver(
        self, name: str, vehicle: str, phone: str, route: str,
        whatsapp_group: str = "", status: str = "available",
    ) -> dict:
        self._append_row("Drivers", [name, status, vehicle, 1, phone, route, whatsapp_group, ""])
        return self.get_driver(name)

    def update_driver(
        self, name: str, vehicle: str, phone: str, route: str,
        whatsapp_group: str = "", status: str = "available",
    ) -> None:
        row = self._find_row("Drivers", 1, name)
        if row:
            ws = self._ws("Drivers")
            ws.update(f"B{row}:G{row}", [[status, vehicle, 1, phone, route, whatsapp_group]])

    def update_driver_last_seen(self, name: str, timestamp: str) -> None:
        row = self._find_row("Drivers", 1, name)
        if row:
            ws = self._ws("Drivers")
            ws.update(f"H{row}", [[timestamp]])

    def update_driver_status(self, name: str, status: str) -> None:
        row = self._find_row("Drivers", 1, name)
        if row:
            ws = self._ws("Drivers")
            ws.update(f"B{row}", [[status]])

    def delete_driver(self, name: str) -> None:
        # Delete from Drivers sheet
        row = self._find_row("Drivers", 1, name)
        if row:
            self._ws("Drivers").delete_rows(row)
        # Delete schedule entries
        self._delete_rows_by_col("Schedule", 1, name)
        # Delete stops entries
        self._delete_rows_by_col("Stops", 2, name)

    def _delete_rows_by_col(self, sheet_name: str, col: int, value: str) -> None:
        ws = self._ws(sheet_name)
        cells = ws.col_values(col)
        rows_to_delete = []
        for i, cell_val in enumerate(cells):
            if i == 0:
                continue
            if str(cell_val) == str(value):
                rows_to_delete.append(i + 1)
        for row in reversed(rows_to_delete):
            ws.delete_rows(row)

    # ------------------------------------------------------------------
    # Driver schedule (weekly)
    # ------------------------------------------------------------------

    def get_driver_schedule(self, driver: str) -> dict[str, bool]:
        records = self._get_all_records("Schedule")
        schedule = {day: False for day in self.DAYS_OF_WEEK}
        for r in records:
            if r.get("driver") == driver:
                schedule[r["day_of_week"]] = bool(int(r.get("active", 0)))
        return schedule

    def set_driver_schedule(self, driver: str, active_days: list[str]) -> None:
        self._delete_rows_by_col("Schedule", 1, driver)
        for day in self.DAYS_OF_WEEK:
            active = 1 if day in active_days else 0
            self._append_row("Schedule", [driver, day, active])

    def get_weekly_schedule(self) -> list[dict]:
        drivers = self.get_all_drivers()
        result = []
        for d in drivers:
            schedule = self.get_driver_schedule(d["name"])
            result.append({"driver": d["name"], "route": d.get("route", ""), "schedule": schedule})
        return result

    # ------------------------------------------------------------------
    # Stops
    # ------------------------------------------------------------------

    def get_stops_for_driver(self, driver: str) -> list[dict]:
        records = self._get_all_records("Stops")
        stops = [r for r in records if r.get("driver") == driver]
        return sorted(stops, key=lambda s: int(s.get("stop_order", 0)))

    def add_stop(self, driver: str, customer: str, address: str, notes: str = "", stop_order: int = 0) -> dict:
        ws = self._ws("Stops")
        all_records = ws.get_all_records()
        max_id = 0
        for r in all_records:
            try:
                max_id = max(max_id, int(r.get("id", 0)))
            except (ValueError, TypeError):
                pass
        new_id = max_id + 1
        self._append_row("Stops", [new_id, driver, stop_order, customer, address, notes])
        return {"id": new_id, "driver": driver, "stop_order": stop_order, "customer": customer, "address": address, "notes": notes}

    def delete_stop(self, stop_id: int) -> None:
        row = self._find_row("Stops", 1, str(stop_id))
        if row:
            self._ws("Stops").delete_rows(row)

    # ------------------------------------------------------------------
    # Deliveries
    # ------------------------------------------------------------------

    def get_all_deliveries(self) -> list[dict]:
        records = self._get_all_records("Deliveries")
        for r in records:
            r["photo_verified"] = bool(int(r.get("photo_verified", 0)))
        return records

    def get_deliveries_by_driver(self, driver: str) -> list[dict]:
        return [d for d in self.get_all_deliveries() if d.get("driver") == driver]

    def get_delivery(self, delivery_id: str) -> dict | None:
        for d in self.get_all_deliveries():
            if d.get("id") == delivery_id:
                return d
        return None

    def update_delivery_status(self, delivery_id: str, status: str, timestamp: str) -> None:
        row = self._find_row("Deliveries", 1, delivery_id)
        if row:
            ws = self._ws("Deliveries")
            ws.update(f"E{row}", [[status]])
            ws.update(f"I{row}", [[timestamp]])

    def update_delivery_photo(
        self, delivery_id: str, verified: bool,
        photo_path: str | None = None, vision_analysis: str | None = None,
    ) -> None:
        row = self._find_row("Deliveries", 1, delivery_id)
        if row:
            ws = self._ws("Deliveries")
            ws.update(f"F{row}:H{row}", [[int(verified), photo_path or "", vision_analysis or ""]])

    def get_delivery_summary(self) -> dict:
        deliveries = self.get_all_deliveries()
        return {
            "total": len(deliveries),
            "completed": sum(1 for d in deliveries if d.get("status") == "delivered"),
            "failed": sum(1 for d in deliveries if d.get("status") in ("photo_mismatch", "failed")),
            "pending": sum(1 for d in deliveries if d.get("status") == "pending"),
        }

    # ------------------------------------------------------------------
    # Incidents
    # ------------------------------------------------------------------

    def add_incident(
        self, incident_id: str, incident_type: str, severity: str,
        driver: str, description: str, logged_at: str,
    ) -> dict:
        self._append_row("Incidents", [incident_id, incident_type, severity, driver, description, logged_at, 0, ""])
        return {"id": incident_id, "type": incident_type, "severity": severity, "driver": driver,
                "description": description, "logged_at": logged_at, "resolved": 0, "resolved_at": ""}

    def get_all_incidents(self) -> list[dict]:
        records = self._get_all_records("Incidents")
        for r in records:
            r["resolved"] = bool(int(r.get("resolved", 0)))
        return sorted(records, key=lambda i: i.get("logged_at", ""), reverse=True)

    def count_incidents(self) -> int:
        return len(self.get_all_incidents())

    def resolve_incident(self, incident_id: str) -> None:
        row = self._find_row("Incidents", 1, incident_id)
        if row:
            ws = self._ws("Incidents")
            ws.update(f"G{row}:H{row}", [[1, self._now()]])

    # ------------------------------------------------------------------
    # Ops messages
    # ------------------------------------------------------------------

    def add_ops_message(
        self, msg_id: str, level: str, subject: str, body: str, sent_at: str,
    ) -> dict:
        self._append_row("OpsMessages", [msg_id, level, subject, body, sent_at])
        return {"id": msg_id, "level": level, "subject": subject, "body": body, "sent_at": sent_at}

    def get_all_ops_messages(self) -> list[dict]:
        records = self._get_all_records("OpsMessages")
        return sorted(records, key=lambda m: m.get("sent_at", ""), reverse=True)

    def count_ops_messages(self) -> int:
        return len(self.get_all_ops_messages())

    # ------------------------------------------------------------------
    # Photo verifications
    # ------------------------------------------------------------------

    def add_photo_verification(
        self, delivery_id: str, photo_path: str, expected_address: str,
        vision_result: str, address_found: str | None, match_result: str,
        confidence: float | None, details: str | None, verified_at: str,
    ) -> int:
        ws = self._ws("PhotoVerifications")
        all_records = ws.get_all_records()
        max_id = 0
        for r in all_records:
            try:
                max_id = max(max_id, int(r.get("id", 0)))
            except (ValueError, TypeError):
                pass
        new_id = max_id + 1
        self._append_row("PhotoVerifications", [
            new_id, delivery_id, photo_path, expected_address, vision_result,
            address_found or "", match_result, confidence or 0, details or "", verified_at,
        ])
        return new_id

    def get_verifications_for_delivery(self, delivery_id: str) -> list[dict]:
        records = self._get_all_records("PhotoVerifications")
        return [r for r in records if r.get("delivery_id") == delivery_id]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        pass  # No connection to close for Google Sheets


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_sheets_instance: GoogleSheetsDatabase | None = None


def get_sheets_db(sheet_id: str = GOOGLE_SHEET_ID) -> GoogleSheetsDatabase:
    """Get or create the global GoogleSheetsDatabase instance."""
    global _sheets_instance
    if _sheets_instance is None:
        _sheets_instance = GoogleSheetsDatabase(sheet_id)
    return _sheets_instance
