"""Logistics tools for ERIC — delivery operations monitoring and escalation.

All tools read from and write to the persistent SQLite database.
Photo verification uses Claude Vision for real image analysis.
"""

from __future__ import annotations

import datetime
import json
from typing import Any

from db.database import get_db
from tools.registry import Tool, ToolRegistry
from tools.vision import verify_delivery_photo_tool, analyse_photo_standalone_tool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Tool functions — all backed by SQLite
# ---------------------------------------------------------------------------


def driver_roll_call(**kwargs: Any) -> str:
    """Check in with all drivers and return their availability."""
    db = get_db()
    drivers = db.get_all_drivers()
    timestamp = _now()
    results = []
    for d in drivers:
        db.update_driver_last_seen(d["name"], timestamp)
        results.append({
            "driver": d["name"],
            "status": d["status"],
            "vehicle": d["vehicle"],
            "vehicle_ok": bool(d["vehicle_ok"]),
            "route": d["route"],
            "checked_in_at": timestamp,
        })
    return json.dumps(results, indent=2)


def get_driver_status(**kwargs: Any) -> str:
    """Get the current status of a specific driver."""
    db = get_db()
    name = kwargs["driver_name"]
    driver = db.get_driver(name)
    if driver is None:
        all_drivers = db.get_all_drivers()
        names = ", ".join(d["name"] for d in all_drivers)
        return f"Error: driver '{name}' not found. Available: {names}"
    driver["vehicle_ok"] = bool(driver["vehicle_ok"])
    driver["queried_at"] = _now()
    return json.dumps(driver, indent=2)


def get_todays_deliveries(**kwargs: Any) -> str:
    """Get all deliveries for today, optionally filtered by driver."""
    db = get_db()
    driver = kwargs.get("driver_name", "")
    if driver:
        deliveries = db.get_deliveries_by_driver(driver)
    else:
        deliveries = db.get_all_deliveries()
    # Convert sqlite3.Row int booleans
    for d in deliveries:
        d["photo_verified"] = bool(d["photo_verified"])
    return json.dumps(deliveries, indent=2)


def check_silent_drivers(**kwargs: Any) -> str:
    """Identify drivers who haven't reported in recently."""
    db = get_db()
    threshold_minutes = int(kwargs.get("threshold_minutes", 30))
    now = datetime.datetime.now()
    drivers = db.get_all_drivers()
    silent = []
    for d in drivers:
        if d["last_seen"] is None:
            silent.append({
                "driver": d["name"],
                "last_seen": "never",
                "silent_minutes": "unknown",
            })
        else:
            last = datetime.datetime.strptime(d["last_seen"], "%Y-%m-%d %H:%M:%S")
            gap = (now - last).total_seconds() / 60
            if gap > threshold_minutes:
                silent.append({
                    "driver": d["name"],
                    "last_seen": d["last_seen"],
                    "silent_minutes": round(gap, 1),
                })
    if not silent:
        return json.dumps({
            "status": "all_clear",
            "message": "All drivers reported in within threshold.",
            "checked_at": _now(),
        }, indent=2)
    return json.dumps({
        "status": "silent_drivers_detected",
        "drivers": silent,
        "threshold_minutes": threshold_minutes,
        "checked_at": _now(),
    }, indent=2)


def log_incident(**kwargs: Any) -> str:
    """Log a delivery incident with a timestamp."""
    db = get_db()
    incident_id = f"INC-{db.count_incidents() + 1:03d}"
    incident = db.add_incident(
        incident_id=incident_id,
        incident_type=kwargs["incident_type"],
        severity=kwargs["severity"],
        driver=kwargs.get("driver_name", "Unknown"),
        description=kwargs["description"],
        logged_at=_now(),
    )
    return json.dumps(incident, indent=2)


def send_ops_alert(**kwargs: Any) -> str:
    """Send an alert message to the operations team."""
    db = get_db()
    msg_id = f"OPS-{db.count_ops_messages() + 1:03d}"
    message = db.add_ops_message(
        msg_id=msg_id,
        level=kwargs["level"],
        subject=kwargs["subject"],
        body=kwargs["body"],
        sent_at=_now(),
    )
    return json.dumps({"status": "sent", "message": message}, indent=2)


def get_delivery_summary(**kwargs: Any) -> str:
    """Generate a summary of all deliveries for the day."""
    db = get_db()
    summary = db.get_delivery_summary()
    deliveries = db.get_all_deliveries()
    incidents = db.get_all_incidents()

    completed = [d for d in deliveries if d["status"] == "delivered"]
    failed = [d for d in deliveries if d["status"] in ("photo_mismatch", "failed")]
    pending = [d for d in deliveries if d["status"] == "pending"]

    for lst in (completed, failed, pending):
        for d in lst:
            d["photo_verified"] = bool(d["photo_verified"])

    return json.dumps({
        "summary": summary,
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "incidents": incidents,
        "generated_at": _now(),
    }, indent=2)


def log_delivery_outcome(**kwargs: Any) -> str:
    """Log the final outcome of a delivery with a timestamp."""
    db = get_db()
    delivery_id = kwargs["delivery_id"]
    outcome = kwargs["outcome"]
    notes = kwargs.get("notes", "")

    delivery = db.get_delivery(delivery_id)
    if delivery is None:
        return f"Error: delivery '{delivery_id}' not found."

    timestamp = _now()
    db.update_delivery_status(delivery_id, outcome, timestamp)
    return json.dumps({
        "delivery_id": delivery_id,
        "outcome": outcome,
        "notes": notes,
        "logged_at": timestamp,
    }, indent=2)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_logistics_tools(registry: ToolRegistry) -> None:
    """Register all logistics tools (database-backed + Claude Vision)."""

    registry.register(Tool(
        name="driver_roll_call",
        description="Check in with all drivers and return their availability, vehicle readiness, and route assignments. Data is persisted to the database.",
        parameters={},
        function=driver_roll_call,
    ))

    registry.register(Tool(
        name="get_driver_status",
        description="Get the current status of a specific driver by name from the database.",
        parameters={
            "driver_name": {"type": "string", "description": "Name of the driver (e.g. 'Marcus', 'Amara', 'Kwame', 'Fatima')"},
        },
        function=get_driver_status,
    ))

    registry.register(Tool(
        name="get_todays_deliveries",
        description="Get all deliveries for today from the database. Optionally filter by driver name.",
        parameters={
            "driver_name": {"type": "string", "description": "Optional driver name to filter by (leave empty for all)"},
        },
        function=get_todays_deliveries,
    ))

    registry.register(Tool(
        name="verify_delivery_photo",
        description=(
            "Verify a proof-of-delivery photo using Claude Vision AI. "
            "Analyses the image for visible address evidence, compares against "
            "the expected customer address, checks for delivery evidence, and "
            "persists the result to the database. Requires a local image file path."
        ),
        parameters={
            "delivery_id": {"type": "string", "description": "The delivery ID (e.g. 'DEL-001')"},
            "image_path": {"type": "string", "description": "Path to the proof-of-delivery photo file (.jpg, .png, .webp, .gif)"},
        },
        function=verify_delivery_photo_tool,
    ))

    registry.register(Tool(
        name="analyse_photo",
        description=(
            "Analyse any photo using Claude Vision AI. Use this for general "
            "photo inspection when you don't have a specific delivery ID, or "
            "to examine images for any purpose."
        ),
        parameters={
            "image_path": {"type": "string", "description": "Path to the image file"},
            "description": {"type": "string", "description": "What to look for or describe about the photo"},
        },
        function=analyse_photo_standalone_tool,
    ))

    registry.register(Tool(
        name="check_silent_drivers",
        description="Check for drivers who haven't reported in recently. Returns any drivers who have been silent beyond the threshold.",
        parameters={
            "threshold_minutes": {"type": "string", "description": "Minutes of silence before flagging (default: 30)"},
        },
        function=check_silent_drivers,
    ))

    registry.register(Tool(
        name="log_incident",
        description="Log a delivery incident (breakdown, sickness, wrong delivery, no-show, etc.) to the database with a timestamp.",
        parameters={
            "incident_type": {"type": "string", "description": "Type of incident: breakdown, sickness, wrong_delivery, no_show, delay, other"},
            "severity": {"type": "string", "description": "Severity level: INFO, WARNING, URGENT, CRITICAL"},
            "driver_name": {"type": "string", "description": "Name of the driver involved"},
            "description": {"type": "string", "description": "Brief factual description of the incident"},
        },
        function=log_incident,
    ))

    registry.register(Tool(
        name="send_ops_alert",
        description="Send an alert message to the Empress Family Feast operations team. Alert is persisted to the database.",
        parameters={
            "level": {"type": "string", "description": "Alert level: INFO, WARNING, URGENT, CRITICAL"},
            "subject": {"type": "string", "description": "Short subject line for the alert"},
            "body": {"type": "string", "description": "Full alert message body — should be actionable and concise"},
        },
        function=send_ops_alert,
    ))

    registry.register(Tool(
        name="get_delivery_summary",
        description="Generate a full delivery summary from the database: completed, failed, pending deliveries and all incidents.",
        parameters={},
        function=get_delivery_summary,
    ))

    registry.register(Tool(
        name="log_delivery_outcome",
        description="Log the final outcome of a specific delivery to the database with a timestamp.",
        parameters={
            "delivery_id": {"type": "string", "description": "The delivery ID (e.g. 'DEL-001')"},
            "outcome": {"type": "string", "description": "Outcome: delivered, failed, returned, rescheduled"},
            "notes": {"type": "string", "description": "Optional notes about the delivery outcome"},
        },
        function=log_delivery_outcome,
    ))
