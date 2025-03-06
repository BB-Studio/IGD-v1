from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateTimeField
from wtforms import TextAreaField, SelectField, SelectMultipleField
from wtforms.validators import Length
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional
from models import User, INDIAN_STATES

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[Optional()])
    password = PasswordField('Password', validators=[Optional()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class PlayerForm(FlaskForm):
    first_name = StringField('First Name', validators=[Optional(), Length(max=50)])
    middle_name = StringField('Middle Name', validators=[Optional(), Length(max=50)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=50)])
    state = SelectField('State', choices=[(state, state) for state in INDIAN_STATES], validators=[Optional()])
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

    def __init__(self, *args, **kwargs):
        super(PlayerForm, self).__init__(*args, **kwargs)
        if self.player_photo.data == '':
            self.player_photo.data = None
        if self.id_card_photo.data == '':
            self.id_card_photo.data = None

class TournamentForm(FlaskForm):
    name = StringField('Tournament Name', validators=[Optional(), Length(max=100)])
    start_date = DateTimeField('Start Date', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    end_date = DateTimeField('End Date', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    state = SelectField('State', choices=[(state, state) for state in INDIAN_STATES], validators=[Optional()])
    info = TextAreaField('Tournament Information (Markdown supported)')
    cover_photo = FileField('Tournament Cover Photo', validators=[
        Optional(),
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    pairing_system = SelectField('Pairing System', 
                                choices=[
                                    ('swiss', 'Swiss System'), 
                                    ('macmahon', 'MacMahon System'),
                                    ('round_robin', 'Round Robin')
                                ],
                                default='swiss',
                                validators=[Optional()])
    players = SelectMultipleField('Select Players', coerce=int, validators=[Optional()])
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(TournamentForm, self).__init__(*args, **kwargs)
        if self.cover_photo.data == '':
            self.cover_photo.data = None

    def validate_end_date(self, field):
        if field.data and self.start_date.data and field.data <= self.start_date.data:
            raise ValidationError('End date must be after start date')