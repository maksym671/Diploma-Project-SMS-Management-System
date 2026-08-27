import json

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Avg, Q, Sum, F, FloatField
from django.db.models.functions import Cast
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
import csv

from .models import User, Student, Course, Enrollment, Grade, Attendance, weighted_average_qs
from .forms import (
    LoginForm,
    StudentForm,
    CourseForm,
    EnrollmentForm,
    GradeForm,
    AttendanceForm,
    TeacherForm,
    ProfileForm,
)
from .decorators import admin_required, teacher_or_admin_required

PAGE_SIZE = 20


def paginate(request, queryset, per_page=PAGE_SIZE):
    """Return a page of `queryset` based on the ?page= query parameter."""
    return Paginator(queryset, per_page).get_page(request.GET.get('page'))


def visible_students(user):
    """Students the user may access: teachers only see their own course rosters."""
    if user.is_teacher():
        return Student.objects.filter(enrollments__course__teacher=user).distinct()
    return Student.objects.all()


def visible_courses(user):
    """Courses the user may access: teachers only see courses they teach."""
    if user.is_teacher():
        return Course.objects.filter(teacher=user)
    return Course.objects.all()


# ─── Authentication ─────────────────────────────────────────────────

def login_view(request):
    """Handle user authentication."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(
                request,
                _('Welcome back, %(name)s!') % {'name': user.get_full_name() or user.username},
            )
            return redirect('dashboard')
        else:
            messages.error(request, _('Invalid username or password.'))
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})


@require_POST
def logout_view(request):
    """Log the user out. POST only, so link prefetching cannot end a session."""
    logout(request)
    messages.info(request, _('You have been logged out.'))
    return redirect('login')


def _grade_distribution(grade_qs):
    """Letter-band counts in one query instead of five separate COUNTs."""
    row = grade_qs.aggregate(
        A=Count('id', filter=Q(grade_value__gte=4.5)),
        B=Count('id', filter=Q(grade_value__gte=4.0, grade_value__lt=4.5)),
        C=Count('id', filter=Q(grade_value__gte=3.5, grade_value__lt=4.0)),
        D=Count('id', filter=Q(grade_value__gte=3.0, grade_value__lt=3.5)),
        F=Count('id', filter=Q(grade_value__lt=3.0)),
    )
    return {band: row[band] for band in ('A', 'B', 'C', 'D', 'F')}


def dashboard_metrics(user):
    """Role-scoped KPI payload shared by the HTML dashboard and /api/dashboard/."""
    if user.is_teacher():
        grade_qs = Grade.objects.filter(enrollment__course__teacher=user)
        course_qs = Course.objects.filter(teacher=user, is_active=True)
        student_qs = Student.objects.filter(
            enrollments__course__teacher=user, is_active=True,
        ).distinct()
        enrollment_qs = Enrollment.objects.filter(
            course__teacher=user, status='active',
        )
        recent_students = (
            Student.objects.filter(enrollments__course__teacher=user)
            .distinct().order_by('-created_at')[:5]
        )
        recent_enrollments = (
            Enrollment.objects.filter(course__teacher=user)
            .select_related('student', 'course')
            .order_by('-created_at')[:5]
        )
        # distinct=True: joining through enrollments repeats a student once per
        # course they take with this teacher, which made the chart total
        # overshoot the "Total Students" KPI on the same screen.
        programs = Student.objects.filter(
            enrollments__course__teacher=user, is_active=True,
        ).values('study_program').annotate(
            count=Count('id', distinct=True),
        ).order_by('-count')[:6]
    else:
        grade_qs = Grade.objects.all()
        course_qs = Course.objects.filter(is_active=True)
        student_qs = Student.objects.filter(is_active=True)
        enrollment_qs = Enrollment.objects.filter(status='active')
        recent_students = Student.objects.order_by('-created_at')[:5]
        recent_enrollments = (
            Enrollment.objects.select_related('student', 'course')
            .order_by('-created_at')[:5]
        )
        programs = student_qs.values('study_program').annotate(
            count=Count('id'),
        ).order_by('-count')[:6]

    course_stats = list(
        course_qs.annotate(
            enrollment_count=Count(
                'enrollments', filter=Q(enrollments__status='active'),
            )
        ).order_by('-enrollment_count')[:8]
    )

    return {
        'role': user.role,
        'total_students': student_qs.count(),
        'total_courses': course_qs.count(),
        'total_enrollments': enrollment_qs.count(),
        'total_grades': grade_qs.count(),
        'avg_grade': weighted_average_qs(grade_qs) or 0,
        'grade_distribution': _grade_distribution(grade_qs),
        'course_labels': [c.course_code for c in course_stats],
        'course_data': [c.enrollment_count for c in course_stats],
        'program_labels': [str(_(p['study_program'])) for p in programs],
        'program_data': [p['count'] for p in programs],
        'recent_students': recent_students,
        'recent_enrollments': recent_enrollments,
    }


# ─── Dashboard ───────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """Main dashboard with statistics and analytics."""
    metrics = dashboard_metrics(request.user)
    context = {
        **metrics,
        'grade_distribution': json.dumps(metrics['grade_distribution']),
        'course_labels': json.dumps(metrics['course_labels']),
        'course_data': json.dumps(metrics['course_data']),
        'program_labels': json.dumps(metrics['program_labels']),
        'program_data': json.dumps(metrics['program_data']),
    }
    return render(request, 'dashboard/index.html', context)


# ─── API endpoints for charts ────────────────────────────────────────

@login_required
def api_dashboard_data(request):
    """JSON REST endpoint for dashboard chart / KPI data (role-scoped)."""
    metrics = dashboard_metrics(request.user)
    avg = metrics['avg_grade']
    return JsonResponse({
        'role': metrics['role'],
        'total_students': metrics['total_students'],
        'total_courses': metrics['total_courses'],
        'total_enrollments': metrics['total_enrollments'],
        'total_grades': metrics['total_grades'],
        'avg_grade': float(round(avg, 2)) if avg else 0,
        'grade_distribution': metrics['grade_distribution'],
        'course_labels': metrics['course_labels'],
        'course_data': metrics['course_data'],
    })


# ─── Students ────────────────────────────────────────────────────────

@login_required
def student_list(request):
    """List all students with search and filtering."""
    query = request.GET.get('q', '')
    program = request.GET.get('program', '')
    status = request.GET.get('status', '')

    students = visible_students(request.user)

    # Optimize queries by pre-calculating enrollment counts and average grades in the DB.
    # annotate() adds a GROUP BY, which drops the implicit Meta ordering that
    # pagination needs, so the sort order is restated explicitly.
    students = students.annotate(
        annotated_enrollment_count=Count('enrollments', filter=Q(enrollments__status='active'), distinct=True),
        # Weighted mean over every component, matching Student.average_grade:
        # sum(value * weight) / sum(weight).
        #
        # Both sides are cast to float on purpose. SQLite gives a "decimal"
        # cast NUMERIC affinity, which turns the operands into integers and
        # makes the division integer division — 350/100 came back as 3
        # instead of 3.5. A real cast divides correctly on SQLite and
        # Postgres alike.
        annotated_average_grade=Cast(
            Sum(F('enrollments__grades__grade_value') * F('enrollments__grades__weight')),
            FloatField(),
        ) / Cast(Sum('enrollments__grades__weight'), FloatField()),
    ).order_by('last_name', 'first_name')

    if query:
        students = students.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(student_number__icontains=query) |
            Q(email__icontains=query)
        )
    if program:
        students = students.filter(study_program=program)
    if status == 'active':
        students = students.filter(is_active=True)
    elif status == 'inactive':
        students = students.filter(is_active=False)

    programs = visible_students(request.user).values_list(
        'study_program', flat=True
    ).distinct().order_by('study_program')

    page_obj = paginate(request, students)

    context = {
        'students': page_obj,
        'page_obj': page_obj,
        'query': query,
        'programs': programs,
        'selected_program': program,
        'selected_status': status,
    }
    return render(request, 'students/list.html', context)


@login_required
def student_detail(request, pk):
    """View student details with enrollments and grades."""
    student = get_object_or_404(visible_students(request.user), pk=pk)

    enrollments = (
        Enrollment.objects.filter(student=student)
        .select_related('course')
        .prefetch_related('grades')
    )
    # A teacher only sees the part of the record that belongs to their own courses.
    if request.user.is_teacher():
        enrollments = enrollments.filter(course__teacher=request.user)

    # The summary card has to agree with the table below it. The model
    # properties aggregate over every course the student takes, which would
    # leak another teacher's roster and grades, so scope them to `enrollments`.
    course_count = enrollments.count()
    average_grade = weighted_average_qs(
        Grade.objects.filter(enrollment__in=enrollments)
    )

    context = {
        'student': student,
        'enrollments': enrollments,
        'course_count': course_count,
        'average_grade': round(average_grade, 2) if average_grade is not None else None,
    }
    return render(request, 'students/detail.html', context)


@login_required
@admin_required
def student_create(request):
    """Create a new student record."""
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(
                request,
                _('Student "%(name)s" has been created successfully.') % {'name': student.full_name},
            )
            return redirect('student_detail', pk=student.pk)
    else:
        form = StudentForm()

    return render(request, 'students/form.html', {'form': form, 'title': _('Add New Student')})


@login_required
@admin_required
def student_update(request, pk):
    """Edit an existing student record."""
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                _('Student "%(name)s" has been updated.') % {'name': student.full_name},
            )
            return redirect('student_detail', pk=pk)
    else:
        form = StudentForm(instance=student)

    return render(request, 'students/form.html', {'form': form, 'title': _('Edit Student'), 'student': student})


@login_required
@admin_required
def student_delete(request, pk):
    """Delete a student record."""
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        name = student.full_name
        student.delete()
        messages.success(request, _('Student "%(name)s" has been deleted.') % {'name': name})
        return redirect('student_list')

    return render(request, 'students/confirm_delete.html', {'student': student})


# ─── Teachers ────────────────────────────────────────────────────────

def _teacher_display_name(teacher):
    return teacher.get_full_name() or teacher.username


@login_required
@admin_required
def teacher_list(request):
    """Staff accounts issued to lecturers — created here, not by self-registration."""
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')

    teachers = User.objects.filter(role='teacher').annotate(
        annotated_course_count=Count('courses', filter=Q(courses__is_active=True)),
    ).order_by('last_name', 'first_name', 'username')

    if query:
        teachers = teachers.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(department__icontains=query)
        )
    if status == 'active':
        teachers = teachers.filter(is_active=True)
    elif status == 'inactive':
        teachers = teachers.filter(is_active=False)

    page_obj = paginate(request, teachers)
    return render(request, 'teachers/list.html', {
        'teachers': page_obj,
        'page_obj': page_obj,
        'query': query,
        'selected_status': status,
    })


@login_required
@admin_required
def teacher_create(request):
    """Issue a new teacher account and an initial password."""
    if request.method == 'POST':
        form = TeacherForm(request.POST)
        if form.is_valid():
            teacher = form.save()
            messages.success(
                request,
                _('Teacher "%(name)s" has been created.') % {
                    'name': _teacher_display_name(teacher),
                },
            )
            return redirect('teacher_list')
    else:
        form = TeacherForm()

    return render(request, 'teachers/form.html', {
        'form': form,
        'title': _('Add Teacher'),
    })


@login_required
@admin_required
def teacher_update(request, pk):
    """Edit a teacher profile or set a new password."""
    teacher = get_object_or_404(User, pk=pk, role='teacher')
    if request.method == 'POST':
        form = TeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                _('Teacher "%(name)s" has been updated.') % {
                    'name': _teacher_display_name(teacher),
                },
            )
            return redirect('teacher_list')
    else:
        form = TeacherForm(instance=teacher)

    return render(request, 'teachers/form.html', {
        'form': form,
        'title': _('Edit Teacher'),
        'teacher': teacher,
    })


@login_required
@admin_required
def teacher_delete(request, pk):
    """Remove a teacher. Their courses stay, unassigned."""
    teacher = get_object_or_404(User, pk=pk, role='teacher')
    if request.method == 'POST':
        name = _teacher_display_name(teacher)
        teacher.delete()
        messages.success(
            request,
            _('Teacher "%(name)s" has been deleted.') % {'name': name},
        )
        return redirect('teacher_list')

    return render(request, 'teachers/confirm_delete.html', {'teacher': teacher})


# ─── Courses ─────────────────────────────────────────────────────────

@login_required
def course_list(request):
    """List all courses with search."""
    query = request.GET.get('q', '')
    semester = request.GET.get('semester', '')

    courses = visible_courses(request.user).select_related('teacher').annotate(
        enrollment_count=Count('enrollments', filter=Q(enrollments__status='active'))
    ).order_by('course_code')

    if query:
        courses = courses.filter(
            Q(course_name__icontains=query) |
            Q(course_code__icontains=query)
        )
    if semester:
        courses = courses.filter(semester=semester)

    page_obj = paginate(request, courses)

    context = {
        'courses': page_obj,
        'page_obj': page_obj,
        'query': query,
        'selected_semester': semester,
    }
    return render(request, 'courses/list.html', context)


@login_required
def course_detail(request, pk):
    """View course details with enrolled students."""
    course = get_object_or_404(visible_courses(request.user), pk=pk)
    enrollments = (
        Enrollment.objects.filter(course=course)
        .select_related('student')
        .prefetch_related('grades')
    )

    context = {
        'course': course,
        'enrollments': enrollments,
    }
    return render(request, 'courses/detail.html', context)


@login_required
@admin_required
def course_create(request):
    """Create a new course."""
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(
                request,
                _('Course "%(name)s" has been created.') % {'name': course.course_name},
            )
            return redirect('course_detail', pk=course.pk)
    else:
        form = CourseForm()

    return render(request, 'courses/form.html', {'form': form, 'title': _('Add New Course')})


@login_required
@admin_required
def course_update(request, pk):
    """Edit an existing course."""
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                _('Course "%(name)s" has been updated.') % {'name': course.course_name},
            )
            return redirect('course_detail', pk=pk)
    else:
        form = CourseForm(instance=course)

    return render(request, 'courses/form.html', {'form': form, 'title': _('Edit Course'), 'course': course})


@login_required
@admin_required
def course_delete(request, pk):
    """Delete a course."""
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        name = course.course_name
        course.delete()
        messages.success(request, _('Course "%(name)s" has been deleted.') % {'name': name})
        return redirect('course_list')

    return render(request, 'courses/confirm_delete.html', {'course': course})


# ─── Enrollments ──────────────────────────────────────────────────────

@login_required
def enrollment_list(request):
    """List enrollments. Teachers get a read-only view of their own courses."""
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')

    enrollments = Enrollment.objects.select_related('student', 'course').prefetch_related('grades')

    if request.user.is_teacher():
        enrollments = enrollments.filter(course__teacher=request.user)

    if query:
        enrollments = enrollments.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(course__course_name__icontains=query) |
            Q(course__course_code__icontains=query)
        )
    if status:
        enrollments = enrollments.filter(status=status)

    page_obj = paginate(request, enrollments)

    context = {
        'enrollments': page_obj,
        'page_obj': page_obj,
        'query': query,
        'selected_status': status,
    }
    return render(request, 'enrollments/list.html', context)


@login_required
@admin_required
def enrollment_create(request):
    """Create a new enrollment."""
    if request.method == 'POST':
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            enrollment = form.save()
            messages.success(
                request,
                _('%(student)s enrolled in %(course)s.') % {
                    'student': enrollment.student.full_name,
                    'course': enrollment.course.course_code,
                },
            )
            return redirect('enrollment_list')
    else:
        form = EnrollmentForm()

    return render(request, 'enrollments/form.html', {'form': form, 'title': _('New Enrollment')})


@login_required
@admin_required
def enrollment_update(request, pk):
    """Update enrollment status."""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    if request.method == 'POST':
        form = EnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            form.save()
            messages.success(request, _('Enrollment updated successfully.'))
            return redirect('enrollment_list')
    else:
        form = EnrollmentForm(instance=enrollment)

    return render(request, 'enrollments/form.html', {'form': form, 'title': _('Edit Enrollment'), 'enrollment': enrollment})


@login_required
@admin_required
def enrollment_delete(request, pk):
    """Delete an enrollment."""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    if request.method == 'POST':
        enrollment.delete()
        messages.success(request, _('Enrollment has been removed.'))
        return redirect('enrollment_list')

    return render(request, 'enrollments/confirm_delete.html', {'enrollment': enrollment})


# ─── Grades ───────────────────────────────────────────────────────────

@login_required
def grade_list(request):
    """List all grades."""
    query = request.GET.get('q', '')

    grades = Grade.objects.select_related(
        'enrollment__student', 'enrollment__course', 'assigned_by'
    ).prefetch_related('enrollment__grades')

    if request.user.is_teacher():
        grades = grades.filter(enrollment__course__teacher=request.user)

    if query:
        grades = grades.filter(
            Q(enrollment__student__first_name__icontains=query) |
            Q(enrollment__student__last_name__icontains=query) |
            Q(enrollment__course__course_code__icontains=query)
        )

    page_obj = paginate(request, grades)

    context = {
        'grades': page_obj,
        'page_obj': page_obj,
        'query': query,
    }
    return render(request, 'grades/list.html', context)


@login_required
@teacher_or_admin_required
def grade_create(request):
    """Assign a new grade."""
    if request.method == 'POST':
        form = GradeForm(request.POST, user=request.user)
        if form.is_valid():
            grade = form.save(commit=False)
            grade.assigned_by = request.user
            grade.save()
            messages.success(
                request,
                _('Grade %(value)s assigned successfully.') % {'value': grade.grade_value},
            )
            return redirect('grade_list')
    else:
        form = GradeForm(user=request.user)

    return render(request, 'grades/form.html', {'form': form, 'title': _('Assign Grade')})


@login_required
@teacher_or_admin_required
def grade_update(request, pk):
    """Update an existing grade."""
    grade = get_object_or_404(Grade, pk=pk)

    # Teachers can only edit grades for their own courses
    if request.user.is_teacher() and grade.enrollment.course.teacher != request.user:
        messages.error(request, _('You can only edit grades for your own courses.'))
        return redirect('grade_list')

    if request.method == 'POST':
        form = GradeForm(request.POST, instance=grade, user=request.user)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.assigned_by = request.user
            updated.save()
            messages.success(request, _('Grade updated successfully.'))
            return redirect('grade_list')
    else:
        form = GradeForm(instance=grade, user=request.user)

    return render(request, 'grades/form.html', {'form': form, 'title': _('Edit Grade'), 'grade': grade})


@login_required
@teacher_or_admin_required
def grade_delete(request, pk):
    """Delete a grade. Teachers may only delete grades for their own courses."""
    grade = get_object_or_404(Grade, pk=pk)

    if request.user.is_teacher() and grade.enrollment.course.teacher != request.user:
        messages.error(request, _('You can only delete grades for your own courses.'))
        return redirect('grade_list')

    if request.method == 'POST':
        grade.delete()
        messages.success(request, _('Grade has been deleted.'))
        return redirect('grade_list')

    return render(request, 'grades/confirm_delete.html', {'grade': grade})


# ─── Attendance ───────────────────────────────────────────────────────

@login_required
def attendance_list(request):
    """List attendance records."""
    records = Attendance.objects.select_related('enrollment__student', 'enrollment__course')
    
    if request.user.is_teacher():
        records = records.filter(enrollment__course__teacher=request.user)

    query = request.GET.get('q', '')
    if query:
        records = records.filter(
            Q(enrollment__student__first_name__icontains=query) |
            Q(enrollment__student__last_name__icontains=query) |
            Q(enrollment__course__course_code__icontains=query)
        )

    page_obj = paginate(request, records)

    context = {
        'records': page_obj,
        'page_obj': page_obj,
        'query': query,
    }
    return render(request, 'attendance/list.html', context)


@login_required
@teacher_or_admin_required
def attendance_bulk(request):
    """Mark a whole class for one date on a single screen.

    The per-record form needs one round trip per student, which is unusable
    for a 30-person group. This view shows the roster for a chosen course and
    date, pre-selected with whatever was already recorded, and saves the lot
    in one POST.
    """
    courses = visible_courses(request.user).filter(is_active=True).order_by('course_code')

    course_id = request.POST.get('course') or request.GET.get('course')
    raw_date = request.POST.get('date') or request.GET.get('date')

    selected_date = parse_date(raw_date) if raw_date else timezone.localdate()
    if selected_date is None:
        messages.error(request, _('That date could not be read. Using today instead.'))
        selected_date = timezone.localdate()

    course = None
    if course_id:
        # 404 rather than a silent empty roster if a teacher aims at a
        # colleague's course.
        course = get_object_or_404(courses, pk=course_id)

    roster = []
    if course:
        enrollments = (
            course.enrollments.filter(status='active')
            .select_related('student')
            .order_by('student__last_name', 'student__first_name')
        )
        existing = {
            record.enrollment_id: record
            for record in Attendance.objects.filter(
                enrollment__in=enrollments, date=selected_date
            )
        }

        if request.method == 'POST':
            saved = cleared = 0
            for enrollment in enrollments:
                choice = request.POST.get(f'status_{enrollment.pk}')
                if choice in {'present', 'absent', 'late'}:
                    Attendance.objects.update_or_create(
                        enrollment=enrollment, date=selected_date,
                        defaults={'status': choice},
                    )
                    saved += 1
                elif choice == 'none' and enrollment.pk in existing:
                    # "Not marked" is an explicit state: drop any record so the
                    # screen keeps telling the truth about that date.
                    existing[enrollment.pk].delete()
                    cleared += 1

            if saved or cleared:
                messages.success(request, _(
                    'Attendance saved for %(count)s students in %(code)s on %(date)s.'
                ) % {
                    'count': saved,
                    'code': course.course_code,
                    'date': selected_date,
                })
            else:
                messages.info(request, _('Nothing to save — no students were marked.'))
            return redirect(f"{reverse('attendance_bulk')}?course={course.pk}&date={selected_date}")

        for enrollment in enrollments:
            record = existing.get(enrollment.pk)
            roster.append({
                'enrollment': enrollment,
                'student': enrollment.student,
                'status': record.status if record else '',
            })

    context = {
        'courses': courses,
        'course': course,
        'selected_date': selected_date,
        'roster': roster,
        'statuses': Attendance.STATUS_CHOICES,
    }
    return render(request, 'attendance/bulk.html', context)


@login_required
@teacher_or_admin_required
def attendance_create(request):
    """Mark attendance."""
    if request.method == 'POST':
        form = AttendanceForm(request.POST, user=request.user)
        if form.is_valid():
            att = form.save()
            messages.success(
                request,
                _('Attendance marked for %(name)s.') % {'name': att.enrollment.student.full_name},
            )
            if 'save_and_add_another' in request.POST:
                return redirect('attendance_create')
            return redirect('attendance_list')
    else:
        form = AttendanceForm(user=request.user)
    
    return render(request, 'attendance/form.html', {'form': form, 'title': _('Mark Attendance')})


@login_required
@teacher_or_admin_required
def attendance_update(request, pk):
    att = get_object_or_404(Attendance, pk=pk)
    if request.user.is_teacher() and att.enrollment.course.teacher != request.user:
        messages.error(request, _('You can only edit attendance for your own courses.'))
        return redirect('attendance_list')
        
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=att, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Attendance updated.'))
            return redirect('attendance_list')
    else:
        form = AttendanceForm(instance=att, user=request.user)
    return render(request, 'attendance/form.html', {'form': form, 'title': _('Edit Attendance'), 'att': att})


@login_required
@teacher_or_admin_required
def attendance_delete(request, pk):
    """Delete an attendance record, scoped to the teacher's own courses."""
    att = get_object_or_404(Attendance, pk=pk)

    if request.user.is_teacher() and att.enrollment.course.teacher != request.user:
        messages.error(request, _('You can only delete attendance for your own courses.'))
        return redirect('attendance_list')

    if request.method == 'POST':
        att.delete()
        messages.success(request, _('Attendance record deleted.'))
        return redirect('attendance_list')
    return render(request, 'attendance/confirm_delete.html', {'att': att})


# ─── Profile ──────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    """User profile edit."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Profile updated successfully.'))
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'profile/index.html', {'form': form})


# ─── Reports ──────────────────────────────────────────────────────────

def _csv_response(filename):
    """CSV response with a UTF-8 BOM so Excel renders accented names correctly."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    return response


@login_required
@teacher_or_admin_required
def export_students_csv(request):
    """Export students list to CSV (scoped to the user's own roster)."""
    response = _csv_response('students_report.csv')

    writer = csv.writer(response)
    writer.writerow([
        _('Student Number'), _('First Name'), _('Last Name'), _('Email'),
        _('Program'), _('Status'), _('Enrollment Date'),
    ])

    for s in visible_students(request.user):
        writer.writerow([
            s.student_number, s.first_name, s.last_name, s.email,
            _(s.study_program), _('Active') if s.is_active else _('Inactive'), s.date_enrolled
        ])
    return response


@login_required
@teacher_or_admin_required
def export_grades_csv(request):
    """Export grades list to CSV (scoped to the user's own courses)."""
    response = _csv_response('grades_report.csv')

    writer = csv.writer(response)
    writer.writerow([
        _('Student'), _('Course Code'), _('Course Name'), _('Component'),
        _('Weight %'), _('Grade'), _('Letter'), _('Course Mark'),
        _('Date Assigned'), _('Assigned By'),
    ])

    grades = Grade.objects.select_related(
        'enrollment__student', 'enrollment__course', 'assigned_by'
    ).prefetch_related('enrollment__grades')
    if request.user.is_teacher():
        grades = grades.filter(enrollment__course__teacher=request.user)

    for g in grades:
        assigned_by = g.assigned_by
        writer.writerow([
            g.enrollment.student.full_name, g.enrollment.course.course_code,
            _(g.enrollment.course.course_name), g.get_kind_display(), g.weight,
            g.grade_value, g.letter_grade, g.enrollment.final_grade,
            g.date_assigned,
            (assigned_by.get_full_name() or assigned_by.username) if assigned_by else '',
        ])
    return response
