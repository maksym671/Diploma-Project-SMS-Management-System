# Student Management System (SMS)

Дипломный инженерный проект: веб-приложение на Django для управления студентами, курсами, оценками и посещаемостью.

## Stack

- Python 3.10+ / Django 6
- SQLite (local) / PostgreSQL via `DATABASE_URL` (production)
- Gunicorn + WhiteNoise
- Session auth + RBAC (admin / teacher)
- Polish / English interface (`django.po`, `set_language`)
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

## Local development note

`runserver` answers `/static/` itself, before any middleware, and sends only a
`Last-Modified` header — no `ETag`, no `Cache-Control`. Browsers therefore keep
editing `style.css` or `main.js` and reload to no visible effect. Hard-reload
(Cmd/Ctrl + Shift + R) after changing a static file. Production is unaffected:
`collectstatic` writes hashed filenames, so a changed file gets a new URL.

## Tests

```bash
python manage.py test
```

96 tests cover models, authentication, role-based access and data isolation,
pagination, the dashboard JSON API, enrolment capacity rules, weighted grade
components, bulk attendance marking, grade authorship, Polish localisation,
the deployment seed step, and a smoke render of every page for both roles.

`.github/workflows/ci.yml` runs the same suite on every push, plus a check for
missing migrations and `manage.py check --deploy` against production settings.

### Testing the live deployment

The unit suite runs against a throwaway database, so it cannot catch a broken
domain, an expired certificate or a CSRF origin that was never added. This does:

```bash
python3 scripts/live_smoke.py https://thesms.me
```

It signs in as the seeded demo teachers and asserts 43 properties of the
running site — the TLS certificate has time left on it, HSTS and
`X-Frame-Options` are sent, `www` redirects to the apex, anonymous pages
redirect to the login screen, a wrong password is rejected, a POST without a
CSRF token gets 403, each teacher sees only their own courses, `/teachers/` is
closed to teachers, both CSV exports work, logout is POST-only, `admin` no
longer accepts
the published demo password, and the Polish locale switches. It only reads, so
it is safe to run against production.
`.github/workflows/smoke.yml` runs it every six hours and on demand.

## Translations

The interface is fully translated into Polish (312 messages, 0 untranslated).

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

Nothing in the running application needs Node. The `package.json` at the root
exists only for `scripts/capture_screenshots.mjs`, a development helper that
drives a headless browser to re-take the screenshots used by the documentation
and the defence slides:

```bash
npm install && node scripts/capture_screenshots.mjs <sessionid>
```

Live: https://thesms.me  
Backup: https://diploma-project-sms-management-system.onrender.com

## Production notes

Set environment variables (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Required when `DEBUG=False` |
| `DEBUG` | `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `DATABASE_URL` | Postgres connection string |
| `DJANGO_ADMIN_PASSWORD` | Replaces the published demo password on the `admin` account |
| `CUSTOM_DOMAIN` | Apex of the Namecheap `.me` (adds www + CSRF automatically) |
| `CSRF_TRUSTED_ORIGINS` | e.g. `https://your-app.onrender.com` |

`/healthz/` runs `SELECT 1` and returns `{"status": "ok"}`. It is what
`healthCheckPath` and the keepalive workflow poll: the login page renders
without touching the database, so pinging it kept only the web service awake
while the managed Postgres suspended itself and charged the next visitor a
multi-second wake-up. Database connections are kept for ten minutes rather
than reopened per request — through a transaction pooler as well, with
server-side cursors and prepared statements disabled as such a pooler
requires.

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

### Free-plan sleep

Render's free plan stops the service after ~15 minutes without traffic, and the
next visitor waits ~30 s for it to boot. `.github/workflows/keepalive.yml` pings
it every 10 minutes to avoid that, but GitHub's scheduler is best-effort and
disables scheduled workflows after 60 days of repository inactivity. For a
demonstration that must not stall, add an external monitor (UptimeRobot's free
plan checks every 5 minutes) or run the service on a plan that never sleeps.

Rehearse the production build locally before pushing:

```bash
export DEBUG=False SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(64))')"
export ALLOWED_HOSTS=127.0.0.1 SECURE_SSL_REDIRECT=False
export DATABASE_URL="sqlite:////tmp/prod_rehearsal.sqlite3"
./build.sh
gunicorn sms_project.wsgi:application --bind 127.0.0.1:8877 --workers 1 --threads 8
```

## Who it is for

The system is the **teaching-staff portal**. Accounts belong to lecturers and
administrators, who keep the course rosters, enter grades and record
attendance. Students are records in the system, not users — there is no
student login, by design.

## Main features

- Login / logout / profile
- Teachers (admin issues lecturer accounts and passwords)
- Students, courses, enrolments, grades, attendance
- **Grades by component** — a course mark is built from several weighted
  parts (coursework, midterm, final exam, retake) rather than a single number;
  `Enrollment.final_grade` is their weighted mean, and the components of one
  course may not exceed 100 % between them
- **Mark a whole class at once** (`/attendance/mark/`) — pick a course and a
  date, mark the group on one screen, save in a single request
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
| Assign, edit and delete grade components; mark attendance (single or whole class) | yes | own courses only |
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

Defence rehearsal (5-minute demo path and likely oral questions):

`docs/defense-prep.md`
