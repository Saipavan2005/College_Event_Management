"""
JSON REST API for the mobile app (Android/iOS via React Native).

The existing routes/{auth,student,organizer,admin}.py power the
session-based Bootstrap website. This blueprint is a parallel,
token-based (JWT) API that exposes the same functionality as JSON,
so a separate mobile frontend can talk to this same Flask backend
and database.

All routes are prefixed with /api/v1 (see app.py registration).
"""
import os
import uuid
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import func
from werkzeug.utils import secure_filename

from extensions import db
from models import User, Event, Registration, Certificate, Feedback
from decorators import api_role_required
from certificates.generator import generate_certificate

api_bp = Blueprint("api", __name__)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def serialize_user(user):
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "department": user.department,
        "roll_number": user.roll_number,
        "club_name": user.club_name,
    }


def serialize_event(event, student_id=None):
    data = {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "category": event.category,
        "venue": event.venue,
        "event_date": event.event_date.isoformat(),
        "event_time": event.event_time.strftime("%H:%M"),
        "poster_url": (
            f"{request.host_url.rstrip('/')}/posters/{event.poster_filename}"
            if event.poster_filename else None
        ),
        "max_participants": event.max_participants,
        "seats_taken": event.seats_taken,
        "seats_left": event.seats_left,
        "is_full": event.is_full,
        "is_past": event.is_past,
        "status": event.status,
        "organizer_id": event.organizer_id,
        "organizer_name": event.organizer.full_name if event.organizer else None,
    }
    if student_id:
        reg = Registration.query.filter_by(student_id=student_id, event_id=event.id).first()
        data["is_registered"] = reg is not None
        data["attended"] = reg.attended if reg else False
    return data


def serialize_registration(reg):
    return {
        "id": reg.id,
        "event": serialize_event(reg.event),
        "registered_at": reg.registered_at.isoformat(),
        "attended": reg.attended,
        "has_certificate": reg.certificate is not None,
        "certificate_id": reg.certificate.id if reg.certificate else None,
    }


def serialize_certificate(cert):
    return {
        "id": cert.id,
        "event_title": cert.registration.event.title,
        "issued_at": cert.issued_at.isoformat(),
        "download_url": f"{request.host_url.rstrip('/')}/api/v1/student/certificates/{cert.id}/download",
    }


def current_api_user_from_jwt():
    return User.query.get(int(get_jwt_identity()))


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@api_bp.route("/auth/register", methods=["POST"])
def api_register():
    data = request.get_json(force=True, silent=True) or {}
    required = ["full_name", "email", "password", "role"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    if data["role"] not in ("student", "organizer"):
        return jsonify(error="role must be 'student' or 'organizer'"), 400

    email = data["email"].lower().strip()
    if User.query.filter_by(email=email).first():
        return jsonify(error="An account with that email already exists."), 409

    user = User(
        full_name=data["full_name"].strip(),
        email=email,
        role=data["role"],
        department=data.get("department"),
        roll_number=data.get("roll_number"),
        club_name=data.get("club_name"),
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify(access_token=token, user=serialize_user(user)), 201


@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").lower().strip()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify(error="Invalid email or password"), 401

    token = create_access_token(identity=str(user.id))
    return jsonify(access_token=token, user=serialize_user(user))


@api_bp.route("/auth/me", methods=["GET"])
@jwt_required()
def api_me():
    user = current_api_user_from_jwt()
    if not user:
        return jsonify(error="User not found"), 404
    return jsonify(user=serialize_user(user))


# ---------------------------------------------------------------------------
# Events (shared: browsing is student-facing, but detail works for anyone)
# ---------------------------------------------------------------------------

@api_bp.route("/events", methods=["GET"])
@jwt_required()
def api_list_events():
    user = current_api_user_from_jwt()
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["EVENTS_PER_PAGE"]

    query = Event.query.filter_by(status="approved")
    if search:
        query = query.filter(Event.title.ilike(f"%{search}%"))
    if category:
        query = query.filter_by(category=category)
    query = query.order_by(Event.event_date.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    student_id = user.id if user.is_student else None

    return jsonify(
        events=[serialize_event(e, student_id=student_id) for e in pagination.items],
        page=pagination.page,
        pages=pagination.pages,
        total=pagination.total,
    )


@api_bp.route("/events/<int:event_id>", methods=["GET"])
@jwt_required()
def api_event_detail(event_id):
    user = current_api_user_from_jwt()
    event = Event.query.get_or_404(event_id)
    student_id = user.id if user.is_student else None
    return jsonify(event=serialize_event(event, student_id=student_id))


@api_bp.route("/events/<int:event_id>/register", methods=["POST"])
@api_role_required("student")
def api_register_event(event_id, current_api_user):
    event = Event.query.get_or_404(event_id)

    if event.status != "approved":
        return jsonify(error="This event is not open for registration."), 400
    if event.is_past:
        return jsonify(error="This event has already taken place."), 400
    if Registration.query.filter_by(student_id=current_api_user.id, event_id=event.id).first():
        return jsonify(error="You are already registered for this event."), 409
    if event.is_full:
        return jsonify(error="Sorry, this event is full."), 400

    reg = Registration(student_id=current_api_user.id, event_id=event.id)
    db.session.add(reg)
    db.session.commit()
    return jsonify(message="Registered successfully.", registration=serialize_registration(reg)), 201


@api_bp.route("/events/<int:event_id>/cancel", methods=["POST"])
@api_role_required("student")
def api_cancel_registration(event_id, current_api_user):
    reg = Registration.query.filter_by(student_id=current_api_user.id, event_id=event_id).first()
    if not reg:
        return jsonify(error="Registration not found."), 404
    db.session.delete(reg)
    db.session.commit()
    return jsonify(message="Registration cancelled.")


@api_bp.route("/events/<int:event_id>/feedback", methods=["POST"])
@api_role_required("student")
def api_leave_feedback(event_id, current_api_user):
    data = request.get_json(force=True, silent=True) or {}
    rating = data.get("rating")
    if not rating or not (1 <= int(rating) <= 5):
        return jsonify(error="rating must be an integer from 1 to 5"), 400

    reg = Registration.query.filter_by(student_id=current_api_user.id, event_id=event_id).first()
    if not reg:
        return jsonify(error="You must be registered for this event to leave feedback."), 403

    existing = Feedback.query.filter_by(student_id=current_api_user.id, event_id=event_id).first()
    if existing:
        existing.rating = int(rating)
        existing.comments = data.get("comments")
    else:
        fb = Feedback(
            student_id=current_api_user.id, event_id=event_id,
            rating=int(rating), comments=data.get("comments"),
        )
        db.session.add(fb)
    db.session.commit()
    return jsonify(message="Thanks for your feedback!")


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------

@api_bp.route("/student/dashboard", methods=["GET"])
@api_role_required("student")
def api_student_dashboard(current_api_user):
    upcoming_count = Registration.query.join(Event).filter(
        Registration.student_id == current_api_user.id,
        Event.event_date >= db.func.current_date()
    ).count()
    total_registrations = Registration.query.filter_by(student_id=current_api_user.id).count()
    certificates_earned = Certificate.query.join(Registration).filter(
        Registration.student_id == current_api_user.id
    ).count()
    return jsonify(
        upcoming_count=upcoming_count,
        total_registrations=total_registrations,
        certificates_earned=certificates_earned,
    )


@api_bp.route("/student/my-events", methods=["GET"])
@api_role_required("student")
def api_my_events(current_api_user):
    regs = (
        Registration.query.filter_by(student_id=current_api_user.id)
        .join(Event).order_by(Event.event_date.asc()).all()
    )
    return jsonify(registrations=[serialize_registration(r) for r in regs])


@api_bp.route("/student/certificates", methods=["GET"])
@api_role_required("student")
def api_certificates(current_api_user):
    certs = (
        Certificate.query.join(Registration)
        .filter(Registration.student_id == current_api_user.id).all()
    )
    return jsonify(certificates=[serialize_certificate(c) for c in certs])


@api_bp.route("/student/certificates/<int:cert_id>/download", methods=["GET"])
@jwt_required()
def api_download_certificate(cert_id):
    user = current_api_user_from_jwt()
    cert = Certificate.query.get_or_404(cert_id)
    if cert.registration.student_id != user.id:
        return jsonify(error="Forbidden"), 403
    return send_from_directory(current_app.config["CERTIFICATE_FOLDER"], cert.filename, as_attachment=True)


@api_bp.route("/student/profile", methods=["GET", "PUT"])
@api_role_required("student")
def api_student_profile(current_api_user):
    if request.method == "GET":
        return jsonify(user=serialize_user(current_api_user))

    data = request.get_json(force=True, silent=True) or {}
    current_api_user.full_name = data.get("full_name", current_api_user.full_name)
    current_api_user.department = data.get("department", current_api_user.department)
    current_api_user.roll_number = data.get("roll_number", current_api_user.roll_number)
    db.session.commit()
    return jsonify(message="Profile updated.", user=serialize_user(current_api_user))


# ---------------------------------------------------------------------------
# Organizer
# ---------------------------------------------------------------------------

def _save_poster(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        return None
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file_storage.save(path)
    return filename


@api_bp.route("/organizer/dashboard", methods=["GET"])
@api_role_required("organizer")
def api_organizer_dashboard(current_api_user):
    events = Event.query.filter_by(organizer_id=current_api_user.id).order_by(Event.event_date.desc()).all()
    counts = {
        "total": len(events),
        "pending": sum(1 for e in events if e.status == "pending"),
        "approved": sum(1 for e in events if e.status == "approved"),
        "rejected": sum(1 for e in events if e.status == "rejected"),
    }
    return jsonify(events=[serialize_event(e) for e in events], counts=counts)


@api_bp.route("/organizer/events", methods=["POST"])
@api_role_required("organizer")
def api_create_event(current_api_user):
    # Accepts multipart/form-data (for optional poster) or plain JSON
    form = request.form if request.form else (request.get_json(force=True, silent=True) or {})
    required = ["title", "description", "venue", "event_date", "event_time"]
    missing = [f for f in required if not form.get(f)]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    try:
        event_date = datetime.strptime(form["event_date"], "%Y-%m-%d").date()
        event_time = datetime.strptime(form["event_time"], "%H:%M").time()
    except ValueError:
        return jsonify(error="event_date must be YYYY-MM-DD and event_time must be HH:MM"), 400

    poster_filename = _save_poster(request.files.get("poster")) if request.files else None

    event = Event(
        title=form["title"], description=form["description"],
        category=form.get("category", "General"), venue=form["venue"],
        event_date=event_date, event_time=event_time,
        max_participants=int(form.get("max_participants") or 0),
        poster_filename=poster_filename,
        organizer_id=current_api_user.id, status="pending",
    )
    db.session.add(event)
    db.session.commit()
    return jsonify(message="Event submitted for admin approval.", event=serialize_event(event)), 201


@api_bp.route("/organizer/events/<int:event_id>", methods=["PUT"])
@api_role_required("organizer")
def api_edit_event(event_id, current_api_user):
    event = Event.query.get_or_404(event_id)
    if event.organizer_id != current_api_user.id:
        return jsonify(error="Forbidden"), 403

    form = request.form if request.form else (request.get_json(force=True, silent=True) or {})
    for field in ("title", "description", "venue"):
        if form.get(field):
            setattr(event, field, form[field])
    if form.get("category"):
        event.category = form["category"]
    if form.get("event_date"):
        event.event_date = datetime.strptime(form["event_date"], "%Y-%m-%d").date()
    if form.get("event_time"):
        event.event_time = datetime.strptime(form["event_time"], "%H:%M").time()
    if form.get("max_participants") is not None and form.get("max_participants") != "":
        event.max_participants = int(form["max_participants"])
    if request.files and request.files.get("poster"):
        new_poster = _save_poster(request.files.get("poster"))
        if new_poster:
            event.poster_filename = new_poster

    event.status = "pending"  # edits require re-approval
    db.session.commit()
    return jsonify(message="Event updated and resubmitted for approval.", event=serialize_event(event))


@api_bp.route("/organizer/events/<int:event_id>", methods=["DELETE"])
@api_role_required("organizer")
def api_delete_event(event_id, current_api_user):
    event = Event.query.get_or_404(event_id)
    if event.organizer_id != current_api_user.id:
        return jsonify(error="Forbidden"), 403
    db.session.delete(event)
    db.session.commit()
    return jsonify(message="Event deleted.")


@api_bp.route("/organizer/events/<int:event_id>/participants", methods=["GET"])
@api_role_required("organizer")
def api_participants(event_id, current_api_user):
    event = Event.query.get_or_404(event_id)
    if event.organizer_id != current_api_user.id:
        return jsonify(error="Forbidden"), 403
    regs = Registration.query.filter_by(event_id=event.id).all()
    return jsonify(
        event=serialize_event(event),
        participants=[
            {
                "registration_id": r.id,
                "student": serialize_user(r.student),
                "registered_at": r.registered_at.isoformat(),
                "attended": r.attended,
                "has_certificate": r.certificate is not None,
            }
            for r in regs
        ],
    )


@api_bp.route("/organizer/registrations/<int:registration_id>/attendance", methods=["POST"])
@api_role_required("organizer")
def api_mark_attendance(registration_id, current_api_user):
    reg = Registration.query.get_or_404(registration_id)
    if reg.event.organizer_id != current_api_user.id:
        return jsonify(error="Forbidden"), 403

    reg.attended = not reg.attended
    cert_generated = False

    if reg.attended and not reg.certificate:
        filename = generate_certificate(
            student_name=reg.student.full_name,
            event_title=reg.event.title,
            event_date=reg.event.event_date,
        )
        cert = Certificate(registration_id=reg.id, filename=filename)
        db.session.add(cert)
        cert_generated = True

    db.session.commit()
    return jsonify(
        message="Certificate generated." if cert_generated else "Attendance updated.",
        attended=reg.attended,
        certificate_generated=cert_generated,
    )


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@api_bp.route("/admin/dashboard", methods=["GET"])
@api_role_required("admin")
def api_admin_dashboard(current_api_user):
    stats = {
        "total_students": User.query.filter_by(role="student").count(),
        "total_organizers": User.query.filter_by(role="organizer").count(),
        "total_events": Event.query.count(),
        "pending_events": Event.query.filter_by(status="pending").count(),
        "total_registrations": Registration.query.count(),
    }
    pending = Event.query.filter_by(status="pending").order_by(Event.created_at.desc()).all()
    return jsonify(stats=stats, pending_events=[serialize_event(e) for e in pending])


@api_bp.route("/admin/events", methods=["GET"])
@api_role_required("admin")
def api_admin_events(current_api_user):
    events = Event.query.order_by(Event.created_at.desc()).all()
    return jsonify(events=[serialize_event(e) for e in events])


@api_bp.route("/admin/events/<int:event_id>/approve", methods=["POST"])
@api_role_required("admin")
def api_approve_event(event_id, current_api_user):
    event = Event.query.get_or_404(event_id)
    event.status = "approved"
    db.session.commit()
    return jsonify(message=f'"{event.title}" approved.', event=serialize_event(event))


@api_bp.route("/admin/events/<int:event_id>/reject", methods=["POST"])
@api_role_required("admin")
def api_reject_event(event_id, current_api_user):
    event = Event.query.get_or_404(event_id)
    event.status = "rejected"
    db.session.commit()
    return jsonify(message=f'"{event.title}" rejected.', event=serialize_event(event))


@api_bp.route("/admin/users", methods=["GET"])
@api_role_required("admin")
def api_admin_users(current_api_user):
    students = User.query.filter_by(role="student").order_by(User.full_name).all()
    organizers = User.query.filter_by(role="organizer").order_by(User.full_name).all()
    return jsonify(
        students=[serialize_user(u) for u in students],
        organizers=[serialize_user(u) for u in organizers],
    )


@api_bp.route("/admin/users/<int:user_id>", methods=["DELETE"])
@api_role_required("admin")
def api_delete_user(user_id, current_api_user):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        return jsonify(error="Cannot delete an admin account from this endpoint."), 403
    db.session.delete(user)
    db.session.commit()
    return jsonify(message=f"{user.full_name}'s account was removed.")


@api_bp.route("/admin/reports", methods=["GET"])
@api_role_required("admin")
def api_reports(current_api_user):
    events_by_category = (
        db.session.query(Event.category, func.count(Event.id)).group_by(Event.category).all()
    )
    popular_events = (
        db.session.query(Event.title, func.count(Registration.id).label("count"))
        .join(Registration, Registration.event_id == Event.id)
        .group_by(Event.id).order_by(func.count(Registration.id).desc()).limit(5).all()
    )
    top_organizers = (
        db.session.query(User.full_name, func.count(Event.id).label("count"))
        .join(Event, Event.organizer_id == User.id)
        .filter(Event.status == "approved")
        .group_by(User.id).order_by(func.count(Event.id).desc()).limit(5).all()
    )
    monthly = (
        db.session.query(
            func.strftime("%Y-%m", Registration.registered_at).label("month"),
            func.count(Registration.id),
        ).group_by("month").order_by("month").all()
    )
    avg_rating = db.session.query(func.avg(Feedback.rating)).scalar()

    return jsonify(
        events_by_category=[{"category": c, "count": n} for c, n in events_by_category],
        popular_events=[{"title": t, "count": n} for t, n in popular_events],
        top_organizers=[{"name": n, "count": c} for n, c in top_organizers],
        monthly=[{"month": m, "count": n} for m, n in monthly],
        avg_rating=round(avg_rating, 2) if avg_rating else None,
    )
