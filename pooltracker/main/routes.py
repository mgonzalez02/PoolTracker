from datetime import timedelta

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pooltracker.extensions import db
from pooltracker.main import main_bp
from pooltracker.main.forms import ChemicalAdditionForm, ReadingForm
from pooltracker.models import ADDITION_FIELDS, READING_FIELDS, ChemicalAddition, Reading
from pooltracker.models import timestamp_for_date, utcnow


@main_bp.route("/")
@login_required
def dashboard():
    last_addition = ChemicalAddition.query.order_by(ChemicalAddition.timestamp.desc()).first()
    last_reading = Reading.query.order_by(Reading.timestamp.desc()).first()
    return render_template(
        "main/dashboard.html",
        reading_fields=READING_FIELDS,
        trend_window_days=current_app.config["TREND_WINDOW_DAYS"],
        last_addition=last_addition,
        last_reading=last_reading,
    )


@main_bp.route("/api/trends")
@login_required
def trends_api():
    view = request.args.get("view")
    if view not in ("30day", "since_addition"):
        view = "30day"

    window_days = current_app.config["TREND_WINDOW_DAYS"]
    last_addition = ChemicalAddition.query.order_by(ChemicalAddition.timestamp.desc()).first()

    if view == "since_addition":
        if last_addition is None:
            readings = []
            additions = []
        else:
            readings = (
                Reading.query.filter(Reading.timestamp >= last_addition.timestamp)
                .order_by(Reading.timestamp.asc())
                .all()
            )
            # There's only one marker to show: by definition nothing has been
            # added since the "last" addition itself.
            additions = [last_addition]
    else:
        since = utcnow() - timedelta(days=window_days)
        readings = (
            Reading.query.filter(Reading.timestamp >= since).order_by(Reading.timestamp.asc()).all()
        )
        additions = (
            ChemicalAddition.query.filter(ChemicalAddition.timestamp >= since)
            .order_by(ChemicalAddition.timestamp.asc())
            .all()
        )

    return jsonify(
        {
            "view": view,
            "window_days": window_days,
            "has_last_addition": last_addition is not None,
            "fields": [{"attr": a, "label": l, "unit": u} for a, l, u in READING_FIELDS],
            "readings": [r.to_dict() for r in readings],
            "additions": [a.to_dict() for a in additions],
            "last_addition_at": last_addition.timestamp.isoformat() if last_addition else None,
        }
    )


@main_bp.route("/readings/new", methods=["GET", "POST"])
@login_required
def new_reading():
    form = ReadingForm()
    if form.validate_on_submit():
        reading = Reading(user_id=current_user.id, timestamp=timestamp_for_date(form.date_added.data))
        for attr, _, _ in READING_FIELDS:
            setattr(reading, attr, getattr(form, attr).data)
        db.session.add(reading)
        db.session.commit()
        return _redirect_with_flash("Reading saved.")

    return render_template("main/add_reading.html", form=form, reading_fields=READING_FIELDS)


@main_bp.route("/chemicals/new", methods=["GET", "POST"])
@login_required
def new_chemical_addition():
    form = ChemicalAdditionForm()
    if form.validate_on_submit():
        addition = ChemicalAddition(
            user_id=current_user.id,
            timestamp=timestamp_for_date(form.date_added.data),
            other_name=form.other_name.data.strip() if form.other_name.data else None,
            other_amount=form.other_amount.data,
            notes=form.notes.data.strip() if form.notes.data else None,
        )
        for attr, _, _ in ADDITION_FIELDS:
            setattr(addition, attr, getattr(form, attr).data)
        db.session.add(addition)
        db.session.commit()
        return _redirect_with_flash("Chemical addition logged.")

    return render_template(
        "main/add_chemical.html", form=form, addition_fields=ADDITION_FIELDS
    )


def _redirect_with_flash(message):
    flash(message, "success")
    return redirect(url_for("main.dashboard"))
