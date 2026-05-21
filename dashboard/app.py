"""Empress Family Feast — Web Dashboard.

Flask application for managing drivers, viewing deliveries, incidents,
and ERIC's operational logs.
"""

from __future__ import annotations

import os
import secrets
import sys

# Ensure project root is on the path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env BEFORE any db imports
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

import datetime
from flask import Flask, render_template, request, redirect, url_for, flash

from db import get_db
from db.seed import seed_database

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "empress-family-feast-dev-key")

REFERRAL_STATUSES = [
    ("new", "New"),
    ("contacted", "Contacted"),
    ("eligible", "Eligible"),
    ("scheduled", "Scheduled"),
    ("enrolled", "Enrolled"),
    ("declined", "Declined"),
]
REFERRAL_STATUS_LABELS = dict(REFERRAL_STATUSES)
REFERRAL_STATUS_BADGES = {
    "new": "badge-yellow",
    "contacted": "badge-blue",
    "eligible": "badge-green",
    "scheduled": "badge-blue",
    "enrolled": "badge-green",
    "declined": "badge-red",
}


def _init_db():
    get_db()
    seed_database()


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _new_referral_id(db) -> str:
    today = datetime.datetime.now().strftime("%Y%m%d")
    for _ in range(10):
        referral_id = f"REF-{today}-{secrets.token_hex(2).upper()}"
        if db.get_referral(referral_id) is None:
            return referral_id
    return f"REF-{today}-{secrets.token_hex(4).upper()}"


def _referral_form_data() -> dict:
    return {
        "referrer_name": request.form.get("referrer_name", "").strip(),
        "referrer_phone": request.form.get("referrer_phone", "").strip(),
        "referrer_email": request.form.get("referrer_email", "").strip(),
        "family_name": request.form.get("family_name", "").strip(),
        "contact_name": request.form.get("contact_name", "").strip(),
        "contact_phone": request.form.get("contact_phone", "").strip(),
        "contact_email": request.form.get("contact_email", "").strip(),
        "address": request.form.get("address", "").strip(),
        "postcode": request.form.get("postcode", "").strip(),
        "household_size": request.form.get("household_size", "1").strip(),
        "preferred_contact": request.form.get("preferred_contact", "phone").strip(),
        "dietary_needs": request.form.get("dietary_needs", "").strip(),
        "reason": request.form.get("reason", "").strip(),
        "consent": request.form.get("consent") == "on",
    }


def _validate_referral_form(form: dict) -> list[str]:
    errors = []
    required_fields = {
        "referrer_name": "Your name is required.",
        "referrer_phone": "Your phone number is required.",
        "family_name": "Family name is required.",
        "contact_phone": "A contact phone number for the family is required.",
        "address": "Delivery address is required.",
    }
    for field, message in required_fields.items():
        if not form[field]:
            errors.append(message)

    try:
        household_size = int(form["household_size"])
    except ValueError:
        household_size = 0
    if household_size < 1:
        errors.append("Household size must be at least 1.")

    if form["preferred_contact"] not in {"phone", "email", "whatsapp"}:
        errors.append("Preferred contact method is invalid.")

    if not form["consent"]:
        errors.append("Consent is required before submitting a referral.")

    return errors


def _decorate_referral(referral: dict) -> dict:
    status = referral.get("status", "new")
    referral["status_label"] = REFERRAL_STATUS_LABELS.get(status, status.title())
    referral["badge_class"] = REFERRAL_STATUS_BADGES.get(status, "badge-blue")
    return referral


# -------------------------------------------------------------------------
# Dashboard home
# -------------------------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    summary = db.get_delivery_summary()
    referral_summary = db.get_referral_summary()
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
        referral_summary=referral_summary,
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
# Referrals
# -------------------------------------------------------------------------

@app.route("/refer", methods=["GET", "POST"])
def referral_public():
    if request.method == "POST":
        form = _referral_form_data()
        errors = _validate_referral_form(form)
        if errors:
            return render_template("refer.html", form=form, errors=errors)

        db = get_db()
        referral = db.add_referral(
            referral_id=_new_referral_id(db),
            referrer_name=form["referrer_name"],
            referrer_phone=form["referrer_phone"],
            referrer_email=form["referrer_email"],
            family_name=form["family_name"],
            contact_name=form["contact_name"],
            contact_phone=form["contact_phone"],
            contact_email=form["contact_email"],
            address=form["address"],
            postcode=form["postcode"],
            household_size=int(form["household_size"]),
            preferred_contact=form["preferred_contact"],
            dietary_needs=form["dietary_needs"],
            reason=form["reason"],
            consent=form["consent"],
            created_at=_now(),
        )
        return render_template("referral_success.html", referral=referral)

    return render_template("refer.html", form={}, errors=[])


@app.route("/referrals")
def referrals_list():
    db = get_db()
    status_filter = request.args.get("status", "").strip()
    query = request.args.get("q", "").strip().lower()
    referrals = [_decorate_referral(r) for r in db.get_all_referrals()]

    if status_filter:
        referrals = [r for r in referrals if r.get("status") == status_filter]
    if query:
        referrals = [
            r for r in referrals
            if query in " ".join([
                r.get("id", ""),
                r.get("family_name", ""),
                r.get("contact_name", ""),
                r.get("contact_phone", ""),
                r.get("postcode", ""),
            ]).lower()
        ]

    return render_template(
        "referrals.html",
        referrals=referrals,
        statuses=REFERRAL_STATUSES,
        status_filter=status_filter,
        query=query,
        summary=db.get_referral_summary(),
    )


@app.route("/referrals/<referral_id>", methods=["GET", "POST"])
def referral_detail(referral_id):
    db = get_db()
    referral = db.get_referral(referral_id)
    if referral is None:
        flash(f"Referral '{referral_id}' not found.", "error")
        return redirect(url_for("referrals_list"))

    if request.method == "POST":
        status = request.form.get("status", "new").strip()
        notes = request.form.get("notes", "").strip()
        valid_statuses = {value for value, _label in REFERRAL_STATUSES}
        if status not in valid_statuses:
            flash("Referral status is invalid.", "error")
            return redirect(url_for("referral_detail", referral_id=referral_id))

        db.update_referral_status(referral_id, status, notes, _now())
        flash(f"Referral {referral_id} updated.", "success")
        return redirect(url_for("referral_detail", referral_id=referral_id))

    return render_template(
        "referral_detail.html",
        referral=_decorate_referral(referral),
        statuses=REFERRAL_STATUSES,
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
