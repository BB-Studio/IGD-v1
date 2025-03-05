from werkzeug.security import generate_password_hash
from app import db, app
from models import User

def create_admin_user(username='admin', password='666666'):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(
                username=username,
                email='admin@example.com',
                is_admin=True
            )
            user.set_password(password)  # Use set_password instead of directly setting password_hash
            db.session.add(user)
        else:
            user.set_password(password)  # Update password if user exists
            user.is_admin = True  # Ensure admin status

        db.session.commit()
        print(f"Admin user '{username}' created/updated successfully!")

if __name__ == '__main__':
    create_admin_user()