from datetime import datetime
from extensions import db


class Registration(db.Model):
    __tablename__ = "registrations"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)

    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    attended = db.Column(db.Boolean, default=False)

    certificate = db.relationship(
        "Certificate", backref="registration", uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        # A student can only register once per event (no duplicate registrations)
        db.UniqueConstraint("student_id", "event_id", name="uq_student_event"),
    )

    def __repr__(self):
        return f"<Registration student={self.student_id} event={self.event_id}>"


class Certificate(db.Model):
    __tablename__ = "certificates"

    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(
        db.Integer, db.ForeignKey("registrations.id"), nullable=False, unique=True
    )
    filename = db.Column(db.String(255), nullable=False)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Certificate {self.filename}>"
