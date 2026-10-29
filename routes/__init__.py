from .auth import auth_bp
from .student import student_bp
from .organizer import organizer_bp
from .admin import admin_bp

__all__ = ["auth_bp", "student_bp", "organizer_bp", "admin_bp"]
