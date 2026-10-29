from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


class User(UserMixin, db.Model):
    """
    A single users table with a 'role' column instead of three separate
    Student / Organizer / Admin tables.

    WHY one table instead of three?
    - Login, logout, and password handling are identical for all roles,
      so Flask-Login only has to know about ONE model.
    - We still get the same real-world behaviour: a student can never do
      organizer/admin things, because every route checks `current_user.role`.
    - Adding a new role later (e.g. "faculty") means adding a value, not a
      whole new table + login system.

    role is one of: "student", "organizer", "admin"
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")

    # Student-specific (optional / blank for other roles)
    department = db.Column(db.String(100))
    roll_number = db.Column(db.String(50))

    # Organizer-specific
    club_name = db.Column(db.String(120))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    events_created = db.relationship(
        "Event", backref="organizer", lazy=True, foreign_keys="Event.organizer_id"
    )
    registrations = db.relationship(
        "Registration", backref="student", lazy=True, cascade="all, delete-orphan"
    )
    feedback_given = db.relationship(
        "Feedback", backref="student", lazy=True, cascade="all, delete-orphan"
    )

    # --- Password helpers ---
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # --- Role helpers ---
    @property
    def is_student(self):
        return self.role == "student"

    @property
    def is_organizer(self):
        return self.role == "organizer"

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
