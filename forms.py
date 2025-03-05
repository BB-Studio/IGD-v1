from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateTimeField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class PlayerForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    submit = SubmitField('Submit')

class TournamentForm(FlaskForm):
    name = StringField('Tournament Name', validators=[DataRequired()])
    start_date = DateTimeField('Start Date', validators=[DataRequired()])
    end_date = DateTimeField('End Date', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Submit')

class MatchForm(FlaskForm):
    black_player = StringField('Black Player', validators=[DataRequired()])
    white_player = StringField('White Player', validators=[DataRequired()])
    result = StringField('Result', validators=[DataRequired()])
    submit = SubmitField('Submit')
