from django.contrib import admin
from .models import User, Student, Course, Enrollment, Grade, Attendance


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'last_name', 'role', 'department']
    list_filter = ['role']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_number', 'first_name', 'last_name', 'study_program', 'is_active']
    list_filter = ['study_program', 'is_active']
    search_fields = ['first_name', 'last_name', 'student_number']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'course_name', 'semester', 'credits', 'teacher']
    list_filter = ['semester', 'is_active']
    search_fields = ['course_name', 'course_code']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'status', 'enrollment_date']
    list_filter = ['status']


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'grade_value', 'date_assigned']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'date', 'status']
    list_filter = ['status', 'date']
