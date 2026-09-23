import smtplib
from email.message import EmailMessage

from flask import current_app


def mail_is_configured():
    return bool(current_app.config.get("MAIL_SERVER"))


def send_password_reset_email(user, reset_url):
    """Send a password reset link to the user. Raises on SMTP failure."""
    config = current_app.config

    message = EmailMessage()
    message["Subject"] = "Reset your PoolTracker password"
    message["From"] = config["MAIL_DEFAULT_SENDER"]
    message["To"] = user.email
    message.set_content(
        "Someone (hopefully you) requested a password reset for your "
        f"PoolTracker account '{user.username}'.\n\n"
        f"Reset your password here: {reset_url}\n\n"
        "This link expires in 1 hour. If you didn't request this, you can "
        "safely ignore this email."
    )

    with smtplib.SMTP(config["MAIL_SERVER"], config["MAIL_PORT"]) as smtp:
        if config["MAIL_USE_TLS"]:
            smtp.starttls()
        if config["MAIL_USERNAME"]:
            smtp.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
        smtp.send_message(message)
