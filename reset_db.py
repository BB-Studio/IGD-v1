
from app import db, app
from models import *

def reset_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create all tables based on updated models
        db.create_all()
        
        print("Database schema has been reset.")

if __name__ == "__main__":
    reset_db()
