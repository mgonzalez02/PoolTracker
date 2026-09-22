import getpass
import os

import click
from flask import Flask

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

    register_cli(app)

    return app


def register_cli(app):
    @app.cli.command("create-user")
    @click.argument("username")
    def create_user(username):
        """Create a new PoolTracker login (you'll be prompted for a password)."""
        from pooltracker.models import User

        username = username.strip()
        if User.query.filter_by(username=username).first():
            click.echo(f"User '{username}' already exists.")
            return

        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            click.echo("Passwords did not match.")
            return
        if len(password) < 8:
            click.echo("Password must be at least 8 characters.")
            return

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"User '{username}' created.")
