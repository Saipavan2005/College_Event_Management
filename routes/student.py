import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app, abort
from flask_login import login_required, current_user

from extensions import db
from models import Event, Registration, Certificate, Feedback
from forms import ProfileForm, FeedbackForm
from decorators import role_required
from certificates.generator import generate_certificate

student_bp = Blueprint("student", __name__)


@student_bp.route("/dashboard")
@login_required
@role_required("student")
def dashboard():
    upcoming_count = Registration.query.join(Event).filter(
        Registration.student_id == current_user.id,
        Event.event_date >= db.func.current_date()
    ).count()
    total_registrations = Registration.query.filter_by(student_id=current_user.id).count()
    certificates_earned = Certificate.query.join(Registration).filter(
        Registration.student_id == current_user.id
    ).count()

    return render_template(
        "student/dashboard.html",
        upcoming_count=upcoming_count,
        total_registrations=total_registrations,
        certificates_earned=certificates_earned,
    )


@student_bp.route("/events")
@login_required
@role_required("student")
def browse_events():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Event.query.filter_by(status="approved")
    if search:
        query = query.filter(Event.title.ilike(f"%{search}%"))
    if category:
        query = query.filter_by(category=category)

    query = query.order_by(Event.event_date.asc())
    pagination = query.paginate(page=page, per_page=current_app.config["EVENTS_PER_PAGE"], error_out=False)

    my_event_ids = {r.event_id for r in Registration.query.filter_by(student_id=current_user.id).all()}
    categories = ["Technical", "Cultural", "Sports", "Workshop", "General"]

    return render_template(
        "student/browse_events.html",
        pagination=pagination,
        events=pagination.items,
        my_event_ids=my_event_ids,
        search=search,
        category=category,
        categories=categories,
    )


@student_bp.route("/events/<int:event_id>")
@login_required
@role_required("student")
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    registration = Registration.query.filter_by(student_id=current_user.id, event_id=event.id).first()
    return render_template("student/event_detail.html", event=event, registration=registration)


@student_bp.route("/events/<int:event_id>/register", methods=["POST"])
@login_required
@role_required("student")
def register_event(event_id):
    event = Event.query.get_or_404(event_id)

    if event.status != "approved":
        flash("This event is not open for registration.", "danger")
        return redirect(url_for("student.browse_events"))

    if event.is_past:
        flash("This event has already taken place.", "warning")
        return redirect(url_for("student.event_detail", event_id=event.id))

    existing = Registration.query.filter_by(student_id=current_user.id, event_id=event.id).first()
    if existing:
        flash("You are already registered for this event.", "info")
        return redirect(url_for("student.event_detail", event_id=event.id))

    if event.is_full:
        flash("Sorry, this event is full.", "danger")
        return redirect(url_for("student.event_detail", event_id=event.id))

    reg = Registration(student_id=current_user.id, event_id=event.id)
    db.session.add(reg)
    db.session.commit()
    flash(f"You're registered for \"{event.title}\"!", "success")
    return redirect(url_for("student.event_detail", event_id=event.id))


@student_bp.route("/events/<int:event_id>/cancel", methods=["POST"])
@login_required
@role_required("student")
def cancel_registration(event_id):
    reg = Registration.query.filter_by(student_id=current_user.id, event_id=event_id).first_or_404()
    db.session.delete(reg)
    db.session.commit()
    flash("Registration cancelled.", "info")
    return redirect(url_for("student.browse_events"))


@student_bp.route("/my-events")
@login_required
@role_required("student")
def my_events():
    registrations = (
        Registration.query.filter_by(student_id=current_user.id)
        .join(Event)
        .order_by(Event.event_date.asc())
        .all()
    )
    return render_template("student/my_events.html", registrations=registrations)


@student_bp.route("/events/<int:event_id>/feedback", methods=["GET", "POST"])
@login_required
@role_required("student")
def leave_feedback(event_id):
    event = Event.query.get_or_404(event_id)
    reg = Registration.query.filter_by(student_id=current_user.id, event_id=event.id).first()
    if not reg:
        abort(403)

    existing = Feedback.query.filter_by(student_id=current_user.id, event_id=event.id).first()
    form = FeedbackForm(obj=existing)

    if form.validate_on_submit():
        if existing:
            existing.rating = int(form.rating.data)
            existing.comments = form.comments.data
        else:
            fb = Feedback(
                student_id=current_user.id, event_id=event.id,
                rating=int(form.rating.data), comments=form.comments.data
            )
            db.session.add(fb)
        db.session.commit()
        flash("Thanks for your feedback!", "success")
        return redirect(url_for("student.my_events"))

    return render_template("student/feedback.html", form=form, event=event)


@student_bp.route("/certificates")
@login_required
@role_required("student")
def certificates():
    certs = (
        Certificate.query.join(Registration)
        .filter(Registration.student_id == current_user.id)
        .all()
    )
    return render_template("student/certificates.html", certs=certs)


@student_bp.route("/certificates/<int:cert_id>/download")
@login_required
@role_required("student")
def download_certificate(cert_id):
    cert = Certificate.query.get_or_404(cert_id)
    if cert.registration.student_id != current_user.id:
        abort(403)
    return send_from_directory(current_app.config["CERTIFICATE_FOLDER"], cert.filename, as_attachment=True)


@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("student")
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.department = form.department.data
        current_user.roll_number = form.roll_number.data
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("student.profile"))
    return render_template("student/profile.html", form=form)
