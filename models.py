from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

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
    name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Float, default=1500)
    rating_deviation = db.Column(db.Float, default=350)
    volatility = db.Column(db.Float, default=0.06)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    tournaments = db.relationship('TournamentPlayer', backref='player', lazy=True)

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='upcoming')  # upcoming, ongoing, completed
    location = db.Column(db.String(200))
    description = db.Column(db.Text)
    players = db.relationship('TournamentPlayer', backref='tournament', lazy=True)
    matches = db.relationship('Match', backref='tournament', lazy=True)

class TournamentPlayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    initial_rating = db.Column(db.Float)
    final_rating = db.Column(db.Float)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    black_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    white_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    result = db.Column(db.String(10))  # B+R, W+1.5, etc.
    date = db.Column(db.DateTime, default=datetime.utcnow)

    black_player = db.relationship('Player', foreign_keys=[black_player_id])
    white_player = db.relationship('Player', foreign_keys=[white_player_id])
