from datetime import datetime
from extensions import db


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default="General")
    venue = db.Column(db.String(150), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    event_time = db.Column(db.Time, nullable=False)
    poster_filename = db.Column(db.String(255))  # stored in /uploads/posters
    max_participants = db.Column(db.Integer, default=0)  # 0 = unlimited

    # Workflow: an organizer creates an event -> status "pending"
    # -> admin approves -> "approved"  (or "rejected")
    status = db.Column(db.String(20), default="pending", nullable=False)

    organizer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    registrations = db.relationship(
        "Registration", backref="event", lazy=True, cascade="all, delete-orphan"
    )
    feedbacks = db.relationship(
        "Feedback", backref="event", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def seats_taken(self):
        return len(self.registrations)

    @property
    def seats_left(self):
        if self.max_participants == 0:
            return None  # unlimited
        return max(self.max_participants - self.seats_taken, 0)

    @property
    def is_full(self):
        return self.max_participants > 0 and self.seats_taken >= self.max_participants

    @property
    def is_past(self):
        return self.event_date < datetime.utcnow().date()

    def __repr__(self):
        return f"<Event {self.title} ({self.status})>"
