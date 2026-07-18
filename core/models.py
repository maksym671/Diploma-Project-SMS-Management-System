from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class User(AbstractUser):
    """Custom user model with role-based access control."""
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='teacher')
    department = models.CharField(max_length=100, blank=True)

    def is_admin(self):
        return self.role == 'admin'

    def is_teacher(self):
        return self.role == 'teacher'

    def is_student(self):
        return self.role == 'student'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class Student(models.Model):
    """Student record with personal and academic information."""
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    student_number = models.CharField(max_length=20, unique=True)
    study_program = models.CharField(max_length=150)
    date_enrolled = models.DateField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_number})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def enrollment_count(self):
        return self.enrollments.count()

    @property
    def average_grade(self):
        grades = Grade.objects.filter(enrollment__student=self)
        if grades.exists():
            return round(grades.aggregate(models.Avg('grade_value'))['grade_value__avg'], 2)
        return None


class Course(models.Model):
    """Course offered by the institution."""
    SEMESTER_CHOICES = [
        ('Fall', 'Fall'),
        ('Spring', 'Spring'),
        ('Summer', 'Summer'),
    ]
    course_name = models.CharField(max_length=200)
    course_code = models.CharField(max_length=20, unique=True)
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    credits = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(30)])
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'role': 'teacher'},
        related_name='courses'
    )
    max_students = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['course_code']

    def __str__(self):
        return f"{self.course_code} — {self.course_name}"

    @property
    def enrolled_count(self):
        return self.enrollments.filter(status='active').count()

    @property
    def available_seats(self):
        return self.max_students - self.enrolled_count


class Enrollment(models.Model):
    """Many-to-many relationship between Student and Course."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrollment_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-enrollment_date']

    def __str__(self):
        return f"{self.student.full_name} → {self.course.course_code}"


class Grade(models.Model):
    """Academic grade assigned to a student for a specific enrollment."""
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='grade')
    grade_value = models.DecimalField(
        max_digits=3, decimal_places=1,
        validators=[MinValueValidator(2.0), MaxValueValidator(5.0)],
        help_text="Grade from 2.0 (fail) to 5.0 (excellent)"
    )
    date_assigned = models.DateField(auto_now_add=True)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_assigned']

    def __str__(self):
        return f"{self.enrollment} — {self.grade_value}"

    @property
    def letter_grade(self):
        v = float(self.grade_value)
        if v >= 4.5:
            return 'A'
        elif v >= 4.0:
            return 'B'
        elif v >= 3.5:
            return 'C'
        elif v >= 3.0:
            return 'D'
        else:
            return 'F'


class Attendance(models.Model):
    """Attendance tracking for students in a specific course."""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['enrollment', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.enrollment.student.full_name} - {self.date} ({self.get_status_display()})"
