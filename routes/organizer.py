import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import Event, Registration, Certificate
from forms import EventForm
from decorators import role_required
from certificates.generator import generate_certificate

organizer_bp = Blueprint("organizer", __name__)


def _save_poster(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file_storage.save(path)
    return filename


@organizer_bp.route("/dashboard")
@login_required
@role_required("organizer")
def dashboard():
    events = Event.query.filter_by(organizer_id=current_user.id).order_by(Event.event_date.desc()).all()
    counts = {
        "total": len(events),
        "pending": sum(1 for e in events if e.status == "pending"),
        "approved": sum(1 for e in events if e.status == "approved"),
        "rejected": sum(1 for e in events if e.status == "rejected"),
    }
    return render_template("organizer/dashboard.html", events=events, counts=counts)


@organizer_bp.route("/events/new", methods=["GET", "POST"])
@login_required
@role_required("organizer")
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        poster_filename = _save_poster(form.poster.data)
        event = Event(
            title=form.title.data,
            description=form.description.data,
            category=form.category.data,
            venue=form.venue.data,
            event_date=form.event_date.data,
            event_time=form.event_time.data,
            max_participants=form.max_participants.data or 0,
            poster_filename=poster_filename,
            organizer_id=current_user.id,
            status="pending",
        )
        db.session.add(event)
        db.session.commit()
        flash("Event submitted for admin approval.", "success")
        return redirect(url_for("organizer.dashboard"))
    return render_template("organizer/event_form.html", form=form, mode="Create")


@organizer_bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("organizer")
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.organizer_id != current_user.id:
        abort(403)

    form = EventForm(obj=event)
    if form.validate_on_submit():
        event.title = form.title.data
        event.description = form.description.data
        event.category = form.category.data
        event.venue = form.venue.data
        event.event_date = form.event_date.data
        event.event_time = form.event_time.data
        event.max_participants = form.max_participants.data or 0

        new_poster = _save_poster(form.poster.data)
        if new_poster:
            event.poster_filename = new_poster

        # Editing sends it back for re-approval
        event.status = "pending"
        db.session.commit()
        flash("Event updated and resubmitted for approval.", "success")
        return redirect(url_for("organizer.dashboard"))

    return render_template("organizer/event_form.html", form=form, mode="Edit", event=event)


@organizer_bp.route("/events/<int:event_id>/delete", methods=["POST"])
@login_required
@role_required("organizer")
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.organizer_id != current_user.id:
        abort(403)
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted.", "info")
    return redirect(url_for("organizer.dashboard"))


@organizer_bp.route("/events/<int:event_id>/participants")
@login_required
@role_required("organizer")
def participants(event_id):
    event = Event.query.get_or_404(event_id)
    if event.organizer_id != current_user.id:
        abort(403)
    registrations = Registration.query.filter_by(event_id=event.id).all()
    return render_template("organizer/participants.html", event=event, registrations=registrations)


@organizer_bp.route("/registrations/<int:registration_id>/attendance", methods=["POST"])
@login_required
@role_required("organizer")
def mark_attendance(registration_id):
    reg = Registration.query.get_or_404(registration_id)
    if reg.event.organizer_id != current_user.id:
        abort(403)

    reg.attended = not reg.attended
    db.session.commit()

    # Auto-generate a certificate the first time a student is marked as attended
    if reg.attended and not reg.certificate:
        filename = generate_certificate(
            student_name=reg.student.full_name,
            event_title=reg.event.title,
            event_date=reg.event.event_date,
        )
        cert = Certificate(registration_id=reg.id, filename=filename)
        db.session.add(cert)
        db.session.commit()
        flash(f"Attendance marked and certificate generated for {reg.student.full_name}.", "success")
    else:
        db.session.commit()
        flash("Attendance updated.", "info")

    return redirect(url_for("organizer.participants", event_id=reg.event_id))
