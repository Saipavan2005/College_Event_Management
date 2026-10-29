import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Secret key (used to sign sessions / cookies) ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-this-in-production")

    # --- JWT (mobile app API auth) ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-this-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 24 * 7  # 7 days, in seconds
    JWT_TOKEN_LOCATION = ["headers"]

    # --- Database ---
    # Default: SQLite, zero setup, great for learning & local dev.
    # To switch to MySQL for production:
    #   1) pip install pymysql
    #   2) set env var DATABASE_URL, e.g.:
    #      mysql+pymysql://root:yourpassword@localhost/college_events
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'college_events.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- File uploads ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "posters")
    CERTIFICATE_FOLDER = os.path.join(BASE_DIR, "certificates")
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload

    # --- Pagination ---
    EVENTS_PER_PAGE = 9
