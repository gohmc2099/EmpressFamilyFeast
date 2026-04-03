"""Seed the database with initial driver and delivery data.

Works with both Google Sheets and SQLite — uses the shared interface.
Run this once to populate a fresh database, or to reset to defaults.
"""

from __future__ import annotations

from db import get_db


SEED_DRIVERS = [
    {"name": "Marcus", "vehicle": "Van #1 — Ford Transit", "phone": "+44 7700 100001", "route": "North London", "whatsapp_group": "North London Drivers"},
    {"name": "Amara", "vehicle": "Van #2 — Mercedes Sprinter", "phone": "+44 7700 100002", "route": "East London", "whatsapp_group": "East London Drivers"},
    {"name": "Kwame", "vehicle": "Van #3 — Peugeot Boxer", "phone": "+44 7700 100003", "route": "South London", "whatsapp_group": "South London Drivers"},
    {"name": "Fatima", "vehicle": "Car #1 — Toyota Yaris", "phone": "+44 7700 100004", "route": "West London", "whatsapp_group": "West London Drivers"},
]

SEED_SCHEDULES = {
    "Marcus": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "Amara": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "Kwame": ["Monday", "Wednesday", "Friday", "Saturday"],
    "Fatima": ["Tuesday", "Thursday", "Saturday"],
}

SEED_DELIVERIES = [
    {"id": "DEL-001", "driver": "Marcus", "customer": "Mrs. Johnson", "address": "12 Maple Road, N1 2AB"},
    {"id": "DEL-002", "driver": "Marcus", "customer": "Mr. Okafor", "address": "45 Elm Street, N4 3CD"},
    {"id": "DEL-003", "driver": "Amara", "customer": "Ms. Chen", "address": "78 Oak Avenue, E8 1EF"},
    {"id": "DEL-004", "driver": "Amara", "customer": "Mr. Patel", "address": "23 Birch Lane, E3 4GH"},
    {"id": "DEL-005", "driver": "Kwame", "customer": "Mrs. Williams", "address": "56 Cedar Close, SE15 5IJ"},
    {"id": "DEL-006", "driver": "Kwame", "customer": "Ms. Adeyemi", "address": "89 Pine Road, SE22 6KL"},
    {"id": "DEL-007", "driver": "Fatima", "customer": "Mr. Brown", "address": "34 Willow Way, W5 7MN"},
    {"id": "DEL-008", "driver": "Fatima", "customer": "Mrs. Mensah", "address": "67 Ash Drive, W12 8OP"},
]


def seed_database(reset: bool = False) -> None:
    """Insert seed data using the shared database interface (Sheets or SQLite)."""
    db = get_db()

    # Only seed drivers if none exist
    if db.count_drivers() == 0:
        for d in SEED_DRIVERS:
            db.add_driver(**d)
        print(f"Seeded {len(SEED_DRIVERS)} drivers.")

        for driver_name, active_days in SEED_SCHEDULES.items():
            db.set_driver_schedule(driver_name, active_days)
        print(f"Seeded schedules for {len(SEED_SCHEDULES)} drivers.")

    # Only seed deliveries if none exist
    existing_deliveries = db.get_all_deliveries()
    if len(existing_deliveries) == 0:
        # Use the adapter's interface — Google Sheets uses _append_row, SQLite uses SQL
        has_append = hasattr(db, '_append_row')
        if has_append:
            import datetime
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for d in SEED_DELIVERIES:
                db._append_row("Deliveries", [
                    d["id"], d["driver"], d["customer"], d["address"],
                    "pending", 0, "", "", "", now,
                ])
        else:
            # SQLite path
            db.conn.executemany(
                "INSERT INTO deliveries (id, driver, customer, address) VALUES (?, ?, ?, ?)",
                [(d["id"], d["driver"], d["customer"], d["address"]) for d in SEED_DELIVERIES],
            )
            db.conn.commit()
        print(f"Seeded {len(SEED_DELIVERIES)} deliveries.")


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from dotenv import load_dotenv
    load_dotenv()
    reset = "--reset" in sys.argv
    seed_database(reset=reset)
    print("Database seeded successfully.")
