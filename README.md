# Student Management System (SMS)

Дипломный инженерный проект: веб-приложение на Django для управления студентами, курсами, оценками и посещаемостью.

## Stack

- Python 3.10+ / Django 6
- SQLite (local) / PostgreSQL via `DATABASE_URL` (production)
- Gunicorn + WhiteNoise
- Session auth + RBAC (admin / teacher)
- Polish / English interface (`django.po`, `set_language`)
- SMTP / console email for password reset
- Self-hosted front-end assets — no CDN, no internet needed at runtime

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

45 tests cover models, authentication, role-based access and data isolation,
pagination, the dashboard JSON API, password-reset email, enrolment capacity
rules, grade authorship, Polish localisation, the deployment seed step, and a
smoke render of every page for both roles.

`.github/workflows/ci.yml` runs the same suite on every push, plus a check for
missing migrations and `manage.py check --deploy` against production settings.

## Translations

The interface is fully translated into Polish (239 messages, 0 untranslated).

```bash
python manage.py makemessages -l pl --ignore=.venv --ignore=staticfiles
python scripts/fill_pl_translations.py   # fill new strings, drop fuzzy guesses
python manage.py compilemessages -l pl --ignore=.venv
```

## Front-end assets

Bootstrap, Bootstrap Icons, Chart.js, Turbo and the DM Sans / Inter web fonts
are vendored under `static/vendor/`, so the interface renders identically on a
machine with no internet connection. Refresh the fonts with:

```bash
python scripts/vendor_fonts.py
```

## Production notes

Set environment variables (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Required when `DEBUG=False` |
| `DEBUG` | `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `DATABASE_URL` | Postgres connection string |
| `DJANGO_ADMIN_PASSWORD` | Replaces the published demo password on the `admin` account |
| `EMAIL_BACKEND` | `console` or `smtp` |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP |
| `CSRF_TRUSTED_ORIGINS` | e.g. `https://your-app.onrender.com` |

## Deployment

`render.yaml` describes the whole service as code, so the deploy is reproducible:
create it on Render via **New → Blueprint** and point it at this repository.

`build.sh` is the build step. It compiles the Polish catalogue, collects static
files, applies migrations and calls `seed_demo`, which loads `demo_data` **only
into an empty database** — an already-running deployment keeps its data.

The database is external managed Postgres (the free tier of Render's own
Postgres is deleted 30 days after creation, which is unsuitable for a project
that must stay online). Paste the connection string into `DATABASE_URL`.

Demo accounts shipped in the fixture use the password `demo1234`. Set
`DJANGO_ADMIN_PASSWORD` on the platform to give the `admin` account a private
password without committing it.

Rehearse the production build locally before pushing:

```bash
export DEBUG=False SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(64))')"
export ALLOWED_HOSTS=127.0.0.1 SECURE_SSL_REDIRECT=False
export DATABASE_URL="sqlite:////tmp/prod_rehearsal.sqlite3"
./build.sh
gunicorn sms_project.wsgi:application --bind 127.0.0.1:8877
```

## Main features

- Login / logout / profile
- Password reset by email (`/accounts/password_reset/`)
- Students, courses, enrolments, grades, attendance
- Role-scoped dashboard + JSON API `GET /api/dashboard/`
- CSV export for students and grades
- Paginated lists (20 rows per page) with search and filters

## Access control

One rule covers the whole system: **an administrator sees and changes
everything, a teacher only sees what belongs to their own courses.**

| Capability | Administrator | Teacher |
|------------|---------------|---------|
| Create / edit / delete students and courses | yes | no |
| Create / edit / delete enrolments | yes | no |
| Assign, edit and delete grades; mark attendance | yes | own courses only |
| Browse students, courses, enrolments, grades, attendance | all records | own courses only (read-only where editing is not allowed) |
| CSV export | all records | own courses only |

Teachers requesting a student or course outside their own courses get `404`,
and the list pages and CSV exports apply the same scope. Course capacity
(`max_students`) is enforced when an enrolment is created or re-activated.
Logout is `POST`-only so that link prefetching cannot terminate a session.
Every grade stores the account that last saved it (`Grade.assigned_by`), shown
in the grade list and the CSV export.

## Project layout

- `core/` — models, views, forms, tests
- `sms_project/` — settings, WSGI
- `templates/` — HTML
- `static/css`, `static/js` — own styles and scripts
- `static/vendor/` — vendored Bootstrap, Chart.js, Turbo, icons, fonts
- `locale/pl/` — Polish message catalogue
- `core/fixtures/demo_data.json` — demonstration data set loaded by `seed_demo`
- `render.yaml`, `build.sh` — deployment as code
- `docs/` — diploma documentation DOCX
- `scripts/` — documentation generator, font vendoring, translation helper

## Documentation

English diploma documentation (BloomTime-style structure):

`docs/SMS_Diploma_Documentation_Shpak_Maksym.docx`
