import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import timedelta
import csv

from .models import Student, Course, Enrollment, Grade, User, Attendance
from .forms import LoginForm, StudentForm, CourseForm, EnrollmentForm, GradeForm, AttendanceForm, ProfileForm
from .decorators import admin_required, teacher_or_admin_required


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
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """Log the user out."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ─── Dashboard ───────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """Main dashboard with statistics and analytics."""
    if request.user.is_student():
        try:
            student = request.user.student_profile
            total_courses = student.enrollments.filter(status='active').count()
            total_grades = Grade.objects.filter(enrollment__student=student).count()
            avg_grade = student.average_grade or 0
            recent_enrollments = student.enrollments.select_related('course').order_by('-created_at')[:5]
            
            context = {
                'student': student,
                'total_courses': total_courses,
                'total_grades': total_grades,
                'avg_grade': avg_grade,
                'recent_enrollments': recent_enrollments,
                'is_student_dashboard': True,
            }
            return render(request, 'dashboard/index.html', context)
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return render(request, 'dashboard/index.html', {'is_student_dashboard': True, 'error': True})

    if request.user.is_teacher():
        total_students = Student.objects.filter(enrollments__course__teacher=request.user, is_active=True).distinct().count()
        total_courses = Course.objects.filter(teacher=request.user, is_active=True).count()
        total_enrollments = Enrollment.objects.filter(course__teacher=request.user, status='active').count()
        total_grades = Grade.objects.filter(enrollment__course__teacher=request.user).count()

        recent_students = Student.objects.filter(enrollments__course__teacher=request.user).distinct().order_by('-created_at')[:5]
        recent_enrollments = Enrollment.objects.filter(course__teacher=request.user).select_related('student', 'course').order_by('-created_at')[:5]

        grade_distribution = {
            'A': Grade.objects.filter(enrollment__course__teacher=request.user, grade_value__gte=4.5).count(),
            'B': Grade.objects.filter(enrollment__course__teacher=request.user, grade_value__gte=4.0, grade_value__lt=4.5).count(),
            'C': Grade.objects.filter(enrollment__course__teacher=request.user, grade_value__gte=3.5, grade_value__lt=4.0).count(),
            'D': Grade.objects.filter(enrollment__course__teacher=request.user, grade_value__gte=3.0, grade_value__lt=3.5).count(),
            'F': Grade.objects.filter(enrollment__course__teacher=request.user, grade_value__lt=3.0).count(),
        }

        course_stats = Course.objects.filter(teacher=request.user, is_active=True).annotate(
            enrollment_count=Count('enrollments', filter=Q(enrollments__status='active'))
        ).order_by('-enrollment_count')[:8]

        avg_grade = Grade.objects.filter(enrollment__course__teacher=request.user).aggregate(avg=Avg('grade_value'))['avg']
        avg_grade = round(avg_grade, 2) if avg_grade else 0

        programs = Student.objects.filter(enrollments__course__teacher=request.user, is_active=True).values('study_program').annotate(
            count=Count('id')
        ).order_by('-count')[:6]

    else:
        total_students = Student.objects.filter(is_active=True).count()
        total_courses = Course.objects.filter(is_active=True).count()
        total_enrollments = Enrollment.objects.filter(status='active').count()
        total_grades = Grade.objects.count()

        recent_students = Student.objects.order_by('-created_at')[:5]
        recent_enrollments = Enrollment.objects.select_related('student', 'course').order_by('-created_at')[:5]

        grade_distribution = {
            'A': Grade.objects.filter(grade_value__gte=4.5).count(),
            'B': Grade.objects.filter(grade_value__gte=4.0, grade_value__lt=4.5).count(),
            'C': Grade.objects.filter(grade_value__gte=3.5, grade_value__lt=4.0).count(),
            'D': Grade.objects.filter(grade_value__gte=3.0, grade_value__lt=3.5).count(),
            'F': Grade.objects.filter(grade_value__lt=3.0).count(),
        }

        course_stats = Course.objects.filter(is_active=True).annotate(
            enrollment_count=Count('enrollments', filter=Q(enrollments__status='active'))
        ).order_by('-enrollment_count')[:8]

        avg_grade = Grade.objects.aggregate(avg=Avg('grade_value'))['avg']
        avg_grade = round(avg_grade, 2) if avg_grade else 0

        programs = Student.objects.filter(is_active=True).values('study_program').annotate(
            count=Count('id')
        ).order_by('-count')[:6]

    course_labels = [c.course_code for c in course_stats]
    course_data = [c.enrollment_count for c in course_stats]
    program_labels = [p['study_program'] for p in programs]
    program_data = [p['count'] for p in programs]

    context = {
        'total_students': total_students,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'total_grades': total_grades,
        'recent_students': recent_students,
        'recent_enrollments': recent_enrollments,
        'grade_distribution': json.dumps(grade_distribution),
        'course_labels': json.dumps(course_labels),
        'course_data': json.dumps(course_data),
        'avg_grade': avg_grade,
        'program_labels': json.dumps(program_labels),
        'program_data': json.dumps(program_data),
    }
    return render(request, 'dashboard/index.html', context)


# ─── API endpoints for charts ────────────────────────────────────────

@login_required
def api_dashboard_data(request):
    """JSON REST endpoint for dashboard chart / KPI data (role-scoped)."""
    user = request.user

    if user.is_student():
        try:
            student = user.student_profile
        except Student.DoesNotExist:
            return JsonResponse({'error': 'Student profile not found.'}, status=404)

        grades = Grade.objects.filter(enrollment__student=student)
        grade_distribution = {
            'A': grades.filter(grade_value__gte=4.5).count(),
            'B': grades.filter(grade_value__gte=4.0, grade_value__lt=4.5).count(),
            'C': grades.filter(grade_value__gte=3.5, grade_value__lt=4.0).count(),
            'D': grades.filter(grade_value__gte=3.0, grade_value__lt=3.5).count(),
            'F': grades.filter(grade_value__lt=3.0).count(),
        }
        return JsonResponse({
            'role': 'student',
            'total_courses': student.enrollments.filter(status='active').count(),
            'total_grades': grades.count(),
            'avg_grade': student.average_grade or 0,
            'grade_distribution': grade_distribution,
        })

    if user.is_teacher():
        grade_qs = Grade.objects.filter(enrollment__course__teacher=user)
        course_qs = Course.objects.filter(teacher=user, is_active=True)
        student_count = Student.objects.filter(
            enrollments__course__teacher=user, is_active=True
        ).distinct().count()
        enrollment_count = Enrollment.objects.filter(
            course__teacher=user, status='active'
        ).count()
    else:
        grade_qs = Grade.objects.all()
        course_qs = Course.objects.filter(is_active=True)
        student_count = Student.objects.filter(is_active=True).count()
        enrollment_count = Enrollment.objects.filter(status='active').count()

    grade_distribution = {
        'A': grade_qs.filter(grade_value__gte=4.5).count(),
        'B': grade_qs.filter(grade_value__gte=4.0, grade_value__lt=4.5).count(),
        'C': grade_qs.filter(grade_value__gte=3.5, grade_value__lt=4.0).count(),
        'D': grade_qs.filter(grade_value__gte=3.0, grade_value__lt=3.5).count(),
        'F': grade_qs.filter(grade_value__lt=3.0).count(),
    }

    course_stats = course_qs.annotate(
        enrollment_count=Count('enrollments', filter=Q(enrollments__status='active'))
    ).order_by('-enrollment_count')[:8]

    avg_grade = grade_qs.aggregate(avg=Avg('grade_value'))['avg']

    return JsonResponse({
        'role': user.role,
        'total_students': student_count,
        'total_courses': course_qs.count(),
        'total_enrollments': enrollment_count,
        'total_grades': grade_qs.count(),
        'avg_grade': round(avg_grade, 2) if avg_grade else 0,
        'grade_distribution': grade_distribution,
        'course_labels': [c.course_code for c in course_stats],
        'course_data': [c.enrollment_count for c in course_stats],
    })


# ─── Students ────────────────────────────────────────────────────────

@login_required
def student_list(request):
    """List all students with search and filtering."""
    if request.user.is_student():
        messages.error(request, 'You do not have permission to view all students.')
        return redirect('dashboard')

    query = request.GET.get('q', '')
    program = request.GET.get('program', '')
    status = request.GET.get('status', '')

    if request.user.is_teacher():
        students = Student.objects.filter(enrollments__course__teacher=request.user).distinct()
    else:
        students = Student.objects.all()

    # Optimize queries by pre-calculating enrollment counts and average grades in the DB
    students = students.annotate(
        annotated_enrollment_count=Count('enrollments', filter=Q(enrollments__status='active'), distinct=True),
        annotated_average_grade=Avg('enrollments__grade__grade_value')
    )

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

    programs = Student.objects.values_list('study_program', flat=True).distinct()

    context = {
        'students': students,
        'query': query,
        'programs': programs,
        'selected_program': program,
        'selected_status': status,
    }
    return render(request, 'students/list.html', context)


@login_required
def student_detail(request, pk):
    """View student details with enrollments and grades."""
    student = get_object_or_404(Student, pk=pk)
    enrollments = Enrollment.objects.filter(student=student).select_related('course', 'grade')

    context = {
        'student': student,
        'enrollments': enrollments,
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
            messages.success(request, f'Student "{student.full_name}" has been created successfully.')
            return redirect('student_detail', pk=student.pk)
    else:
        form = StudentForm()

    return render(request, 'students/form.html', {'form': form, 'title': 'Add New Student'})


@login_required
@admin_required
def student_update(request, pk):
    """Edit an existing student record."""
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f'Student "{student.full_name}" has been updated.')
            return redirect('student_detail', pk=pk)
    else:
        form = StudentForm(instance=student)

    return render(request, 'students/form.html', {'form': form, 'title': 'Edit Student', 'student': student})


@login_required
@admin_required
def student_delete(request, pk):
    """Delete a student record."""
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        name = student.full_name
        student.delete()
        messages.success(request, f'Student "{name}" has been deleted.')
        return redirect('student_list')

    return render(request, 'students/confirm_delete.html', {'student': student})


# ─── Courses ─────────────────────────────────────────────────────────

@login_required
def course_list(request):
    """List all courses with search."""
    if request.user.is_student():
        messages.error(request, 'You do not have permission to view all courses.')
        return redirect('dashboard')

    query = request.GET.get('q', '')
    semester = request.GET.get('semester', '')

    if request.user.is_teacher():
        courses = Course.objects.filter(teacher=request.user).select_related('teacher').annotate(
            enrollment_count=Count('enrollments', filter=Q(enrollments__status='active'))
        )
    else:
        courses = Course.objects.select_related('teacher').annotate(
            enrollment_count=Count('enrollments', filter=Q(enrollments__status='active'))
        )

    if query:
        courses = courses.filter(
            Q(course_name__icontains=query) |
            Q(course_code__icontains=query)
        )
    if semester:
        courses = courses.filter(semester=semester)

    context = {
        'courses': courses,
        'query': query,
        'selected_semester': semester,
    }
    return render(request, 'courses/list.html', context)


@login_required
def course_detail(request, pk):
    """View course details with enrolled students."""
    course = get_object_or_404(Course, pk=pk)
    enrollments = Enrollment.objects.filter(course=course).select_related('student', 'grade')

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
            messages.success(request, f'Course "{course.course_name}" has been created.')
            return redirect('course_detail', pk=course.pk)
    else:
        form = CourseForm()

    return render(request, 'courses/form.html', {'form': form, 'title': 'Add New Course'})


@login_required
@admin_required
def course_update(request, pk):
    """Edit an existing course."""
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f'Course "{course.course_name}" has been updated.')
            return redirect('course_detail', pk=pk)
    else:
        form = CourseForm(instance=course)

    return render(request, 'courses/form.html', {'form': form, 'title': 'Edit Course', 'course': course})


@login_required
@admin_required
def course_delete(request, pk):
    """Delete a course."""
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        name = course.course_name
        course.delete()
        messages.success(request, f'Course "{name}" has been deleted.')
        return redirect('course_list')

    return render(request, 'courses/confirm_delete.html', {'course': course})


# ─── Enrollments ──────────────────────────────────────────────────────

@login_required
def enrollment_list(request):
    """List all enrollments."""
    if request.user.is_student():
        messages.error(request, 'You do not have permission to view all enrollments.')
        return redirect('dashboard')
    elif request.user.is_teacher():
        messages.error(request, 'You do not have permission to manage enrollments. Please use the courses tab.')
        return redirect('dashboard')
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')

    enrollments = Enrollment.objects.select_related('student', 'course', 'grade')

    if query:
        enrollments = enrollments.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(course__course_name__icontains=query) |
            Q(course__course_code__icontains=query)
        )
    if status:
        enrollments = enrollments.filter(status=status)

    context = {
        'enrollments': enrollments,
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
            messages.success(request, f'{enrollment.student.full_name} enrolled in {enrollment.course.course_code}.')
            return redirect('enrollment_list')
    else:
        form = EnrollmentForm()

    return render(request, 'enrollments/form.html', {'form': form, 'title': 'New Enrollment'})


@login_required
@admin_required
def enrollment_update(request, pk):
    """Update enrollment status."""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    if request.method == 'POST':
        form = EnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Enrollment updated successfully.')
            return redirect('enrollment_list')
    else:
        form = EnrollmentForm(instance=enrollment)

    return render(request, 'enrollments/form.html', {'form': form, 'title': 'Edit Enrollment', 'enrollment': enrollment})


@login_required
@admin_required
def enrollment_delete(request, pk):
    """Delete an enrollment."""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    if request.method == 'POST':
        enrollment.delete()
        messages.success(request, 'Enrollment has been removed.')
        return redirect('enrollment_list')

    return render(request, 'enrollments/confirm_delete.html', {'enrollment': enrollment})


# ─── Grades ───────────────────────────────────────────────────────────

@login_required
def grade_list(request):
    """List all grades."""
    query = request.GET.get('q', '')

    grades = Grade.objects.select_related(
        'enrollment__student', 'enrollment__course'
    )

    if request.user.is_student():
        try:
            grades = grades.filter(enrollment__student=request.user.student_profile)
        except Student.DoesNotExist:
            grades = Grade.objects.none()
    elif request.user.is_teacher():
        grades = grades.filter(enrollment__course__teacher=request.user)

    if query:
        grades = grades.filter(
            Q(enrollment__student__first_name__icontains=query) |
            Q(enrollment__student__last_name__icontains=query) |
            Q(enrollment__course__course_code__icontains=query)
        )

    context = {
        'grades': grades,
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
            grade = form.save()
            messages.success(request, f'Grade {grade.grade_value} assigned successfully.')
            return redirect('grade_list')
    else:
        form = GradeForm(user=request.user)

    return render(request, 'grades/form.html', {'form': form, 'title': 'Assign Grade'})


@login_required
@teacher_or_admin_required
def grade_update(request, pk):
    """Update an existing grade."""
    grade = get_object_or_404(Grade, pk=pk)

    # Teachers can only edit grades for their own courses
    if request.user.is_teacher() and grade.enrollment.course.teacher != request.user:
        messages.error(request, 'You can only edit grades for your own courses.')
        return redirect('grade_list')

    if request.method == 'POST':
        form = GradeForm(request.POST, instance=grade, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grade updated successfully.')
            return redirect('grade_list')
    else:
        form = GradeForm(instance=grade, user=request.user)

    return render(request, 'grades/form.html', {'form': form, 'title': 'Edit Grade', 'grade': grade})


@login_required
@admin_required
def grade_delete(request, pk):
    """Delete a grade."""
    grade = get_object_or_404(Grade, pk=pk)
    if request.method == 'POST':
        grade.delete()
        messages.success(request, 'Grade has been deleted.')
        return redirect('grade_list')

    return render(request, 'grades/confirm_delete.html', {'grade': grade})


# ─── Attendance ───────────────────────────────────────────────────────

@login_required
def attendance_list(request):
    """List attendance records."""
    records = Attendance.objects.select_related('enrollment__student', 'enrollment__course')
    
    if request.user.is_student():
        try:
            records = records.filter(enrollment__student=request.user.student_profile)
        except Student.DoesNotExist:
            records = Attendance.objects.none()
    elif request.user.is_teacher():
        records = records.filter(enrollment__course__teacher=request.user)

    query = request.GET.get('q', '')
    if query:
        records = records.filter(
            Q(enrollment__student__first_name__icontains=query) |
            Q(enrollment__student__last_name__icontains=query) |
            Q(enrollment__course__course_code__icontains=query)
        )

    context = {
        'records': records,
        'query': query,
    }
    return render(request, 'attendance/list.html', context)


@login_required
@teacher_or_admin_required
def attendance_create(request):
    """Mark attendance."""
    if request.method == 'POST':
        form = AttendanceForm(request.POST, user=request.user)
        if form.is_valid():
            att = form.save()
            messages.success(request, f'Attendance marked for {att.enrollment.student.full_name}.')
            if 'save_and_add_another' in request.POST:
                return redirect('attendance_create')
            return redirect('attendance_list')
    else:
        form = AttendanceForm(user=request.user)
    
    return render(request, 'attendance/form.html', {'form': form, 'title': 'Mark Attendance'})


@login_required
@teacher_or_admin_required
def attendance_update(request, pk):
    att = get_object_or_404(Attendance, pk=pk)
    if request.user.is_teacher() and att.enrollment.course.teacher != request.user:
        messages.error(request, 'You can only edit attendance for your own courses.')
        return redirect('attendance_list')
        
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=att, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance updated.')
            return redirect('attendance_list')
    else:
        form = AttendanceForm(instance=att, user=request.user)
    return render(request, 'attendance/form.html', {'form': form, 'title': 'Edit Attendance', 'att': att})


@login_required
@admin_required
def attendance_delete(request, pk):
    att = get_object_or_404(Attendance, pk=pk)
    if request.method == 'POST':
        att.delete()
        messages.success(request, 'Attendance record deleted.')
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
            messages.success(request, 'Profile updated successfully.')
            # Update password if requested (we'll rely on the standard password reset emails, 
            # but for basic names/emails we use this form).
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'profile/index.html', {'form': form})


# ─── Reports ──────────────────────────────────────────────────────────

@login_required
@teacher_or_admin_required
def export_students_csv(request):
    """Export students list to CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Number', 'First Name', 'Last Name', 'Email', 'Program', 'Status', 'Enrollment Date'])
    
    students = Student.objects.all()
    for s in students:
        writer.writerow([
            s.student_number, s.first_name, s.last_name, s.email, 
            s.study_program, 'Active' if s.is_active else 'Inactive', s.date_enrolled
        ])
    return response


@login_required
@teacher_or_admin_required
def export_grades_csv(request):
    """Export grades list to CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="grades_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student', 'Course Code', 'Course Name', 'Grade', 'Letter', 'Date Assigned'])
    
    grades = Grade.objects.select_related('enrollment__student', 'enrollment__course')
    if request.user.is_teacher():
        grades = grades.filter(enrollment__course__teacher=request.user)
        
    for g in grades:
        writer.writerow([
            g.enrollment.student.full_name, g.enrollment.course.course_code, 
            g.enrollment.course.course_name, g.grade_value, g.letter_grade, g.date_assigned
        ])
    return response
