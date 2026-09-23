from datetime import datetime, timezone

from flask import current_app
from flask_login import UserMixin
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from pooltracker.extensions import db

PASSWORD_RESET_SALT = "password-reset"
PASSWORD_RESET_MAX_AGE = 3600  # 1 hour


def utcnow():
    return datetime.now(timezone.utc)


# Chemical readings tracked on the dashboard: (model attribute, display label, unit).
READING_FIELDS = [
    ("free_chlorine", "Free Chlorine", "ppm"),
    ("total_chlorine", "Total Chlorine", "ppm"),
    ("ph", "pH", ""),
    ("total_alkalinity", "Total Alkalinity", "ppm"),
    ("cya", "CYA", "ppm"),
    ("tds", "TDS", "ppm"),
    ("calcium_hardness", "Calcium Hardness", "ppm"),
    ("nacl", "NaCl (Salt)", "ppm"),
]

# Chemicals that can be logged as "added to the pool": (model attribute, display label, unit).
ADDITION_FIELDS = [
    ("chlorine_oz", "Chlorine", "oz"),
    ("muriatic_acid_oz", "Muriatic Acid", "oz"),
    ("cya_oz", "CYA", "oz"),
    ("bromine_oz", "Bromine", "oz"),
    ("soda_ash_oz", "Soda Ash", "oz"),
]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_token(self):
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        # Binding the token to a fragment of the current password hash makes
        # it single-use: once the password is changed, old tokens naturally
        # stop matching, with no extra "used" state to store or clean up.
        return serializer.dumps([self.id, self.password_hash[-12:]], salt=PASSWORD_RESET_SALT)

    @staticmethod
    def verify_reset_token(token):
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            user_id, hash_fragment = serializer.loads(
                token, salt=PASSWORD_RESET_SALT, max_age=PASSWORD_RESET_MAX_AGE
            )
        except (BadSignature, SignatureExpired, ValueError):
            return None
        user = db.session.get(User, user_id)
        if user is None or user.password_hash[-12:] != hash_fragment:
            return None
        return user

    def __repr__(self):
        return f"<User {self.username}>"


class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    free_chlorine = db.Column(db.Float, nullable=True)
    total_chlorine = db.Column(db.Float, nullable=True)
    ph = db.Column(db.Float, nullable=True)
    total_alkalinity = db.Column(db.Float, nullable=True)
    cya = db.Column(db.Float, nullable=True)
    tds = db.Column(db.Float, nullable=True)
    calcium_hardness = db.Column(db.Float, nullable=True)
    nacl = db.Column(db.Float, nullable=True)

    user = db.relationship("User", backref=db.backref("readings", lazy="dynamic"))

    def to_dict(self):
        data = {"id": self.id, "timestamp": self.timestamp.isoformat()}
        for attr, _, _ in READING_FIELDS:
            data[attr] = getattr(self, attr)
        return data


class ChemicalAddition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    chlorine_oz = db.Column(db.Float, nullable=True)
    muriatic_acid_oz = db.Column(db.Float, nullable=True)
    cya_oz = db.Column(db.Float, nullable=True)
    bromine_oz = db.Column(db.Float, nullable=True)
    soda_ash_oz = db.Column(db.Float, nullable=True)
    other_name = db.Column(db.String(120), nullable=True)
    other_amount = db.Column(db.Float, nullable=True)
    notes = db.Column(db.String(500), nullable=True)

    user = db.relationship("User", backref=db.backref("chemical_additions", lazy="dynamic"))

    def items_added(self):
        """List of (label, amount, unit) for every field that was actually filled in."""
        items = []
        for attr, label, unit in ADDITION_FIELDS:
            value = getattr(self, attr)
            if value:
                items.append((label, value, unit))
        if self.other_name and self.other_amount:
            items.append((self.other_name, self.other_amount, "oz"))
        return items

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "items": [{"label": label, "amount": amount, "unit": unit} for label, amount, unit in self.items_added()],
            "notes": self.notes,
        }
