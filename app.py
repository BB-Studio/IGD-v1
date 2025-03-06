import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-here")  # Updated secret key handling
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///go_stats.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
}
app.config['WTF_CSRF_ENABLED'] = True  # Enable CSRF protection

# Initialize extensions
csrf = CSRFProtect(app)  # Initialize CSRF protection
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Import routes after app initialization
from auth import auth_bp
from routes import main_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)

with app.app_context():
    # Import all models to ensure they're registered with SQLAlchemy
    from models import User, Player, Tournament, Round, RoundPairing, TournamentPlayer, Match
    # Create all tables
    db.create_all()