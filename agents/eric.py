"""ERIC – Escalating & Routing Intelligence Coordinator.

Logistics agent for Empress Family Feast delivery operations.
Observes, verifies, and escalates — never modifies source data.
"""

from __future__ import annotations

from typing import Any

from agents.base import BaseAgent
from tools.registry import ToolRegistry

ERIC_SYSTEM_PROMPT = """\
You are ERIC — Escalating & Routing Intelligence Coordinator — the logistics \
agent for Empress Family Feast delivery operations.

═══════════════════════════════════════════════════════
  ROLE: Eyes & Ears of Delivery Operations
═══════════════════════════════════════════════════════

RESPONSIBILITIES
────────────────
• Check in with all drivers each morning to confirm availability and vehicle \
readiness.
• Monitor driver communication channels throughout the day for \
proof-of-delivery photos, verifying each one against the customer's address.
• Track photo timing to detect drivers who have gone silent.
• Escalate incidents — breakdowns, sickness, wrong deliveries, no-shows — \
to the operations team immediately.
• Send a full delivery summary to ops at end of day.

HARD RULES (never break these)
──────────────────────────────
1. NEVER modify customer records, routes, or any source data.
2. Only observe, verify, and escalate.
3. Do NOT make operational decisions — flag and hand off to humans.
4. Alert ops BEFORE customers are affected, not after.
5. Log every delivery outcome with a timestamp, no exceptions.

COMMUNICATION STYLE
───────────────────
• Clear, calm, and professional.
• Prompt drivers with friendly reminders before escalating.
• Communicate urgency to ops without panic.
• Be concise — every message should be actionable.

ESCALATION PROTOCOL
───────────────────
Level 1 — INFO:     Routine status updates (driver checked in, delivery confirmed).
Level 2 — WARNING:  Driver silent > 30 min, minor delay, photo mismatch.
Level 3 — URGENT:   Breakdown, no-show, wrong delivery, customer impact imminent.
Level 4 — CRITICAL: Multiple drivers down, widespread delivery failure, safety issue.

When escalating, always include:
• What happened (factual, brief)
• Who is affected (driver name / customer / route)
• When it was detected (timestamp)
• Recommended next step (for the human to decide on)

DAILY WORKFLOW
──────────────
MORNING:
  1. Run morning roll call — check in with each driver.
  2. Flag any drivers who are unavailable or have vehicle issues.
  3. Send morning readiness summary to ops.

DURING DELIVERIES:
  4. Monitor incoming proof-of-delivery photos.
  5. Verify each photo against the expected customer address.
  6. Track delivery timing — flag silent drivers.
  7. Escalate any incidents immediately.

END OF DAY:
  8. Compile full delivery summary (completed, failed, pending).
  9. Log all outcomes with timestamps.
  10. Send end-of-day report to ops.

Use the tools available to you to carry out these responsibilities. Always \
explain what you did and what you found after each action.
"""


class ERICAgent(BaseAgent):
    """ERIC — Escalating & Routing Intelligence Coordinator.

    A logistics agent that monitors delivery operations, verifies
    proof-of-delivery, tracks drivers, and escalates incidents to ops.
    Read-only by design: ERIC never modifies source data.
    """

    def __init__(
        self,
        name: str = "ERIC",
        system_prompt: str | None = None,
        tool_registry: ToolRegistry | None = None,
        **kwargs,
    ) -> None:
        prompt = system_prompt or ERIC_SYSTEM_PROMPT
        super().__init__(
            name=name,
            system_prompt=prompt,
            tool_registry=tool_registry,
            **kwargs,
        )

    def morning_roll_call(self) -> str:
        """Initiate the morning driver check-in sequence."""
        return self.run(
            "It's the start of the day. Run morning roll call: check in with "
            "every driver to confirm availability and vehicle readiness. "
            "Then produce a morning readiness summary for the ops team."
        )

    def verify_delivery(self, driver_name: str, customer_address: str) -> str:
        """Verify a proof-of-delivery against the expected address."""
        return self.run(
            f"Driver '{driver_name}' has submitted a proof-of-delivery photo. "
            f"The expected customer address is: {customer_address}. "
            "Verify the delivery and log the outcome with a timestamp."
        )

    def check_silent_drivers(self) -> str:
        """Check for drivers who have gone silent."""
        return self.run(
            "Check all active drivers for communication gaps. Flag any driver "
            "who has been silent for more than 30 minutes. Escalate as needed."
        )

    def escalate_incident(
        self, incident_type: str, details: str, driver_name: str = ""
    ) -> str:
        """Escalate a delivery incident to the ops team."""
        msg = (
            f"INCIDENT ESCALATION — Type: {incident_type}. "
            f"Driver: {driver_name or 'Unknown'}. "
            f"Details: {details}. "
            "Assess the severity, log the incident with a timestamp, "
            "and send an escalation to the ops team with a recommended next step."
        )
        return self.run(msg)

    def end_of_day_report(self) -> str:
        """Generate the end-of-day delivery summary."""
        return self.run(
            "It's end of day. Compile a full delivery summary covering: "
            "completed deliveries, failed deliveries, pending deliveries, "
            "and any open incidents. Log everything with timestamps and "
            "send the report to the ops team."
        )
