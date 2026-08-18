# Student Management System (SMS)

Дипломный инженерный проект: веб-приложение на Django для управления студентами, курсами, оценками и посещаемостью.

## Stack

- Python 3.10+ / Django 6
- SQLite (local) / PostgreSQL via `DATABASE_URL` (production)
- Gunicorn + WhiteNoise
- Session auth + RBAC (admin / teacher / student)
- SMTP / console email for password reset

## Quick start

```bash
cd DiplomCode
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000

## Tests

```bash
python manage.py test
```

## Production notes

Set environment variables (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Required when `DEBUG=False` |
| `DEBUG` | `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `DATABASE_URL` | Postgres connection string |
| `EMAIL_BACKEND` | `console` or `smtp` |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP |
| `CSRF_TRUSTED_ORIGINS` | e.g. `https://your-app.onrender.com` |

`build.sh` runs `collectstatic` + `migrate` for PaaS deploy (e.g. Render).

## Main features

- Login / logout / profile
- Password reset by email (`/accounts/password_reset/`)
- Students, courses, enrolments, grades, attendance
- Role-scoped dashboard + JSON API `GET /api/dashboard/`
- CSV export for students and grades

## Project layout

- `core/` — models, views, forms, tests
- `sms_project/` — settings, WSGI
- `templates/` — HTML
- `static/` — CSS / JS
- `docs/` — diploma documentation DOCX
- `scripts/generate_diploma_docs.py` — regenerate documentation

## Documentation

English diploma documentation (BloomTime-style structure):

`docs/SMS_Diploma_Documentation_Shpak_Maksym.docx`
