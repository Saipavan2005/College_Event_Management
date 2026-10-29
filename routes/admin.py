from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from models import User, Event, Registration, Feedback
from decorators import role_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    stats = {
        "total_students": User.query.filter_by(role="student").count(),
        "total_organizers": User.query.filter_by(role="organizer").count(),
        "total_events": Event.query.count(),
        "pending_events": Event.query.filter_by(status="pending").count(),
        "total_registrations": Registration.query.count(),
    }
    pending_events = Event.query.filter_by(status="pending").order_by(Event.created_at.desc()).all()
    return render_template("admin/dashboard.html", stats=stats, pending_events=pending_events)


@admin_bp.route("/events")
@login_required
@role_required("admin")
def manage_events():
    events = Event.query.order_by(Event.created_at.desc()).all()
    return render_template("admin/manage_events.html", events=events)


@admin_bp.route("/events/<int:event_id>/approve", methods=["POST"])
@login_required
@role_required("admin")
def approve_event(event_id):
    event = Event.query.get_or_404(event_id)
    event.status = "approved"
    db.session.commit()
    flash(f'"{event.title}" approved.', "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/events/<int:event_id>/reject", methods=["POST"])
@login_required
@role_required("admin")
def reject_event(event_id):
    event = Event.query.get_or_404(event_id)
    event.status = "rejected"
    db.session.commit()
    flash(f'"{event.title}" rejected.', "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users")
@login_required
@role_required("admin")
def manage_users():
    students = User.query.filter_by(role="student").order_by(User.full_name).all()
    organizers = User.query.filter_by(role="organizer").order_by(User.full_name).all()
    return render_template("admin/manage_users.html", students=students, organizers=organizers)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        abort(403)  # can't delete other admins from this view
    db.session.delete(user)
    db.session.commit()
    flash(f"{user.full_name}'s account was removed.", "info")
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/reports")
@login_required
@role_required("admin")
def reports():
    # Total events per category
    events_by_category = (
        db.session.query(Event.category, func.count(Event.id))
        .group_by(Event.category)
        .all()
    )

    # Top 5 most popular events (by registration count)
    popular_events = (
        db.session.query(Event.title, func.count(Registration.id).label("count"))
        .join(Registration, Registration.event_id == Event.id)
        .group_by(Event.id)
        .order_by(func.count(Registration.id).desc())
        .limit(5)
        .all()
    )

    # Top organizers (by number of approved events)
    top_organizers = (
        db.session.query(User.full_name, func.count(Event.id).label("count"))
        .join(Event, Event.organizer_id == User.id)
        .filter(Event.status == "approved")
        .group_by(User.id)
        .order_by(func.count(Event.id).desc())
        .limit(5)
        .all()
    )

    # Monthly participation (registrations grouped by month)
    monthly = (
        db.session.query(
            func.strftime("%Y-%m", Registration.registered_at).label("month"),
            func.count(Registration.id),
        )
        .group_by("month")
        .order_by("month")
        .all()
    )

    avg_rating = db.session.query(func.avg(Feedback.rating)).scalar()

    return render_template(
        "admin/reports.html",
        events_by_category=events_by_category,
        popular_events=popular_events,
        top_organizers=top_organizers,
        monthly=monthly,
        avg_rating=round(avg_rating, 2) if avg_rating else None,
    )
