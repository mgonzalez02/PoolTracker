import getpass
import os

import click
from email_validator import EmailNotValidError, validate_email
from flask import Flask
from sqlalchemy import inspect, text

from pooltracker.extensions import csrf, db, login_manager


def create_app(config_object="config.Config"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from pooltracker.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from pooltracker.auth import auth_bp
    from pooltracker.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        _ensure_user_email_column()

    register_cli(app)

    return app


def _ensure_user_email_column():
    """Add the `email` column to an existing `user` table created before it existed.

    db.create_all() only creates missing tables, so upgrading in place needs a
    one-off ALTER TABLE rather than a full migration framework.
    """
    inspector = inspect(db.engine)
    if "user" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("user")}
    if "email" in columns:
        return
    with db.engine.begin() as conn:
        conn.execute(text("ALTER TABLE user ADD COLUMN email VARCHAR(255)"))


def _read_new_password():
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        click.echo("Passwords did not match.")
        return None
    if len(password) < 8:
        click.echo("Password must be at least 8 characters.")
        return None
    return password


def _prompt_for_email(User):
    """Ask for an optional email, so 'Forgot password?' knows where to send the reset link.

    Returns (email_or_None, ok). ok is False if the entered email is invalid
    or already taken, in which case the caller should abort.
    """
    raw = click.prompt(
        "Email (used for 'Forgot password?' resets; press Enter to skip)",
        default="",
        show_default=False,
    ).strip()
    if not raw:
        return None, True

    try:
        email = validate_email(raw, check_deliverability=False).normalized
    except EmailNotValidError as exc:
        click.echo(f"Invalid email: {exc}")
        return None, False

    if User.query.filter_by(email=email).first():
        click.echo(f"Email '{email}' is already in use by another account.")
        return None, False

    return email, True


def register_cli(app):
    @app.cli.command("create-user")
    @click.argument("username")
    def create_user(username):
        """Create a new PoolTracker login (you'll be prompted for an email and password)."""
        from pooltracker.models import User

        username = username.strip()
        if User.query.filter_by(username=username).first():
            click.echo(f"User '{username}' already exists.")
            return

        email, ok = _prompt_for_email(User)
        if not ok:
            return

        password = _read_new_password()
        if password is None:
            return

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"User '{username}' created.")

    @app.cli.command("set-email")
    @click.argument("username")
    @click.argument("email")
    def set_email(username, email):
        """Attach or update the email address on an existing login."""
        from pooltracker.models import User

        username = username.strip()
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"User '{username}' not found.")
            return

        try:
            email = validate_email(email.strip(), check_deliverability=False).normalized
        except EmailNotValidError as exc:
            click.echo(f"Invalid email: {exc}")
            return

        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != user.id:
            click.echo(f"Email '{email}' is already in use by another account.")
            return

        user.email = email
        db.session.commit()
        click.echo(f"Email for '{username}' set to '{email}'.")

    @app.cli.command("reset-password")
    @click.argument("username")
    def reset_password(username):
        """Reset an existing user's password (you'll be prompted for a new one)."""
        from pooltracker.models import User

        username = username.strip()
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"User '{username}' not found.")
            return

        password = _read_new_password()
        if password is None:
            return

        user.set_password(password)
        db.session.commit()
        click.echo(f"Password for '{username}' updated.")
