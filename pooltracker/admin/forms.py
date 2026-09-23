from wtforms import BooleanField, SubmitField

from pooltracker.auth.forms import AccountForm


class AdminCreateUserForm(AccountForm):
    is_admin = BooleanField("Make this user an admin")
    submit = SubmitField("Create User")
