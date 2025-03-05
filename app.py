import os
import logging
from datetime import timedelta
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
csrf = CSRFProtect()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Essential Configuration
    app.secret_key = os.environ.get("SESSION_SECRET")
    if not app.secret_key:
        logger.warning("No SESSION_SECRET set! Using development key - NOT SECURE!")
        app.secret_key = "dev-key-not-secure"

    # Database Configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///go_stats.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # Security Configuration
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour CSRF token validity
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

    # Initialize extensions with app
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    # Login configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.session_protection = "strong"

    # Register blueprints
    with app.app_context():
        from auth import auth_bp
        from routes import main_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)

        # Create database tables
        db.create_all()

        @app.errorhandler(CSRFError)
        def handle_csrf_error(e):
            logger.error(f"CSRF Error: {e.description}")
            return render_template('error.html', 
                                error="CSRF token validation failed. Please try again."), 400

    return app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)