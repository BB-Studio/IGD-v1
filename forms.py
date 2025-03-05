from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateTimeField
from wtforms import TextAreaField, SelectField, SelectMultipleField, Length
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional
from models import User, INDIAN_STATES

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class PlayerForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    middle_name = StringField('Middle Name', validators=[Optional(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    state = SelectField('State', choices=[(state, state) for state in INDIAN_STATES], validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    player_photo = FileField('Player Photo', validators=[
        Optional(),
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    id_card_photo = FileField('ID Card Photo', validators=[
        Optional(),
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Submit')

class TournamentForm(FlaskForm):
    name = StringField('Tournament Name', validators=[DataRequired(), Length(max=100)])
    start_date = DateTimeField('Start Date', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_date = DateTimeField('End Date', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    state = SelectField('State', choices=[(state, state) for state in INDIAN_STATES], validators=[DataRequired()])
    info = TextAreaField('Tournament Information (Markdown supported)')
    cover_photo = FileField('Tournament Cover Photo', validators=[
        Optional(),
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    pairing_system = SelectField('Pairing System', 
                                choices=[('swiss', 'Swiss System'), ('macmahon', 'MacMahon System')],
                                default='swiss')
    players = SelectMultipleField('Select Players', coerce=int)
    submit = SubmitField('Submit')

    def validate_end_date(self, field):
        if field.data <= self.start_date.data:
            raise ValidationError('End date must be after start date')