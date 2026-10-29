"""
Run once to create the first Admin account (registration page only
allows signing up as Student or Organizer, on purpose).

Usage:
    python seed_admin.py
"""
from app import create_app
from extensions import db
from models import User

app = create_app()

with app.app_context():
    db.create_all()

    email = "admin@college.edu"
    if User.query.filter_by(email=email).first():
        print("Admin already exists.")
    else:
        admin = User(full_name="System Admin", email=email, role="admin")
        admin.set_password("Admin@123")
        db.session.add(admin)
        db.session.commit()
        print("Admin account created:")
        print(f"  email:    {email}")
        print(f"  password: Admin@123")
        print("Change this password after your first login!")
