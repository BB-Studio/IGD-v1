from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateTimeField
from wtforms import TextAreaField, SelectField, IntegerField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional
from models import User, INDIAN_STATES

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class PlayerForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    middle_name = StringField('Middle Name', validators=[Optional()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    state = SelectField('State', choices=[(state, state) for state in INDIAN_STATES], validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number')
    id_card_photo = FileField('ID Card Photo', validators=[
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    player_photo = FileField('Player Photo', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Submit')

class TournamentForm(FlaskForm):
    name = StringField('Tournament Name', validators=[DataRequired()])
    start_date = DateTimeField('Start Date', validators=[DataRequired()])
    end_date = DateTimeField('End Date', validators=[DataRequired()])
    state = SelectField('State', choices=[(state, state) for state in INDIAN_STATES], validators=[DataRequired()])
    info = TextAreaField('Tournament Information (Markdown supported)')
    cover_photo = FileField('Tournament Cover Photo', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    rounds = IntegerField('Number of Rounds', validators=[DataRequired()])
    players = SelectMultipleField('Select Players', coerce=int)
    submit = SubmitField('Submit')

class MatchForm(FlaskForm):
    black_player = SelectField('Black Player', coerce=int, validators=[DataRequired()])
    white_player = SelectField('White Player', coerce=int, validators=[DataRequired()])
    round_number = IntegerField('Round Number', validators=[DataRequired()])
    round_start_time = DateTimeField('Round Start Time', validators=[DataRequired()])
    result = StringField('Result', validators=[DataRequired()])
    submit = SubmitField('Submit')