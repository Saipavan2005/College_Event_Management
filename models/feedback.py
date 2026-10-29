from datetime import datetime
from extensions import db


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)

    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("student_id", "event_id", name="uq_feedback_student_event"),
    )

    def __repr__(self):
        return f"<Feedback event={self.event_id} rating={self.rating}>"
