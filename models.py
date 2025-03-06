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
    first_name = db.Column(db.String(50))  # Made nullable
    middle_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))  # Made nullable
    state = db.Column(db.String(50))  # Made nullable
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    id_card_photo = db.Column(db.String(255))
    player_photo = db.Column(db.String(255))
    rating = db.Column(db.Float, default=1500)
    rating_deviation = db.Column(db.Float, default=350)
    volatility = db.Column(db.Float, default=0.06)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    tournaments = db.relationship('TournamentPlayer', backref='player', lazy=True)

    @property
    def name(self):
        if self.middle_name:
            return f"{self.first_name or ''} {self.middle_name} {self.last_name or ''}"
        return f"{self.first_name or ''} {self.last_name or ''}"

    @property
    def current_score(self):
        return 0  # Default score for new players

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.String(5), unique=True, default=generate_tournament_id)
    name = db.Column(db.String(100))  # Made nullable
    start_date = db.Column(db.DateTime)  # Made nullable
    end_date = db.Column(db.DateTime)  # Made nullable
    state = db.Column(db.String(50))  # Made nullable
    info = db.Column(db.Text)
    cover_photo = db.Column(db.String(255))
    status = db.Column(db.String(20), default='upcoming')
    pairing_system = db.Column(db.String(20), default='swiss')
    players = db.relationship('TournamentPlayer', backref='tournament', lazy=True, cascade='all, delete-orphan')
    rounds = db.relationship('Round', backref='tournament', lazy=True, cascade='all, delete-orphan')

class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id', ondelete='CASCADE'), nullable=False)
    number = db.Column(db.Integer)  # Made nullable
    datetime = db.Column(db.DateTime)  # Made nullable
    status = db.Column(db.String(20), default='pending')
    pairings = db.relationship('RoundPairing', backref='round', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('tournament_id', 'number', name='unique_round_number'),
    )

class RoundPairing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('round.id', ondelete='CASCADE'), nullable=False)
    white_player_id = db.Column(db.Integer, db.ForeignKey('player.id', ondelete='CASCADE'), nullable=False)
    black_player_id = db.Column(db.Integer, db.ForeignKey('player.id', ondelete='CASCADE'), nullable=False)
    result = db.Column(db.String(10))
    white_player = db.relationship('Player', foreign_keys=[white_player_id])
    black_player = db.relationship('Player', foreign_keys=[black_player_id])

class TournamentPlayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id', ondelete='CASCADE'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id', ondelete='CASCADE'), nullable=False)
    initial_rating = db.Column(db.Float)
    final_rating = db.Column(db.Float)
    current_score = db.Column(db.Float, default=0)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id', ondelete='CASCADE'), nullable=False)
    round_number = db.Column(db.Integer)  # Made nullable
    round_start_time = db.Column(db.DateTime)
    black_player_id = db.Column(db.Integer, db.ForeignKey('player.id', ondelete='CASCADE'), nullable=False)
    white_player_id = db.Column(db.Integer, db.ForeignKey('player.id', ondelete='CASCADE'), nullable=False)
    result = db.Column(db.String(10))
    date = db.Column(db.DateTime, default=datetime.utcnow)

    black_player = db.relationship('Player', foreign_keys=[black_player_id])
    white_player = db.relationship('Player', foreign_keys=[white_player_id])
    tournament = db.relationship('Tournament', backref='matches')