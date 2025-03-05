from werkzeug.security import generate_password_hash
from app import db, app
from models import User

def create_admin_user(username='admin', password='qwerty'):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(
                username=username,
                email='admin@example.com',
                is_admin=True
            )
        user.password_hash = generate_password_hash(password)
        db.session.add(user)
        db.session.commit()
        print(f"Admin user '{username}' created/updated successfully!")

if __name__ == '__main__':
    create_admin_user()