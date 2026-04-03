"""Logistics tools for ERIC — delivery operations monitoring and escalation.

These tools simulate the integrations ERIC would use in production:
driver management, delivery tracking, photo verification, and ops alerting.
"""

from __future__ import annotations

import datetime
import json
from typing import Any

from tools.registry import Tool, ToolRegistry

# ---------------------------------------------------------------------------
# In-memory data stores (simulate databases / external services)
# ---------------------------------------------------------------------------

_DRIVERS: dict[str, dict[str, Any]] = {
    "Marcus": {
        "status": "available",
        "vehicle": "Van #1 — Ford Transit",
        "vehicle_ok": True,
        "phone": "+44 7700 100001",
        "route": "North London",
        "last_seen": None,
    },
    "Amara": {
        "status": "available",
        "vehicle": "Van #2 — Mercedes Sprinter",
        "vehicle_ok": True,
        "phone": "+44 7700 100002",
        "route": "East London",
        "last_seen": None,
    },
    "Kwame": {
        "status": "available",
        "vehicle": "Van #3 — Peugeot Boxer",
        "vehicle_ok": True,
        "phone": "+44 7700 100003",
        "route": "South London",
        "last_seen": None,
    },
    "Fatima": {
        "status": "available",
        "vehicle": "Car #1 — Toyota Yaris",
        "vehicle_ok": True,
        "phone": "+44 7700 100004",
        "route": "West London",
        "last_seen": None,
    },
}

_DELIVERIES: list[dict[str, Any]] = [
    {"id": "DEL-001", "driver": "Marcus", "customer": "Mrs. Johnson", "address": "12 Maple Road, N1 2AB", "status": "pending", "photo_verified": False, "timestamp": None},
    {"id": "DEL-002", "driver": "Marcus", "customer": "Mr. Okafor", "address": "45 Elm Street, N4 3CD", "status": "pending", "photo_verified": False, "timestamp": None},
    {"id": "DEL-003", "driver": "Amara", "customer": "Ms. Chen", "address": "78 Oak Avenue, E8 1EF", "status": "pending", "photo_verified": False, "timestamp": None},
    {"id": "DEL-004", "driver": "Amara", "customer": "Mr. Patel", "address": "23 Birch Lane, E3 4GH", "status": "pending", "photo_verified": False, "timestamp": None},
    {"id": "DEL-005", "driver": "Kwame", "customer": "Mrs. Williams", "address": "56 Cedar Close, SE15 5IJ", "status": "pending", "photo_verified": False, "timestamp": None},
    {"id": "DEL-006", "driver": "Kwame", "customer": "Ms. Adeyemi", "address": "89 Pine Road, SE22 6KL", "status": "pending", "photo_verified": False, "timestamp": None},
    {"id": "DEL-007", "driver": "Fatima", "customer": "Mr. Brown", "address": "34 Willow Way, W5 7MN", "status": "pending", "photo_verified": False, "timestamp": None},
    {"id": "DEL-008", "driver": "Fatima", "customer": "Mrs. Mensah", "address": "67 Ash Drive, W12 8OP", "status": "pending", "photo_verified": False, "timestamp": None},
]

_INCIDENT_LOG: list[dict[str, Any]] = []
_OPS_MESSAGES: list[dict[str, Any]] = []

# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def driver_roll_call(**kwargs: Any) -> str:
    """Check in with all drivers and return their availability."""
    results = []
    for name, info in _DRIVERS.items():
        info["last_seen"] = _now()
        results.append(
            {
                "driver": name,
                "status": info["status"],
                "vehicle": info["vehicle"],
                "vehicle_ok": info["vehicle_ok"],
                "route": info["route"],
                "checked_in_at": info["last_seen"],
            }
        )
    return json.dumps(results, indent=2)


def get_driver_status(**kwargs: Any) -> str:
    """Get the current status of a specific driver."""
    name = kwargs["driver_name"]
    info = _DRIVERS.get(name)
    if info is None:
        return f"Error: driver '{name}' not found. Available: {', '.join(_DRIVERS.keys())}"
    return json.dumps({"driver": name, **info, "queried_at": _now()}, indent=2)


def get_todays_deliveries(**kwargs: Any) -> str:
    """Get all deliveries for today, optionally filtered by driver."""
    driver = kwargs.get("driver_name", "")
    deliveries = _DELIVERIES if not driver else [
        d for d in _DELIVERIES if d["driver"].lower() == driver.lower()
    ]
    return json.dumps(deliveries, indent=2)


def verify_proof_of_delivery(**kwargs: Any) -> str:
    """Verify a proof-of-delivery photo against the expected address.

    Simulates computer-vision address matching.
    """
    delivery_id = kwargs["delivery_id"]
    photo_address = kwargs["photo_address"]

    delivery = next((d for d in _DELIVERIES if d["id"] == delivery_id), None)
    if delivery is None:
        return f"Error: delivery '{delivery_id}' not found."

    expected = delivery["address"].lower().strip()
    submitted = photo_address.lower().strip()

    # Simple simulated match — in production this would be CV-based
    match = expected == submitted or expected.startswith(submitted.split(",")[0])

    timestamp = _now()
    delivery["photo_verified"] = match
    delivery["timestamp"] = timestamp

    if match:
        delivery["status"] = "delivered"
        return json.dumps({
            "delivery_id": delivery_id,
            "result": "VERIFIED",
            "expected_address": delivery["address"],
            "photo_address": photo_address,
            "driver": delivery["driver"],
            "customer": delivery["customer"],
            "verified_at": timestamp,
        }, indent=2)
    else:
        delivery["status"] = "photo_mismatch"
        return json.dumps({
            "delivery_id": delivery_id,
            "result": "MISMATCH",
            "expected_address": delivery["address"],
            "photo_address": photo_address,
            "driver": delivery["driver"],
            "customer": delivery["customer"],
            "flagged_at": timestamp,
            "action_required": "Escalate to ops — possible wrong delivery",
        }, indent=2)


def check_silent_drivers(**kwargs: Any) -> str:
    """Identify drivers who haven't reported in recently."""
    threshold_minutes = int(kwargs.get("threshold_minutes", 30))
    now = datetime.datetime.now()
    silent = []
    for name, info in _DRIVERS.items():
        if info["last_seen"] is None:
            silent.append({"driver": name, "last_seen": "never", "silent_minutes": "unknown"})
        else:
            last = datetime.datetime.strptime(info["last_seen"], "%Y-%m-%d %H:%M:%S")
            gap = (now - last).total_seconds() / 60
            if gap > threshold_minutes:
                silent.append({
                    "driver": name,
                    "last_seen": info["last_seen"],
                    "silent_minutes": round(gap, 1),
                })
    if not silent:
        return json.dumps({"status": "all_clear", "message": "All drivers reported in within threshold.", "checked_at": _now()}, indent=2)
    return json.dumps({"status": "silent_drivers_detected", "drivers": silent, "threshold_minutes": threshold_minutes, "checked_at": _now()}, indent=2)


def log_incident(**kwargs: Any) -> str:
    """Log a delivery incident with a timestamp."""
    incident = {
        "id": f"INC-{len(_INCIDENT_LOG) + 1:03d}",
        "type": kwargs["incident_type"],
        "severity": kwargs["severity"],
        "driver": kwargs.get("driver_name", "Unknown"),
        "description": kwargs["description"],
        "logged_at": _now(),
        "resolved": False,
    }
    _INCIDENT_LOG.append(incident)
    return json.dumps(incident, indent=2)


def send_ops_alert(**kwargs: Any) -> str:
    """Send an alert message to the operations team."""
    message = {
        "id": f"OPS-{len(_OPS_MESSAGES) + 1:03d}",
        "level": kwargs["level"],
        "subject": kwargs["subject"],
        "body": kwargs["body"],
        "sent_at": _now(),
    }
    _OPS_MESSAGES.append(message)
    return json.dumps({
        "status": "sent",
        "message": message,
    }, indent=2)


def get_delivery_summary(**kwargs: Any) -> str:
    """Generate a summary of all deliveries for the day."""
    completed = [d for d in _DELIVERIES if d["status"] == "delivered"]
    failed = [d for d in _DELIVERIES if d["status"] in ("photo_mismatch", "failed")]
    pending = [d for d in _DELIVERIES if d["status"] == "pending"]
    return json.dumps({
        "summary": {
            "total": len(_DELIVERIES),
            "completed": len(completed),
            "failed": len(failed),
            "pending": len(pending),
        },
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "incidents": _INCIDENT_LOG,
        "generated_at": _now(),
    }, indent=2)


def log_delivery_outcome(**kwargs: Any) -> str:
    """Log the final outcome of a delivery with a timestamp."""
    delivery_id = kwargs["delivery_id"]
    outcome = kwargs["outcome"]
    notes = kwargs.get("notes", "")

    delivery = next((d for d in _DELIVERIES if d["id"] == delivery_id), None)
    if delivery is None:
        return f"Error: delivery '{delivery_id}' not found."

    delivery["status"] = outcome
    delivery["timestamp"] = _now()
    return json.dumps({
        "delivery_id": delivery_id,
        "outcome": outcome,
        "notes": notes,
        "logged_at": delivery["timestamp"],
    }, indent=2)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_logistics_tools(registry: ToolRegistry) -> None:
    """Register all logistics tools into the given registry."""

    registry.register(Tool(
        name="driver_roll_call",
        description="Check in with all drivers and return their availability, vehicle readiness, and route assignments.",
        parameters={},
        function=driver_roll_call,
    ))

    registry.register(Tool(
        name="get_driver_status",
        description="Get the current status of a specific driver by name.",
        parameters={
            "driver_name": {"type": "string", "description": "Name of the driver (e.g. 'Marcus', 'Amara', 'Kwame', 'Fatima')"},
        },
        function=get_driver_status,
    ))

    registry.register(Tool(
        name="get_todays_deliveries",
        description="Get all deliveries for today. Optionally filter by driver name.",
        parameters={
            "driver_name": {"type": "string", "description": "Optional driver name to filter by (leave empty for all)"},
        },
        function=get_todays_deliveries,
    ))

    registry.register(Tool(
        name="verify_proof_of_delivery",
        description="Verify a proof-of-delivery photo by comparing the address in the photo against the expected customer address. Simulates computer-vision verification.",
        parameters={
            "delivery_id": {"type": "string", "description": "The delivery ID (e.g. 'DEL-001')"},
            "photo_address": {"type": "string", "description": "The address detected in the proof-of-delivery photo"},
        },
        function=verify_proof_of_delivery,
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
        description="Log a delivery incident (breakdown, sickness, wrong delivery, no-show, etc.) with a timestamp.",
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
        description="Send an alert message to the Empress Family Feast operations team.",
        parameters={
            "level": {"type": "string", "description": "Alert level: INFO, WARNING, URGENT, CRITICAL"},
            "subject": {"type": "string", "description": "Short subject line for the alert"},
            "body": {"type": "string", "description": "Full alert message body — should be actionable and concise"},
        },
        function=send_ops_alert,
    ))

    registry.register(Tool(
        name="get_delivery_summary",
        description="Generate a full delivery summary for the day: completed, failed, pending deliveries and all incidents.",
        parameters={},
        function=get_delivery_summary,
    ))

    registry.register(Tool(
        name="log_delivery_outcome",
        description="Log the final outcome of a specific delivery with a timestamp.",
        parameters={
            "delivery_id": {"type": "string", "description": "The delivery ID (e.g. 'DEL-001')"},
            "outcome": {"type": "string", "description": "Outcome: delivered, failed, returned, rescheduled"},
            "notes": {"type": "string", "description": "Optional notes about the delivery outcome"},
        },
        function=log_delivery_outcome,
    ))
