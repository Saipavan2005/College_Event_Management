from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, SelectField, TextAreaField,
    IntegerField, DateField, TimeField, SubmitField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional


class RegisterForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=150)])
    role = SelectField(
        "I am a", choices=[("student", "Student"), ("organizer", "Organizer")],
        validators=[DataRequired()]
    )
    department = StringField("Department", validators=[Optional(), Length(max=100)])
    roll_number = StringField("Roll Number", validators=[Optional(), Length(max=50)])
    club_name = StringField("Club / Society Name", validators=[Optional(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")]
    )
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class EventForm(FlaskForm):
    title = StringField("Event Title", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Description", validators=[DataRequired()])
    category = SelectField(
        "Category",
        choices=[("Technical", "Technical"), ("Cultural", "Cultural"),
                 ("Sports", "Sports"), ("Workshop", "Workshop"), ("General", "General")]
    )
    venue = StringField("Venue", validators=[DataRequired(), Length(max=150)])
    event_date = DateField("Event Date", validators=[DataRequired()])
    event_time = TimeField("Event Time", validators=[DataRequired()])
    max_participants = IntegerField(
        "Max Participants (0 = unlimited)",
        validators=[Optional(), NumberRange(min=0)], default=0
    )
    poster = FileField(
        "Event Poster",
        validators=[Optional(), FileAllowed(["png", "jpg", "jpeg", "gif", "webp"], "Images only!")]
    )
    submit = SubmitField("Save Event")


class ProfileForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    department = StringField("Department", validators=[Optional(), Length(max=100)])
    roll_number = StringField("Roll Number", validators=[Optional(), Length(max=50)])
    club_name = StringField("Club / Society Name", validators=[Optional(), Length(max=120)])
    submit = SubmitField("Update Profile")


class FeedbackForm(FlaskForm):
    rating = SelectField(
        "Rating", choices=[(str(i), f"{i} Star{'s' if i > 1 else ''}") for i in range(5, 0, -1)],
        validators=[DataRequired()]
    )
    comments = TextAreaField("Comments", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Submit Feedback")
