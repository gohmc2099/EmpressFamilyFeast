"""Empress Family Feast — Web Dashboard.

Flask application for managing drivers, viewing deliveries, incidents,
and ERIC's operational logs.
"""

from __future__ import annotations

import os
import sys

# Ensure project root is on the path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env BEFORE any db imports
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

import datetime
import random
import string
from flask import Flask, render_template, request, redirect, url_for, flash

from db import get_db
from db.seed import seed_database

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "empress-family-feast-dev-key")


def _init_db():
    get_db()
    seed_database()


def _generate_referral_code(db, name: str) -> str:
    base = "".join(ch for ch in name.upper() if ch.isalnum())[:5] or "EMP"
    for _ in range(25):
        code = f"{base}{''.join(random.choices(string.digits, k=4))}"
        if not db.referral_code_exists(code):
            return code
    return f"EMP{datetime.datetime.now().strftime('%H%M%S')}"


def _build_signup_link(referral_code: str) -> str:
    return url_for("customer_referral_signup", referral_code=referral_code, _external=True)


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
# Referrals
# -------------------------------------------------------------------------

@app.route("/referrals")
def referrals_dashboard():
    db = get_db()
    summary = db.get_referral_summary()
    referrers = db.get_all_referrers()
    for referrer in referrers:
        referrer["signup_link"] = _build_signup_link(referrer["referral_code"])
    referrals = db.get_all_referrals()
    return render_template(
        "referrals.html",
        summary=summary,
        referrers=referrers,
        referrals=referrals,
    )


@app.route("/referrals/referrers/add", methods=["POST"])
def add_referrer():
    db = get_db()
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    if not name or not email:
        flash("Referrer name and email are required.", "error")
        return redirect(url_for("referrals_dashboard"))

    code = request.form.get("referral_code", "").strip().upper()
    if not code:
        code = _generate_referral_code(db, name)

    try:
        db.add_referrer(name=name, email=email, phone=phone, referral_code=code)
    except Exception:
        flash("Could not add referrer. Email or referral code may already exist.", "error")
        return redirect(url_for("referrals_dashboard"))

    flash(f"Referrer '{name}' added with code {code}.", "success")
    return redirect(url_for("referrals_dashboard"))


@app.route("/referrals/add", methods=["POST"])
def add_referral():
    db = get_db()
    referral_code = request.form.get("referral_code", "").strip().upper()
    referred_name = request.form.get("referred_name", "").strip()
    referred_email = request.form.get("referred_email", "").strip().lower()
    notes = request.form.get("notes", "").strip()
    order_value_raw = request.form.get("order_value", "0").strip()

    if not referral_code or not referred_name or not referred_email:
        flash("Referral code, referred name, and referred email are required.", "error")
        return redirect(url_for("referrals_dashboard"))

    try:
        order_value = float(order_value_raw or 0)
        if order_value < 0:
            raise ValueError("Order value cannot be negative")
    except ValueError:
        flash("Order value must be a non-negative number.", "error")
        return redirect(url_for("referrals_dashboard"))

    try:
        referral = db.add_referral(
            referral_code=referral_code,
            referred_name=referred_name,
            referred_email=referred_email,
            order_value=order_value,
            notes=notes,
        )
    except Exception:
        flash("Could not log referral. This referred email may already be attached to the code.", "error")
        return redirect(url_for("referrals_dashboard"))

    if referral is None:
        flash("Referral code not found.", "error")
        return redirect(url_for("referrals_dashboard"))

    flash(f"Referral logged for {referred_name}.", "success")
    return redirect(url_for("referrals_dashboard"))


@app.route("/referrals/<int:referral_id>/status", methods=["POST"])
def update_referral_status(referral_id: int):
    db = get_db()
    status = request.form.get("status", "pending").strip().lower()
    reward_amount_raw = request.form.get("reward_amount", "0").strip()
    valid_statuses = {"pending", "converted", "cancelled"}

    if status not in valid_statuses:
        flash("Invalid referral status.", "error")
        return redirect(url_for("referrals_dashboard"))

    try:
        reward_amount = float(reward_amount_raw or 0)
        if reward_amount < 0:
            raise ValueError("Reward amount cannot be negative")
    except ValueError:
        flash("Reward amount must be a non-negative number.", "error")
        return redirect(url_for("referrals_dashboard"))

    if status != "converted":
        reward_amount = 0

    db.update_referral_status(referral_id=referral_id, status=status, reward_amount=reward_amount)
    flash(f"Referral #{referral_id} updated to {status}.", "success")
    return redirect(url_for("referrals_dashboard"))


@app.route("/refer/<referral_code>", methods=["GET", "POST"])
def customer_referral_signup(referral_code: str):
    db = get_db()
    code = referral_code.strip().upper()
    referrer = db.get_referrer_by_code(code)
    if referrer is None:
        return render_template("customer_referral_signup.html", referrer=None, referral_code=code), 404

    if request.method == "POST":
        referred_name = request.form.get("referred_name", "").strip()
        referred_email = request.form.get("referred_email", "").strip().lower()
        notes = request.form.get("notes", "").strip()

        if not referred_name or not referred_email:
            flash("Your name and email are required.", "error")
            return render_template(
                "customer_referral_signup.html",
                referrer=referrer,
                referral_code=code,
                submitted=False,
            )

        try:
            created = db.add_referral(
                referral_code=code,
                referred_name=referred_name,
                referred_email=referred_email,
                order_value=0.0,
                notes=notes,
            )
        except Exception:
            flash("This email is already registered with this referral code.", "error")
            return render_template(
                "customer_referral_signup.html",
                referrer=referrer,
                referral_code=code,
                submitted=False,
            )

        if created is None:
            flash("Referral code is no longer valid.", "error")
            return render_template(
                "customer_referral_signup.html",
                referrer=referrer,
                referral_code=code,
                submitted=False,
            )

        return redirect(url_for("customer_referral_signup", referral_code=code, submitted="1"))

    submitted = request.args.get("submitted", "") == "1"
    return render_template(
        "customer_referral_signup.html",
        referrer=referrer,
        referral_code=code,
        submitted=submitted,
    )


# -------------------------------------------------------------------------
# Error handling
# -------------------------------------------------------------------------

@app.errorhandler(Exception)
def handle_error(e):
    error_name = type(e).__name__
    flash(f"Error: {error_name} — {e}. Try refreshing in a few seconds.", "error")
    return redirect(url_for("index"))


# -------------------------------------------------------------------------
# Run
# -------------------------------------------------------------------------

_init_db()

if __name__ == "__main__":
    print("\n  Empress Family Feast Dashboard")
    print("  Open http://127.0.0.1:5000 in your browser\n")
    app.run(debug=True, port=5000)
