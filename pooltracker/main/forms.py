from flask_wtf import FlaskForm
from wtforms import FloatField, StringField, SubmitField, TextAreaField
from wtforms.validators import Length, NumberRange, Optional

from pooltracker.models import ADDITION_FIELDS, READING_FIELDS


class ReadingForm(FlaskForm):
    submit = SubmitField("Save Reading")


class ChemicalAdditionForm(FlaskForm):
    other_name = StringField("Other (name)", validators=[Optional(), Length(max=120)])
    other_amount = FloatField("Other (amount, oz)", validators=[Optional(), NumberRange(min=0)])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Log Chemicals Added")


# Attach one optional, non-negative FloatField per tracked reading/addition value.
# Done dynamically so READING_FIELDS / ADDITION_FIELDS stay the single source of truth.
for attr, label, unit in READING_FIELDS:
    field_label = f"{label} ({unit})" if unit else label
    setattr(ReadingForm, attr, FloatField(field_label, validators=[Optional(), NumberRange(min=0)]))

for attr, label, unit in ADDITION_FIELDS:
    setattr(
        ChemicalAdditionForm,
        attr,
        FloatField(f"{label} ({unit})", validators=[Optional(), NumberRange(min=0)]),
    )
