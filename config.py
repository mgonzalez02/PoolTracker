import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Copy .env.example to .env and set a random secret key."
        )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "pooltracker.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set to True when serving over HTTPS in production.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

    # Rolling window (in days) used for the trend charts on the dashboard.
    TREND_WINDOW_DAYS = 7

    # Public hostname used to build links in emails (e.g. password resets),
    # e.g. "https://pool.example.com" or "http://192.168.1.50:8080". Without
    # this, links are built from the request's Host header, which is wrong
    # behind a proxy or when the app is reached at a different address than
    # the one the request came in on (e.g. 127.0.0.1 during local testing).
    # No trailing slash.
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "").rstrip("/") or None

    # SMTP settings used to send "forgot password" emails. Leave MAIL_SERVER
    # unset to disable emailing (the "Forgot password?" link will tell users
    # to contact an admin instead).
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
