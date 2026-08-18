#!/usr/bin/env python3
"""Generate diploma documentation DOCX for Student Management System."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Pt, Cm


OUT_PATHS = [
    Path('/Users/maksym/DiplomCode/docs/SMS_Diploma_Documentation_Shpak_Maksym.docx'),
    Path('/Users/maksym/Diploma/Documentation for the diploma project - Student Management System - Shpak Maksym.docx'),
]


def set_normal_style(doc: Document) -> None:
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    pf = style.paragraph_format
    pf.space_after = Pt(8)
    pf.line_spacing = 1.15


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.name = 'Times New Roman'


def add_para(doc: Document, text: str, bold: bool = False) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.name = 'Times New Roman'
    run.font.size = Pt(12)


def _set_run_font(run, *, bold: bool = False, size: Pt = Pt(12)) -> None:
    run.bold = bold
    run.font.name = 'Times New Roman'
    run.font.size = size
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')


def _set_cell_width(cell, width_dxa: int) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcW = tcPr.find(qn('w:tcW'))
    if tcW is None:
        from docx.oxml import OxmlElement
        tcW = OxmlElement('w:tcW')
        tcPr.append(tcW)
    tcW.set(qn('w:w'), str(width_dxa))
    tcW.set(qn('w:type'), 'dxa')


def add_basic_info_table(doc: Document, rows: list[tuple[str, str]]) -> None:
    """2-column table like BloomTime sample (label | content)."""
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = 'Table Grid'
    table.autofit = False

    left_w, right_w = 2800, 6526  # dxa — same proportions as BloomTime

    for i, (label, value) in enumerate(rows):
        left, right = table.rows[i].cells
        _set_cell_width(left, left_w)
        _set_cell_width(right, right_w)
        left.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
        right.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP

        left.text = ''
        lp = left.paragraphs[0]
        lr = lp.add_run(label)
        _set_run_font(lr, bold=True)

        right.text = ''
        first = True
        for line in value.split('\n'):
            rp = right.paragraphs[0] if first else right.add_paragraph()
            first = False
            # Bold Backend:/Frontend:/Infrastructure: labels inside cell
            if line.rstrip().endswith(':') and line.rstrip() in {
                'Backend:', 'Frontend:', 'Infrastructure:'
            }:
                rr = rp.add_run(line)
                _set_run_font(rr, bold=True)
            else:
                rr = rp.add_run(line)
                _set_run_font(rr, bold=False)

    doc.add_paragraph()


def build() -> Document:
    doc = Document()
    set_normal_style(doc)

    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(1.5)

    # Title page
    for line in [
        'School of Computer Science & Technologies',
        'Field of study: Computer Science',
        '',
        'Maksym Shpak',
        '',
        'Design and Implementation of a Web-Based Student Management System '
        'for Educational Institutions',
        '',
        'Documentation for the diploma project',
        'prepared under the direction of',
        '[Supervisor / Promotor]',
        '',
        '',
        'Warsaw, 2026 r.',
    ]:
        p = doc.add_paragraph(line)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.name = 'Times New Roman'
            run.font.size = Pt(14 if 'Design and Implementation' in line else 12)
            if 'Design and Implementation' in line or line == 'Maksym Shpak':
                run.bold = True

    doc.add_page_break()

    # 1. Basic information — table (same layout as BloomTime sample)
    add_heading(doc, '1. Basic information', 1)

    tech_list = (
        'Backend:\n'
        'Python 3.10+, Django 6, Django Auth (session-based), Gunicorn, WhiteNoise, '
        'dj-database-url, PostgreSQL (production) / SQLite (development), SMTP email '
        'for password reset\n'
        'Frontend:\n'
        'Django Templates, HTML5, CSS custom properties, vanilla JavaScript, '
        'dashboard JSON endpoint (/api/dashboard/)\n'
        'Infrastructure:\n'
        'Render-ready build (build.sh: migrate + collectstatic), environment-based '
        'configuration (.env), HTTPS-oriented security settings when DEBUG=False, '
        'optional Mailtrap / Gmail SMTP for transactional mail'
    )

    add_basic_info_table(doc, [
        (
            'Project name',
            'Design and Implementation of a Web-Based Student Management System '
            'for Educational Institutions — Student Management System (SMS)',
        ),
        (
            'Purpose of the project',
            'The project addresses a recurring problem in small and medium educational '
            'units: academic records for students, courses, grades and attendance are still '
            'often kept in spreadsheets or fragmented paper files. This leads to duplicated '
            'data, weak access control, and slow reporting for teachers and administrators. '
            'SMS centralises these processes in a single web application with role-based '
            'access (Administrator, Teacher, Student), structured CRUD workflows, dashboard '
            'analytics, CSV export, and password-reset via email. The system is implemented '
            'as a complete engineering deliverable — not only a conceptual design.',
        ),
        (
            'Brief description of the project',
            'Student Management System is a full-stack Django web application that stores '
            'and manages academic data related to students, courses, enrolments, grades and '
            'attendance. Administrators maintain the institutional catalogue of students and '
            'courses; teachers manage grades and attendance for their own courses; students '
            'view personal academic information. The presentation layer uses Django templates '
            'with custom CSS and JavaScript; the application layer implements business rules '
            'and RBAC; the data layer uses a relational schema (SQLite locally, PostgreSQL in '
            'production via DATABASE_URL). The application is production-ready for deployment '
            'on platforms such as Render (Gunicorn + WhiteNoise + optional managed Postgres).',
        ),
        (
            'Competitor analysis',
            'Microsoft Excel / Google Sheets: easy to start, but no relational integrity, '
            'no role-based permissions, and high risk of accidental edits. '
            'Moodle / Canvas: powerful LMS platforms with many modules, but heavy to deploy '
            'and operate for a small faculty office that only needs student-course-grade-'
            'attendance administration. '
            'Commercial university ERP suites: broad feature sets and high cost, often '
            'oversized for training centres or single departments. '
            'SMS differentiator: a lightweight, open academic engineering project focused on '
            'core administrative workflows, transparent Django architecture suitable for '
            'defence and further extension, zero proprietary licence fees, and explicit '
            'teacher-centred dashboards with JSON analytics API.',
        ),
        (
            'List of technologies used',
            tech_list,
        ),
        (
            'Description of the technology stack and justification of selected technologies',
            'The stack follows a classic three-tier architecture: Browser (HTML/CSS/JS) → '
            'Django views & forms (business logic, authentication, RBAC) → Relational database. '
            'Django was selected because it provides batteries-included authentication, CSRF '
            'protection, ORM migrations, and an admin site — essential for an academic records '
            'system delivered within an engineering diploma timeframe. Session authentication '
            'fits server-rendered pages better than JWT (no separate SPA). PostgreSQL is preferred '
            'in production for ACID transactions and concurrent multi-user access; SQLite keeps '
            'local development simple. WhiteNoise serves compressed static assets behind Gunicorn, '
            'which matches typical PaaS deployments without a separate Nginx container. SMTP-based '
            'password reset uses Django’s built-in auth views, avoiding custom token plumbing while '
            'remaining compatible with Mailtrap sandbox or real providers.',
        ),
    ])

    # 2. Key issues
    add_heading(doc, '2. Key issues related to the implementation of the project', 1)

    add_heading(doc, '2.1 Role-Based Access Control (RBAC)', 2)
    add_para(
        doc,
        'The custom User model extends AbstractUser with a role field '
        '(admin / teacher / student). View decorators enforce permissions: administrators '
        'manage all records; teachers see only students and grades related to their courses; '
        'students are blocked from institutional lists and redirected to their personal '
        'dashboard. This prevents privilege escalation while keeping URLs simple.',
    )
    add_para(doc, 'Code snippet (decorator, simplified):', bold=True)
    add_para(
        doc,
        "def role_required(allowed_roles):\n"
        "    def decorator(view_func):\n"
        "        def wrapper(request, *args, **kwargs):\n"
        "            if request.user.role not in allowed_roles:\n"
        "                return redirect('dashboard')\n"
        "            return view_func(request, *args, **kwargs)\n"
        "        return wrapper\n"
        "    return decorator",
    )

    add_heading(doc, '2.2 Relational Academic Schema', 2)
    add_para(
        doc,
        'The schema comprises six core models: User, Student, Course, Enrollment, Grade, '
        'Attendance. Enrolment links students and courses (many-to-many with status). Grade '
        'is one-to-one with Enrolment (scale 2.0–5.0 with letter mapping). Attendance is unique '
        'per (enrolment, date) to avoid duplicate daily marks. Foreign keys and unique '
        'constraints protect referential integrity at the database level.',
    )

    add_heading(doc, '2.3 Dashboard Analytics and REST JSON Endpoint', 2)
    add_para(
        doc,
        'The HTML dashboard aggregates KPIs (students, courses, enrolments, average grade) '
        'and chart series (grade distribution, enrolments per course). Endpoint '
        'GET /api/dashboard/ returns the same metrics as JSON, scoped by role, so charts '
        'or future SPA clients can refresh data without reloading the page.',
    )
    add_para(doc, 'Example response fields:', bold=True)
    add_para(
        doc,
        "{'role': 'teacher', 'total_students': …, 'grade_distribution': {'A': …}, "
        "'course_labels': [...], 'course_data': [...]}",
    )

    add_heading(doc, '2.4 Password Reset via Email', 2)
    add_para(
        doc,
        'Password recovery uses Django’s auth URLs under /accounts/ with custom email '
        'templates. In development, EMAIL_BACKEND=console prints messages to the terminal. '
        'In production, SMTP settings (Mailtrap, Gmail, SendGrid, etc.) send a signed reset '
        'link. Unknown emails still redirect (no user enumeration), matching Django defaults.',
    )

    add_heading(doc, '2.5 Production Configuration and Security Hardening', 2)
    add_para(
        doc,
        'Configuration is driven by environment variables: SECRET_KEY, DEBUG, ALLOWED_HOSTS, '
        'DATABASE_URL, EMAIL_*. When DEBUG=False the application enforces HTTPS redirects, '
        'secure cookies, HSTS, and refuses insecure default SECRET_KEY values. WhiteNoise '
        'serves hashed/compressed static files. This allows the same codebase to run locally '
        'on SQLite and on a hosted PostgreSQL instance without code changes.',
    )

    # 3. Screenshots
    add_heading(doc, '3. Screenshots, visualizations, etc.', 1)
    add_para(
        doc,
        'This section describes representative screens of the Student Management System. '
        'Replace the figure placeholders with actual captures from the running application '
        'before the final submission / defence.',
    )
    add_para(
        doc,
        'Fig. 1 — Login page: username/password form with link to password reset.',
    )
    add_para(
        doc,
        'Fig. 2 — Administrator / Teacher dashboard: KPI cards, grade distribution chart, '
        'recent enrolments.',
    )
    add_para(
        doc,
        'Fig. 3 — Student list with search and filters (program, active status).',
    )
    add_para(
        doc,
        'Fig. 4 — Course detail: enrolled students, capacity, teacher assignment.',
    )
    add_para(
        doc,
        'Fig. 5 — Grade entry form with validation (2.0–5.0) and comments.',
    )
    add_para(
        doc,
        'Fig. 6 — Attendance register with present / absent / late statuses.',
    )
    add_para(
        doc,
        'Fig. 7 — Password reset email (console or SMTP) containing the secure confirmation link.',
    )
    add_para(
        doc,
        'Fig. 8 — JSON response from GET /api/dashboard/ (browser or HTTP client).',
    )

    # 4. Conclusions
    add_heading(doc, '4. Conclusions and development prospects', 1)
    add_para(
        doc,
        'The primary goal — to design and implement a functional web-based Student '
        'Management System for educational administration — was achieved. The application '
        'covers authentication with RBAC, student and course administration, enrolments, '
        'grading, attendance, analytics dashboard, CSV export, password reset mail, and '
        'production-oriented configuration.',
    )
    add_para(doc, 'All core objectives were met:', bold=True)
    for item in [
        'Role-based access for Administrator, Teacher and Student',
        'Relational schema with integrity constraints for academic entities',
        'CRUD workflows with form validation and flash messages',
        'Dashboard KPIs and role-scoped REST endpoint /api/dashboard/',
        'Email-based password reset (console locally, SMTP in production)',
        'Automated test suite covering models, auth, API, CRUD and mail',
        'Deployment-ready settings (Gunicorn, WhiteNoise, Postgres via DATABASE_URL)',
    ]:
        doc.add_paragraph(item, style='List Bullet')

    add_para(
        doc,
        'The project demonstrates that a production-capable academic administration system '
        'can be delivered by a single developer within an engineering diploma timeframe, '
        'using a coherent Django monolith suitable for oral examination and further maintenance.',
    )

    add_para(doc, 'Future development priorities:', bold=True)
    for item in [
        'Multi-language UI (EN/PL) using Django i18n',
        'PDF report generation for transcripts and attendance sheets',
        'Calendar view for classes and attendance sessions',
        'REST API tokens for mobile clients',
        'LDAP / Google SSO for institutional login',
        'Soft-delete audit log for grade changes',
    ]:
        doc.add_paragraph(item, style='List Bullet')

    # 5. Bibliography
    add_heading(doc, '5. Bibliography / Resources', 1)

    add_para(doc, 'Official Documentation', bold=True)
    refs = [
        '[1] Django Software Foundation — Django Documentation — https://docs.djangoproject.com',
        '[2] Django Software Foundation — Django Authentication System — https://docs.djangoproject.com/en/stable/topics/auth/',
        '[3] Python Software Foundation — Python 3 Documentation — https://docs.python.org/3/',
        '[4] The PostgreSQL Global Development Group — PostgreSQL Documentation — https://www.postgresql.org/docs/',
        '[5] SQLite Consortium — SQLite Documentation — https://www.sqlite.org/docs.html',
        '[6] Whitenoise — WhiteNoise Documentation — https://whitenoise.readthedocs.io',
        '[7] Gunicorn — Gunicorn Documentation — https://docs.gunicorn.org',
        '[8] Render — Deploy Django — https://render.com/docs/deploy-django',
        '[9] MDN Web Docs — HTML / CSS / HTTP — https://developer.mozilla.org',
        '[10] OWASP Foundation — OWASP Top Ten — https://owasp.org/www-project-top-ten/',
        '[11] Jazzband — dj-database-url — https://github.com/jazzband/dj-database-url',
        '[12] Django Software Foundation — Sending email — https://docs.djangoproject.com/en/stable/topics/email/',
        '[13] Mailtrap — Email Testing for Developers — https://mailtrap.io',
        '[14] Bootstrap Icons — https://icons.getbootstrap.com',
        '[15] Uniwersytet VIZJA / AEH — study programme materials for Computer Science (engineering profile)',
    ]
    for r in refs:
        add_para(doc, r)

    return doc


def main() -> None:
    doc = build()
    for path in OUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(path)
        print('Wrote', path)


if __name__ == '__main__':
    main()
