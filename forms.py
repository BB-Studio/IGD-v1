from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateTimeField
from wtforms import TextAreaField, SelectField, SelectMultipleField
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
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone Number', validators=[Optional()])
    player_photo = FileField('Player Photo', validators=[
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    id_card_photo = FileField('ID Card Photo', validators=[
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Submit')

class TournamentForm(FlaskForm):
    name = StringField('Tournament Name', validators=[DataRequired()])
    start_date = DateTimeField('Start Date', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_date = DateTimeField('End Date', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    state = SelectField('State', choices=[(state, state) for state in INDIAN_STATES], validators=[DataRequired()])
    info = TextAreaField('Tournament Information (Markdown supported)')
    cover_photo = FileField('Tournament Cover Photo', validators=[
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