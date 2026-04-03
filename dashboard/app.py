"""Empress Family Feast — Web Dashboard.

Flask application for managing drivers, viewing deliveries, incidents,
and ERIC's operational logs.
"""

from __future__ import annotations

import os
import sys

# Ensure project root is on the path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import datetime
from flask import Flask, render_template, request, redirect, url_for, flash

from db.database import get_db
from db.seed import seed_database

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "empress-family-feast-dev-key")


def _init_db():
    get_db()
    seed_database()


# -------------------------------------------------------------------------
# Dashboard home
# -------------------------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    summary = db.get_delivery_summary()
    incidents = db.get_all_incidents()
    drivers = db.get_all_drivers()
    open_incidents = [i for i in incidents if not i["resolved"]]
    recent_ops = db.get_all_ops_messages()[:5]

    today = datetime.datetime.now().strftime("%A")
    active_today = []
    for d in drivers:
        schedule = db.get_driver_schedule(d["name"])
        if schedule.get(today, False):
            active_today.append(d["name"])

    return render_template(
        "index.html",
        summary=summary,
        drivers=drivers,
        active_today=active_today,
        open_incidents=open_incidents,
        recent_ops=recent_ops,
        today=today,
    )


# -------------------------------------------------------------------------
# Drivers
# -------------------------------------------------------------------------

@app.route("/drivers")
def drivers_list():
    db = get_db()
    drivers = db.get_all_drivers()
    for d in drivers:
        d["stops"] = db.get_stops_for_driver(d["name"])
        d["schedule"] = db.get_driver_schedule(d["name"])
    return render_template("drivers.html", drivers=drivers)


@app.route("/drivers/add", methods=["GET", "POST"])
def driver_add():
    db = get_db()
    days = db.DAYS_OF_WEEK
    if request.method == "POST":
        name = request.form["name"].strip()
        if not name:
            flash("Driver name is required.", "error")
            return redirect(url_for("driver_add"))
        if db.driver_exists(name):
            flash(f"Driver '{name}' already exists.", "error")
            return redirect(url_for("driver_add"))
        db.add_driver(
            name=name,
            vehicle=request.form.get("vehicle", "").strip(),
            phone=request.form.get("phone", "").strip(),
            route=request.form.get("route", "").strip(),
            whatsapp_group=request.form.get("whatsapp_group", "").strip(),
        )
        active_days = request.form.getlist("active_days")
        db.set_driver_schedule(name, active_days)
        flash(f"Driver '{name}' added.", "success")
        return redirect(url_for("drivers_list"))
    return render_template("driver_form.html", driver=None, days=days, action="Add")


@app.route("/drivers/<name>/edit", methods=["GET", "POST"])
def driver_edit(name):
    db = get_db()
    driver = db.get_driver(name)
    days = db.DAYS_OF_WEEK
    if driver is None:
        flash(f"Driver '{name}' not found.", "error")
        return redirect(url_for("drivers_list"))
    if request.method == "POST":
        db.update_driver(
            name=name,
            vehicle=request.form.get("vehicle", "").strip(),
            phone=request.form.get("phone", "").strip(),
            route=request.form.get("route", "").strip(),
            whatsapp_group=request.form.get("whatsapp_group", "").strip(),
            status=request.form.get("status", "available").strip(),
        )
        active_days = request.form.getlist("active_days")
        db.set_driver_schedule(name, active_days)
        flash(f"Driver '{name}' updated.", "success")
        return redirect(url_for("drivers_list"))
    driver["schedule"] = db.get_driver_schedule(name)
    return render_template("driver_form.html", driver=driver, days=days, action="Edit")


@app.route("/drivers/<name>/delete", methods=["POST"])
def driver_delete(name):
    db = get_db()
    db.delete_driver(name)
    flash(f"Driver '{name}' deleted.", "success")
    return redirect(url_for("drivers_list"))


# -------------------------------------------------------------------------
# Stops
# -------------------------------------------------------------------------

@app.route("/drivers/<name>/stops")
def driver_stops(name):
    db = get_db()
    driver = db.get_driver(name)
    if driver is None:
        flash(f"Driver '{name}' not found.", "error")
        return redirect(url_for("drivers_list"))
    stops = db.get_stops_for_driver(name)
    return render_template("stops.html", driver=driver, stops=stops)


@app.route("/drivers/<name>/stops/add", methods=["POST"])
def stop_add(name):
    db = get_db()
    customer = request.form.get("customer", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()
    if not customer or not address:
        flash("Customer and address are required.", "error")
        return redirect(url_for("driver_stops", name=name))
    existing = db.get_stops_for_driver(name)
    order = len(existing) + 1
    db.add_stop(driver=name, customer=customer, address=address, notes=notes, stop_order=order)
    flash(f"Stop added for {name}.", "success")
    return redirect(url_for("driver_stops", name=name))


@app.route("/stops/<int:stop_id>/delete", methods=["POST"])
def stop_delete(stop_id):
    db = get_db()
    row = db.conn.execute("SELECT driver FROM stops WHERE id = ?", (stop_id,)).fetchone()
    driver_name = row["driver"] if row else ""
    db.delete_stop(stop_id)
    flash("Stop removed.", "success")
    return redirect(url_for("driver_stops", name=driver_name) if driver_name else url_for("drivers_list"))


# -------------------------------------------------------------------------
# Weekly schedule
# -------------------------------------------------------------------------

@app.route("/schedule")
def schedule():
    db = get_db()
    weekly = db.get_weekly_schedule()
    days = db.DAYS_OF_WEEK
    return render_template("schedule.html", weekly=weekly, days=days)


# -------------------------------------------------------------------------
# Deliveries
# -------------------------------------------------------------------------

@app.route("/deliveries")
def deliveries_list():
    db = get_db()
    status_filter = request.args.get("status", "")
    driver_filter = request.args.get("driver", "")
    deliveries = db.get_all_deliveries()
    if status_filter:
        deliveries = [d for d in deliveries if d["status"] == status_filter]
    if driver_filter:
        deliveries = [d for d in deliveries if d["driver"] == driver_filter]
    for d in deliveries:
        d["photo_verified"] = bool(d["photo_verified"])
    drivers = db.get_all_drivers()
    return render_template(
        "deliveries.html",
        deliveries=deliveries,
        drivers=drivers,
        status_filter=status_filter,
        driver_filter=driver_filter,
    )


# -------------------------------------------------------------------------
# Incidents
# -------------------------------------------------------------------------

@app.route("/incidents")
def incidents_list():
    db = get_db()
    incidents = db.get_all_incidents()
    return render_template("incidents.html", incidents=incidents)


@app.route("/incidents/<incident_id>/resolve", methods=["POST"])
def incident_resolve(incident_id):
    db = get_db()
    db.resolve_incident(incident_id)
    flash(f"Incident {incident_id} marked as resolved.", "success")
    return redirect(url_for("incidents_list"))


# -------------------------------------------------------------------------
# ERIC logs (ops messages)
# -------------------------------------------------------------------------

@app.route("/logs")
def logs():
    db = get_db()
    ops_messages = db.get_all_ops_messages()
    return render_template("logs.html", ops_messages=ops_messages)


# -------------------------------------------------------------------------
# Run
# -------------------------------------------------------------------------

if __name__ == "__main__":
    _init_db()
    print("\n  Empress Family Feast Dashboard")
    print("  Open http://127.0.0.1:5000 in your browser\n")
    app.run(debug=True, port=5000)
