from urllib.parse import urlparse

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from pooltracker.auth import auth_bp
from pooltracker.auth.forms import LoginForm, RequestResetForm, ResetPasswordForm, SetupForm
from pooltracker.email_utils import mail_is_configured, send_password_reset_email
from pooltracker.extensions import db
from pooltracker.models import User


def _is_safe_next_url(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return test_url.scheme in ("", "http", "https") and ref_url.netloc == test_url.netloc


def _build_reset_url(token):
    base_url = current_app.config.get("APP_BASE_URL")
    if base_url:
        return base_url + url_for("auth.reset_password", token=token)
    return url_for("auth.reset_password", token=token, _external=True)


@auth_bp.route("/setup", methods=["GET", "POST"])
def setup():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    # Only usable to create the very first account. Once any user exists,
    # further accounts go through admin-managed creation instead.
    if User.query.count() > 0:
        return redirect(url_for("auth.login"))

    form = SetupForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip() if form.email.data else None
        if User.query.filter_by(username=username).first():
            flash("That username is already taken.", "error")
            return render_template("auth/setup.html", form=form)

        user = User(username=username, email=email, is_admin=True)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Admin account created. Welcome to PoolTracker!", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/setup.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if User.query.count() == 0:
        return redirect(url_for("auth.setup"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        next_url = request.args.get("next")
        if _is_safe_next_url(next_url):
            return redirect(next_url)
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if not mail_is_configured():
        flash(
            "Password reset emails aren't set up for this site. Ask an admin to reset your password.",
            "info",
        )
        return redirect(url_for("auth.login"))

    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip()).first()
        if user:
            reset_url = _build_reset_url(user.get_reset_token())
            try:
                send_password_reset_email(user, reset_url)
            except OSError:
                current_app.logger.exception("Failed to send password reset email")

        # Always show the same message, whether or not that email is on file,
        # so this form can't be used to discover which emails have accounts.
        flash("If that email is on file, a password reset link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    user = User.verify_reset_token(token)
    if not user:
        flash("That password reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been reset. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)
