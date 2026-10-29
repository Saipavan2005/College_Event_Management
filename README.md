# College Event Management Platform

A full-stack Flask web app for managing college events: students browse and
register for events, organizers create and run them, and admins approve
events, manage users, and view analytics. Attendance marking auto-generates
a PDF certificate for each student.

## Tech Stack

| Layer          | Technology                          |
|----------------|--------------------------------------|
| Frontend       | HTML5, Bootstrap 5, vanilla JS       |
| Backend        | Python (Flask)                       |
| Database       | SQLite by default (MySQL-ready)      |
| ORM            | SQLAlchemy (Flask-SQLAlchemy)        |
| Authentication | Flask-Login + password hashing       |
| Forms          | Flask-WTF (CSRF protection built-in) |
| PDF Certificates | ReportLab                          |

## Project Structure

```
College_Event_Management/
├── app.py                 # App factory, blueprint registration, entry point
├── config.py               # All configuration (DB URI, upload folders, etc.)
├── extensions.py           # Shared db / login_manager instances
├── decorators.py           # @role_required(...) access control
├── forms.py                 # Flask-WTF forms (register, login, event, etc.)
├── seed_admin.py            # Creates the first admin account
├── requirements.txt
│
├── models/
│   ├── user.py              # User (role: student/organizer/admin)
│   ├── event.py              # Event
│   ├── registration.py       # Registration + Certificate
│   └── feedback.py           # Feedback
│
├── routes/
│   ├── auth.py               # register / login / logout
│   ├── student.py            # browse/register events, certificates, profile
│   ├── organizer.py          # create/edit/delete events, attendance
│   └── admin.py               # approve events, manage users, reports
│
├── certificates/
│   └── generator.py          # ReportLab PDF certificate builder
│
├── templates/                # Jinja2 + Bootstrap 5 templates
├── static/css, static/js
├── uploads/posters/           # Event poster images
└── certificates/              # Generated PDF certificates land here
```

### Why one `User` table instead of three (Students / Organizers / Admin)?
Login, logout, and password handling are identical for every role, so one
table + a `role` column keeps Flask-Login simple while every route still
enforces role-based access via the `@role_required(...)` decorator. Adding a
new role later means adding a value, not a parallel login system.

## Setup

```bash
cd College_Event_Management
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

python seed_admin.py            # creates tables + first admin account
python app.py                   # runs on http://127.0.0.1:5000
```

Default admin login (change the password after first login):
- Email: `admin@college.edu`
- Password: `Admin@123`

Sign up as a Student or Organizer from the app's Register page — the
registration form intentionally does not offer "Admin" as an option.

## Switching from SQLite to MySQL

The app runs on SQLite out of the box (zero setup). To use MySQL instead:

```bash
pip install pymysql
export DATABASE_URL="mysql+pymysql://root:yourpassword@localhost/college_events"
python seed_admin.py
python app.py
```

Create the MySQL database first: `CREATE DATABASE college_events;`

> Note: the admin "Monthly Participation" report uses SQLite's `strftime()`.
> On MySQL, swap that one query in `routes/admin.py` for
> `func.date_format(Registration.registered_at, '%Y-%m')`.

## How the 12 Phases Map to This Code

| Phase | Where it lives |
|---|---|
| 1. Environment Setup | `requirements.txt`, this README |
| 2. Project Structure | Folder layout above |
| 3. Database Design | `models/` (User, Event, Registration, Certificate, Feedback) |
| 4. Authentication | `routes/auth.py`, `forms.py`, password hashing in `models/user.py` |
| 5. Student Dashboard | `routes/student.py`, `templates/student/*` |
| 6. Organizer Dashboard | `routes/organizer.py`, `templates/organizer/*` |
| 7. Admin Dashboard | `routes/admin.py`, `templates/admin/*` |
| 8. Event Registration | `student.register_event` / `cancel_registration` (unique constraint blocks duplicates) |
| 9. Certificate Generator | `certificates/generator.py`, triggered from `organizer.mark_attendance` |
| 10. Reports & Analytics | `admin.reports` route + `templates/admin/reports.html` |
| 11. UI Improvements | Bootstrap 5 responsive layout, search + category filters, `data-confirm` JS |
| 12. Deployment | See below |

## Core Workflows

1. **Organizer** creates an event → status `pending`.
2. **Admin** approves or rejects it from the dashboard.
3. **Student** browses approved events, registers (duplicates and full events are blocked).
4. **Organizer** marks students present on the participants page — this
   auto-generates a PDF certificate the first time a student is marked.
5. **Student** downloads their certificate from "My Certificates".
6. **Student** can leave a 1–5 star rating + comment once the event has passed.
7. **Admin** views category breakdowns, most popular events, top organizers,
   monthly participation, and average feedback rating under Reports.

## Deployment Notes

- Set a real `SECRET_KEY` via environment variable in production.
- Switch `DATABASE_URL` to your MySQL instance (see above).
- Run behind a production WSGI server, e.g.:
  ```bash
  pip install gunicorn
  gunicorn -w 4 -b 0.0.0.0:8000 "app:app"
  ```
- Push to GitHub, then deploy to a host like Render, Railway, or PythonAnywhere.
- Make sure `uploads/` and `certificates/` are persistent storage (not
  ephemeral) on whatever host you choose, or switch to S3-style storage.
