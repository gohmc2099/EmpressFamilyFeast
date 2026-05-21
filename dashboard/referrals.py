"""Referral routes for Empress Family Feast.

Provides:
- Admin pages for managing referrers and referrals (under /referrers and /referrals)
- Public-facing referral landing page (/r/<code>) where friends sign up

Reward rules (defaults; configurable via env vars):
- REFERRER_REWARD: credit awarded to the referrer when their referee places
  their first order (default: 10).
- REFEREE_REWARD: discount applied to the referee's first order (default: 5).
- REWARD_CURRENCY: display currency symbol (default: "GBP").
"""

from __future__ import annotations

import os
import secrets
import string

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)

from db import get_db


REFERRER_REWARD = float(os.environ.get("REFERRER_REWARD", "10"))
REFEREE_REWARD = float(os.environ.get("REFEREE_REWARD", "5"))
REWARD_CURRENCY = os.environ.get("REWARD_CURRENCY", "GBP")
CURRENCY_SYMBOLS = {"GBP": "£", "USD": "$", "EUR": "€"}
CURRENCY_SYMBOL = CURRENCY_SYMBOLS.get(REWARD_CURRENCY, REWARD_CURRENCY + " ")

CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_LENGTH = 8

bp = Blueprint("referrals", __name__)


def _generate_code() -> str:
    """Generate a unique referral code that isn't already in use."""
    db = get_db()
    for _ in range(20):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if not db.referrer_code_exists(code):
            return code
    raise RuntimeError("Could not generate unique referral code")


def _share_url(code: str) -> str:
    """Build an absolute share URL for a referral code."""
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if base:
        return f"{base}/r/{code}"
    return url_for("referrals.public_landing", code=code, _external=True)


@bp.app_context_processor
def _inject_currency():
    return {
        "currency_symbol": CURRENCY_SYMBOL,
        "referrer_reward": REFERRER_REWARD,
        "referee_reward": REFEREE_REWARD,
    }


# ---------------------------------------------------------------------------
# Admin: referrers list, add, detail, edit, delete
# ---------------------------------------------------------------------------

@bp.route("/referrers")
def referrers_list():
    db = get_db()
    referrers = db.get_all_referrers()
    referrals = db.get_all_referrals()
    counts = {}
    converted = {}
    for r in referrals:
        code = r.get("referrer_code")
        counts[code] = counts.get(code, 0) + 1
        if r.get("status") == "converted":
            converted[code] = converted.get(code, 0) + 1
    for r in referrers:
        r["referral_count"] = counts.get(r["code"], 0)
        r["converted_count"] = converted.get(r["code"], 0)
    return render_template("referrers.html", referrers=referrers)


@bp.route("/referrers/add", methods=["GET", "POST"])
def referrer_add():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Referrer name is required.", "error")
            return redirect(url_for("referrals.referrer_add"))
        code = request.form.get("code", "").strip().upper() or _generate_code()
        if db.referrer_code_exists(code):
            flash(f"Code '{code}' is already in use.", "error")
            return redirect(url_for("referrals.referrer_add"))
        db.add_referrer(
            code=code,
            name=name,
            email=request.form.get("email", "").strip(),
            phone=request.form.get("phone", "").strip(),
            notes=request.form.get("notes", "").strip(),
        )
        flash(f"Referrer '{name}' added with code {code}.", "success")
        return redirect(url_for("referrals.referrer_detail", code=code))
    suggested_code = _generate_code()
    return render_template(
        "referrer_form.html",
        referrer=None,
        action="Add",
        suggested_code=suggested_code,
    )


@bp.route("/referrers/<code>")
def referrer_detail(code):
    db = get_db()
    referrer = db.get_referrer(code)
    if not referrer:
        flash(f"Referrer '{code}' not found.", "error")
        return redirect(url_for("referrals.referrers_list"))
    referrals = db.get_referrals_by_referrer(code)
    return render_template(
        "referrer_detail.html",
        referrer=referrer,
        referrals=referrals,
        share_url=_share_url(code),
    )


@bp.route("/referrers/<code>/edit", methods=["GET", "POST"])
def referrer_edit(code):
    db = get_db()
    referrer = db.get_referrer(code)
    if not referrer:
        flash(f"Referrer '{code}' not found.", "error")
        return redirect(url_for("referrals.referrers_list"))
    if request.method == "POST":
        db.update_referrer(
            code=code,
            name=request.form.get("name", "").strip(),
            email=request.form.get("email", "").strip(),
            phone=request.form.get("phone", "").strip(),
            notes=request.form.get("notes", "").strip(),
        )
        flash(f"Referrer '{code}' updated.", "success")
        return redirect(url_for("referrals.referrer_detail", code=code))
    return render_template(
        "referrer_form.html",
        referrer=referrer,
        action="Edit",
        suggested_code=referrer["code"],
    )


@bp.route("/referrers/<code>/delete", methods=["POST"])
def referrer_delete(code):
    db = get_db()
    db.delete_referrer(code)
    flash(f"Referrer '{code}' deleted.", "success")
    return redirect(url_for("referrals.referrers_list"))


@bp.route("/referrers/<code>/payout", methods=["POST"])
def referrer_payout(code):
    db = get_db()
    referrer = db.get_referrer(code)
    if not referrer:
        flash(f"Referrer '{code}' not found.", "error")
        return redirect(url_for("referrals.referrers_list"))
    paid = referrer.get("credit_balance", 0)
    db.reset_referrer_credit(code)
    flash(
        f"Marked {CURRENCY_SYMBOL}{paid:.2f} as paid out to {referrer['name']}.",
        "success",
    )
    return redirect(url_for("referrals.referrer_detail", code=code))


# ---------------------------------------------------------------------------
# Admin: referrals list and status updates
# ---------------------------------------------------------------------------

@bp.route("/referrals")
def referrals_list():
    db = get_db()
    status_filter = request.args.get("status", "")
    referrals = db.get_all_referrals()
    if status_filter:
        referrals = [r for r in referrals if r.get("status") == status_filter]
    summary = db.get_referral_summary()
    return render_template(
        "referrals.html",
        referrals=referrals,
        summary=summary,
        status_filter=status_filter,
    )


@bp.route("/referrals/<int:referral_id>/mark/<status>", methods=["POST"])
def referral_mark(referral_id, status):
    if status not in ("pending", "signed_up", "converted", "expired"):
        flash(f"Invalid status '{status}'.", "error")
        return redirect(url_for("referrals.referrals_list"))
    db = get_db()
    ref = db.get_referral(referral_id)
    if not ref:
        flash(f"Referral #{referral_id} not found.", "error")
        return redirect(url_for("referrals.referrals_list"))
    previous_status = ref.get("status")
    db.update_referral_status(referral_id, status)
    if status == "converted" and previous_status != "converted":
        reward = float(ref.get("referrer_reward") or 0)
        if reward > 0:
            db.add_referrer_credit(ref["referrer_code"], reward)
            flash(
                f"Marked converted; awarded {CURRENCY_SYMBOL}{reward:.2f} credit to {ref['referrer_code']}.",
                "success",
            )
        else:
            flash("Marked as converted.", "success")
    else:
        flash(f"Referral #{referral_id} status set to '{status}'.", "success")
    return redirect(request.referrer or url_for("referrals.referrals_list"))


@bp.route("/referrals/<int:referral_id>/delete", methods=["POST"])
def referral_delete(referral_id):
    db = get_db()
    db.delete_referral(referral_id)
    flash(f"Referral #{referral_id} deleted.", "success")
    return redirect(request.referrer or url_for("referrals.referrals_list"))


# ---------------------------------------------------------------------------
# Public-facing landing page for a referral link
# ---------------------------------------------------------------------------

@bp.route("/r/<code>", methods=["GET", "POST"])
def public_landing(code):
    db = get_db()
    referrer = db.get_referrer(code)
    if not referrer:
        return render_template("referral_invalid.html", code=code), 404
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()
        if not name:
            flash("Please enter your name.", "error")
            return redirect(url_for("referrals.public_landing", code=code))
        if not email and not phone:
            flash("Please provide an email or phone number so we can reach you.", "error")
            return redirect(url_for("referrals.public_landing", code=code))
        referral = db.add_referral(
            referrer_code=code,
            referee_name=name,
            referee_email=email,
            referee_phone=phone,
            referee_message=message,
            status="signed_up",
            referrer_reward=REFERRER_REWARD,
            referee_reward=REFEREE_REWARD,
        )
        return render_template(
            "referral_thanks.html",
            referrer=referrer,
            referral=referral,
        )
    return render_template(
        "referral_landing.html",
        referrer=referrer,
        share_url=_share_url(code),
    )
