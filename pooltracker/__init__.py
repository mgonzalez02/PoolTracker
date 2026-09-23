import getpass
import os

import click
from email_validator import EmailNotValidError, validate_email
from flask import Flask, render_template
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

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

    from pooltracker.admin import admin_bp
    from pooltracker.auth import auth_bp
    from pooltracker.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    with app.app_context():
        db.create_all()
        _ensure_user_columns()
        _ensure_chemical_addition_columns()
        _ensure_reading_columns()

    register_cli(app)

    return app


def _add_column_if_missing(existing_columns, column_name, alter_sql):
    """Add a column via ALTER TABLE, tolerating a concurrent gunicorn worker
    doing the exact same thing (each worker calls create_app() independently
    at boot, so two workers can both see the column missing and race to add it)."""
    if column_name in existing_columns:
        return
    try:
        with db.engine.begin() as conn:
            conn.execute(text(alter_sql))
    except OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


def _rename_column_if_needed(existing_columns, old_name, new_name, table):
    """Rename a column, tolerating a concurrent gunicorn worker doing the same
    rename (see _add_column_if_missing for why workers can race at boot)."""
    if old_name not in existing_columns or new_name in existing_columns:
        return
    try:
        with db.engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} RENAME COLUMN {old_name} TO {new_name}"))
    except OperationalError:
        # A sibling worker may have already renamed it; only re-raise if it didn't.
        current_columns = {col["name"] for col in inspect(db.engine).get_columns(table)}
        if new_name not in current_columns:
            raise


def _ensure_chemical_addition_columns():
    """Upgrade an existing `chemical_addition` table created before Sodium
    Bicarbonate replaced Soda Ash and Calcium Chloride was added.
    """
    inspector = inspect(db.engine)
    if "chemical_addition" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("chemical_addition")}

    _rename_column_if_needed(columns, "soda_ash_oz", "sodium_bicarbonate_oz", "chemical_addition")

    columns = {col["name"] for col in inspect(db.engine).get_columns("chemical_addition")}
    _add_column_if_missing(
        columns,
        "calcium_chloride_oz",
        "ALTER TABLE chemical_addition ADD COLUMN calcium_chloride_oz FLOAT",
    )


def _ensure_reading_columns():
    """Add the `temperature` column to an existing `reading` table created
    before it existed."""
    inspector = inspect(db.engine)
    if "reading" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("reading")}
    _add_column_if_missing(columns, "temperature", "ALTER TABLE reading ADD COLUMN temperature FLOAT")


def _ensure_user_columns():
    """Add columns to an existing `user` table created before they existed.

    db.create_all() only creates missing tables, so upgrading in place needs
    one-off ALTER TABLEs rather than a full migration framework.
    """
    inspector = inspect(db.engine)
    if "user" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("user")}

    _add_column_if_missing(columns, "email", "ALTER TABLE user ADD COLUMN email VARCHAR(255)")
    _add_column_if_missing(
        columns, "is_admin", "ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"
    )

    # If nobody is an admin yet but there's exactly one account, it's clearly
    # the site's owner, so grandfather it in rather than silently locking
    # them out of admin features (the /setup page only helps when zero users
    # exist). Safe to run on every boot: it's a no-op once any admin exists,
    # and from multiple concurrent workers it just performs the same
    # harmless write twice.
    from pooltracker.models import User

    if User.query.filter_by(is_admin=True).count() == 0:
        users = User.query.all()
        if len(users) == 1:
            users[0].is_admin = True
            db.session.commit()


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

    @app.cli.command("promote-admin")
    @click.argument("username")
    def promote_admin(username):
        """Grant an existing login admin access (user management, editing entries)."""
        from pooltracker.models import User

        username = username.strip()
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"User '{username}' not found.")
            return

        if user.is_admin:
            click.echo(f"'{username}' is already an admin.")
            return

        user.is_admin = True
        db.session.commit()
        click.echo(f"'{username}' is now an admin.")
