from functools import wraps
from flask import abort, jsonify
from flask_login import current_user
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity


def role_required(*roles):
    """
    Usage:
        @role_required("organizer")
        def create_event(): ...

        @role_required("admin", "organizer")
        def some_shared_view(): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


def api_role_required(*roles):
    """
    Same idea as role_required, but for JWT-authenticated JSON API routes
    (used by the mobile app instead of the session-based web app).

    Usage:
        @api_role_required("organizer")
        def api_create_event(): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            verify_jwt_in_request()
            from models import User
            user = User.query.get(int(get_jwt_identity()))
            if not user or user.role not in roles:
                return jsonify(error="Forbidden"), 403
            kwargs["current_api_user"] = user
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
