import os
from datetime import datetime
from flask import Flask, render_template, send_from_directory
from flask_wtf import CSRFProtect
from flask_cors import CORS

from config import Config
from extensions import db, login_manager, jwt


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Make sure upload/certificate folders exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["CERTIFICATE_FOLDER"], exist_ok=True)

    # --- Extensions ---
    db.init_app(app)
    login_manager.init_app(app)
    csrf = CSRFProtect(app)
    jwt.init_app(app)
    # Mobile app origin(s) — loosen/tighten as needed for your setup
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # --- Blueprints ---
    from routes import auth_bp, student_bp, organizer_bp, admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(organizer_bp, url_prefix="/organizer")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    # The JSON API is authenticated with JWT bearer tokens (not cookies),
    # so it isn't subject to CSRF the way the session-based web app is.
    csrf.exempt(api_bp)

    # --- Public routes ---
    @app.route("/")
    def home():
        from models import Event
        featured = Event.query.filter_by(status="approved").order_by(Event.event_date.asc()).limit(6).all()
        return render_template("home.html", events=featured)

    @app.route("/posters/<path:filename>")
    def poster_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # --- Error pages ---
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    # --- Template globals ---
    @app.context_processor
    def inject_now():
        return {"current_year": datetime.utcnow().year}

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
