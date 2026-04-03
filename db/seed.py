"""Seed the database with initial driver and delivery data.

Run this once to populate a fresh database, or to reset to defaults.
"""

from __future__ import annotations

from db.database import get_db


SEED_DRIVERS = [
    ("Marcus", "available", "Van #1 — Ford Transit", 1, "+44 7700 100001", "North London"),
    ("Amara", "available", "Van #2 — Mercedes Sprinter", 1, "+44 7700 100002", "East London"),
    ("Kwame", "available", "Van #3 — Peugeot Boxer", 1, "+44 7700 100003", "South London"),
    ("Fatima", "available", "Car #1 — Toyota Yaris", 1, "+44 7700 100004", "West London"),
]

SEED_DELIVERIES = [
    ("DEL-001", "Marcus", "Mrs. Johnson", "12 Maple Road, N1 2AB"),
    ("DEL-002", "Marcus", "Mr. Okafor", "45 Elm Street, N4 3CD"),
    ("DEL-003", "Amara", "Ms. Chen", "78 Oak Avenue, E8 1EF"),
    ("DEL-004", "Amara", "Mr. Patel", "23 Birch Lane, E3 4GH"),
    ("DEL-005", "Kwame", "Mrs. Williams", "56 Cedar Close, SE15 5IJ"),
    ("DEL-006", "Kwame", "Ms. Adeyemi", "89 Pine Road, SE22 6KL"),
    ("DEL-007", "Fatima", "Mr. Brown", "34 Willow Way, W5 7MN"),
    ("DEL-008", "Fatima", "Mrs. Mensah", "67 Ash Drive, W12 8OP"),
]


def seed_database(reset: bool = False) -> None:
    """Insert seed data. If reset=True, clears existing data first."""
    db = get_db()

    if reset:
        db.conn.executescript("""
            DELETE FROM photo_verifications;
            DELETE FROM incidents;
            DELETE FROM ops_messages;
            DELETE FROM deliveries;
            DELETE FROM drivers;
        """)

    # Only seed if tables are empty
    if db.count_drivers() == 0:
        db.conn.executemany(
            "INSERT INTO drivers (name, status, vehicle, vehicle_ok, phone, route) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            SEED_DRIVERS,
        )
        db.conn.commit()
        print(f"Seeded {len(SEED_DRIVERS)} drivers.")

    delivery_count = db.conn.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0]
    if delivery_count == 0:
        db.conn.executemany(
            "INSERT INTO deliveries (id, driver, customer, address) "
            "VALUES (?, ?, ?, ?)",
            SEED_DELIVERIES,
        )
        db.conn.commit()
        print(f"Seeded {len(SEED_DELIVERIES)} deliveries.")


if __name__ == "__main__":
    import sys
    reset = "--reset" in sys.argv
    seed_database(reset=reset)
    print("Database seeded successfully.")
