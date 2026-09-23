from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from pooltracker.admin import admin_bp
from pooltracker.admin.forms import AdminCreateUserForm
from pooltracker.auth.decorators import admin_required
from pooltracker.extensions import db
from pooltracker.main.forms import ChemicalAdditionForm, ReadingForm
from pooltracker.models import (
    ADDITION_FIELDS,
    READING_FIELDS,
    ChemicalAddition,
    Reading,
    User,
    timestamp_for_date,
)


@admin_bp.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.username.asc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    form = AdminCreateUserForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip() if form.email.data else None

        if User.query.filter_by(username=username).first():
            flash("That username is already taken.", "error")
            return render_template("admin/new_user.html", form=form)
        if email and User.query.filter_by(email=email).first():
            flash("That email is already in use by another account.", "error")
            return render_template("admin/new_user.html", form=form)

        user = User(username=username, email=email, is_admin=form.is_admin.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f"User '{username}' created.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/new_user.html", form=form)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    entry_count = Reading.query.filter_by(user_id=user.id).count() + ChemicalAddition.query.filter_by(
        user_id=user.id
    ).count()

    if user.id == current_user.id:
        flash("You can't delete your own account.", "error")
    elif user.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
        flash("Can't delete the last remaining admin.", "error")
    elif entry_count:
        noun = "entry" if entry_count == 1 else "entries"
        flash(
            f"Can't delete '{user.username}': they have {entry_count} logged "
            f"{noun} attached to their account.",
            "error",
        )
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f"User '{user.username}' deleted.", "success")

    return redirect(url_for("admin.users"))


@admin_bp.route("/entries")
@admin_required
def entries():
    readings = Reading.query.order_by(Reading.timestamp.desc()).limit(50).all()
    additions = ChemicalAddition.query.order_by(ChemicalAddition.timestamp.desc()).limit(50).all()
    return render_template(
        "admin/entries.html", readings=readings, additions=additions, reading_fields=READING_FIELDS
    )


@admin_bp.route("/readings/<int:reading_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_reading(reading_id):
    reading = db.session.get(Reading, reading_id)
    if reading is None:
        abort(404)

    form = ReadingForm(obj=reading)
    if request.method == "GET":
        form.date_added.data = reading.timestamp.date()

    if form.validate_on_submit():
        reading.timestamp = timestamp_for_date(form.date_added.data)
        for attr, _, _ in READING_FIELDS:
            setattr(reading, attr, getattr(form, attr).data)
        db.session.commit()
        flash("Reading updated.", "success")
        return redirect(url_for("admin.entries"))

    return render_template("admin/edit_reading.html", form=form, reading_fields=READING_FIELDS)


@admin_bp.route("/readings/<int:reading_id>/delete", methods=["POST"])
@admin_required
def delete_reading(reading_id):
    reading = db.session.get(Reading, reading_id)
    if reading is None:
        abort(404)
    db.session.delete(reading)
    db.session.commit()
    flash("Reading deleted.", "success")
    return redirect(url_for("admin.entries"))


@admin_bp.route("/chemicals/<int:addition_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_chemical_addition(addition_id):
    addition = db.session.get(ChemicalAddition, addition_id)
    if addition is None:
        abort(404)

    form = ChemicalAdditionForm(obj=addition)
    if request.method == "GET":
        form.date_added.data = addition.timestamp.date()

    if form.validate_on_submit():
        addition.timestamp = timestamp_for_date(form.date_added.data)
        addition.other_name = form.other_name.data.strip() if form.other_name.data else None
        addition.other_amount = form.other_amount.data
        addition.notes = form.notes.data.strip() if form.notes.data else None
        for attr, _, _ in ADDITION_FIELDS:
            setattr(addition, attr, getattr(form, attr).data)
        db.session.commit()
        flash("Chemical addition updated.", "success")
        return redirect(url_for("admin.entries"))

    return render_template("admin/edit_chemical.html", form=form, addition_fields=ADDITION_FIELDS)


@admin_bp.route("/chemicals/<int:addition_id>/delete", methods=["POST"])
@admin_required
def delete_chemical_addition(addition_id):
    addition = db.session.get(ChemicalAddition, addition_id)
    if addition is None:
        abort(404)
    db.session.delete(addition)
    db.session.commit()
    flash("Chemical addition deleted.", "success")
    return redirect(url_for("admin.entries"))
