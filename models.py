from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string

def generate_player_id():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=10))

def generate_tournament_id():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=5))

INDIAN_STATES = [
    'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
    'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
    'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
    'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
    'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal'
]

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.String(10), unique=True, default=generate_player_id)
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    id_card_photo = db.Column(db.String(255))  # Path to ID card photo
    player_photo = db.Column(db.String(255))  # Path to player photo
    rating = db.Column(db.Float, default=1500)
    rating_deviation = db.Column(db.Float, default=350)
    volatility = db.Column(db.Float, default=0.06)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    tournaments = db.relationship('TournamentPlayer', backref='player', lazy=True)

    @property
    def name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.String(5), unique=True, default=generate_tournament_id)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    state = db.Column(db.String(50), nullable=False)
    info = db.Column(db.Text)  # Markdown content
    cover_photo = db.Column(db.String(255))  # Path to cover photo
    rounds = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='upcoming')  # upcoming, ongoing, completed
    players = db.relationship('TournamentPlayer', backref='tournament', lazy=True)
    matches = db.relationship('Match', backref='tournament', lazy=True)

class TournamentPlayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    initial_rating = db.Column(db.Float)
    final_rating = db.Column(db.Float)
    current_score = db.Column(db.Float, default=0)  # For tournament standings

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    round_start_time = db.Column(db.DateTime)
    black_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    white_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    result = db.Column(db.String(10))  # B+R, W+1.5, etc.
    date = db.Column(db.DateTime, default=datetime.utcnow)

    black_player = db.relationship('Player', foreign_keys=[black_player_id])
    white_player = db.relationship('Player', foreign_keys=[white_player_id])