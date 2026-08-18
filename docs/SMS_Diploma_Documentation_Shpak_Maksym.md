School of Computer Science & Technologies
Field of study: Computer Science

Maksym Shpak

Design and Implementation of a Web-Based Student Management System for Educational Institutions

Documentation for the diploma project
prepared under the direction of
[Supervisor / Promotor]


Warsaw, 2026 r.


# 1. Basic information

Project name
Design and Implementation of a Web-Based Student Management System for Educational Institutions — Student Management System (SMS)
Purpose of the project
The project addresses a recurring problem in small and medium educational units: academic records for students, courses, grades and attendance are still often kept in spreadsheets or fragmented paper files. This leads to duplicated data, weak access control, and slow reporting for teachers and administrators. SMS centralises these processes in a single web application with role-based access (Administrator, Teacher, Student), structured CRUD workflows, dashboard analytics, CSV export, and password-reset via email. The system is implemented as a complete engineering deliverable — not only a conceptual design.
Brief description of the project
Student Management System is a full-stack Django web application that stores and manages academic data related to students, courses, enrolments, grades and attendance. Administrators maintain the institutional catalogue of students and courses; teachers manage grades and attendance for their own courses; students view personal academic information. The presentation layer uses Django templates with custom CSS and JavaScript; the application layer implements business rules and RBAC; the data layer uses a relational schema (SQLite locally, PostgreSQL in production via DATABASE_URL). The application is production-ready for deployment on platforms such as Render (Gunicorn + WhiteNoise + optional managed Postgres).
Competitor analysis
Microsoft Excel / Google Sheets: easy to start, but no relational integrity, no role-based permissions, and high risk of accidental edits. Moodle / Canvas: powerful LMS platforms with many modules, but heavy to deploy and operate for a small faculty office that only needs student-course-grade-attendance administration. Commercial university ERP suites: broad feature sets and high cost, often oversized for training centres or single departments. SMS differentiator: a lightweight, open academic engineering project focused on core administrative workflows, transparent Django architecture suitable for defence and further extension, zero proprietary licence fees, and explicit teacher-centred dashboards with JSON analytics API.
List of technologies used
Backend:
Python 3.10+, Django 6, Django Auth (session-based), Gunicorn, WhiteNoise, dj-database-url, PostgreSQL (production) / SQLite (development), SMTP email for password reset
Frontend:
Django Templates, HTML5, CSS custom properties, vanilla JavaScript, Chart-ready dashboard JSON endpoint (/api/dashboard/)
Infrastructure:
Render-ready build (build.sh: migrate + collectstatic), environment-based configuration (.env), HTTPS-oriented security settings when DEBUG=False, optional Mailtrap / Gmail SMTP for transactional mail
Description of the technology stack and justification of selected technologies
The stack follows a classic three-tier architecture: Browser (HTML/CSS/JS) → Django views & forms (business logic, authentication, RBAC) → Relational database. Django was selected because it provides batteries-included authentication, CSRF protection, ORM migrations, and an admin site — essential for an academic records system delivered within an engineering diploma timeframe. Session authentication fits server-rendered pages better than JWT (no separate SPA). PostgreSQL is preferred in production for ACID transactions and concurrent multi-user access; SQLite keeps local development simple. WhiteNoise serves compressed static assets behind Gunicorn, which matches typical PaaS deployments without a separate Nginx container. SMTP-based password reset uses Django’s built-in auth views, avoiding custom token plumbing while remaining compatible with Mailtrap sandbox or real providers.

# 2. Key issues related to the implementation of the project


## 2.1 Role-Based Access Control (RBAC)

The custom User model extends AbstractUser with a role field (admin / teacher / student). View decorators enforce permissions: administrators manage all records; teachers see only students and grades related to their courses; students are blocked from institutional lists and redirected to their personal dashboard. This prevents privilege escalation while keeping URLs simple.
Code snippet (decorator, simplified):
def role_required(allowed_roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.role not in allowed_roles:
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

## 2.2 Relational Academic Schema

The schema comprises six core models: User, Student, Course, Enrollment, Grade, Attendance. Enrolment links students and courses (many-to-many with status). Grade is one-to-one with Enrolment (scale 2.0–5.0 with letter mapping). Attendance is unique per (enrolment, date) to avoid duplicate daily marks. Foreign keys and unique constraints protect referential integrity at the database level.

## 2.3 Dashboard Analytics and REST JSON Endpoint

The HTML dashboard aggregates KPIs (students, courses, enrolments, average grade) and chart series (grade distribution, enrolments per course). Endpoint GET /api/dashboard/ returns the same metrics as JSON, scoped by role, so charts or future SPA clients can refresh data without reloading the page.
Example response fields:
{'role': 'teacher', 'total_students': …, 'grade_distribution': {'A': …}, 'course_labels': [...], 'course_data': [...]}

## 2.4 Password Reset via Email

Password recovery uses Django’s auth URLs under /accounts/ with custom email templates. In development, EMAIL_BACKEND=console prints messages to the terminal. In production, SMTP settings (Mailtrap, Gmail, SendGrid, etc.) send a signed reset link. Unknown emails still redirect (no user enumeration), matching Django defaults.

## 2.5 Production Configuration and Security Hardening

Configuration is driven by environment variables: SECRET_KEY, DEBUG, ALLOWED_HOSTS, DATABASE_URL, EMAIL_*. When DEBUG=False the application enforces HTTPS redirects, secure cookies, HSTS, and refuses insecure default SECRET_KEY values. WhiteNoise serves hashed/compressed static files. This allows the same codebase to run locally on SQLite and on a hosted PostgreSQL instance without code changes.

# 3. Screenshots, visualizations, etc.

This section describes representative screens of the Student Management System. Replace the figure placeholders with actual captures from the running application before the final submission / defence.
Fig. 1 — Login page: username/password form with link to password reset.
Fig. 2 — Administrator / Teacher dashboard: KPI cards, grade distribution chart, recent enrolments.
Fig. 3 — Student list with search and filters (program, active status).
Fig. 4 — Course detail: enrolled students, capacity, teacher assignment.
Fig. 5 — Grade entry form with validation (2.0–5.0) and comments.
Fig. 6 — Attendance register with present / absent / late statuses.
Fig. 7 — Password reset email (console or SMTP) containing the secure confirmation link.
Fig. 8 — JSON response from GET /api/dashboard/ (browser or HTTP client).

# 4. Conclusions and development prospects

The primary goal — to design and implement a functional web-based Student Management System for educational administration — was achieved. The application covers authentication with RBAC, student and course administration, enrolments, grading, attendance, analytics dashboard, CSV export, password reset mail, and production-oriented configuration.
All core objectives were met:
- Role-based access for Administrator, Teacher and Student
- Relational schema with integrity constraints for academic entities
- CRUD workflows with form validation and flash messages
- Dashboard KPIs and role-scoped REST endpoint /api/dashboard/
- Email-based password reset (console locally, SMTP in production)
- Automated test suite covering models, auth, API, CRUD and mail
- Deployment-ready settings (Gunicorn, WhiteNoise, Postgres via DATABASE_URL)
The project demonstrates that a production-capable academic administration system can be delivered by a single developer within an engineering diploma timeframe, using a coherent Django monolith suitable for oral examination and further maintenance.
Future development priorities:
- Multi-language UI (EN/PL) using Django i18n
- PDF report generation for transcripts and attendance sheets
- Calendar view for classes and attendance sessions
- REST API tokens for mobile clients
- LDAP / Google SSO for institutional login
- Soft-delete audit log for grade changes

# 5. Bibliography / Resources

Official Documentation
[1] Django Software Foundation — Django Documentation — https://docs.djangoproject.com
[2] Django Software Foundation — Django Authentication System — https://docs.djangoproject.com/en/stable/topics/auth/
[3] Python Software Foundation — Python 3 Documentation — https://docs.python.org/3/
[4] The PostgreSQL Global Development Group — PostgreSQL Documentation — https://www.postgresql.org/docs/
[5] SQLite Consortium — SQLite Documentation — https://www.sqlite.org/docs.html
[6] Whitenoise — WhiteNoise Documentation — https://whitenoise.readthedocs.io
[7] Gunicorn — Gunicorn Documentation — https://docs.gunicorn.org
[8] Render — Deploy Django — https://render.com/docs/deploy-django
[9] MDN Web Docs — HTML / CSS / HTTP — https://developer.mozilla.org
[10] OWASP Foundation — OWASP Top Ten — https://owasp.org/www-project-top-ten/
[11] Jazzband — dj-database-url — https://github.com/jazzband/dj-database-url
[12] Django Software Foundation — Sending email — https://docs.djangoproject.com/en/stable/topics/email/
[13] Mailtrap — Email Testing for Developers — https://mailtrap.io
[14] Bootstrap Icons — https://icons.getbootstrap.com
[15] Uniwersytet VIZJA / AEH — study programme materials for Computer Science (engineering profile)