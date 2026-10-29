from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User
from forms import RegisterForm, LoginForm

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard_redirect"))

    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if existing:
            flash("An account with that email already exists. Please log in.", "danger")
            return redirect(url_for("auth.login"))

        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.lower().strip(),
            role=form.role.data,
            department=form.department.data,
            roll_number=form.roll_number.data,
            club_name=form.club_name.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard_redirect"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f"Welcome back, {user.full_name}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("auth.dashboard_redirect"))
        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard_redirect():
    """Send the user to the right dashboard based on their role."""
    if current_user.is_student:
        return redirect(url_for("student.dashboard"))
    if current_user.is_organizer:
        return redirect(url_for("organizer.dashboard"))
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("auth.login"))
