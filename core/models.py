from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import F, FloatField, Sum
from django.db.models.functions import Cast
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def letter_for(value):
    """Letter band for a numeric grade — used by single grades and averages alike."""
    if value is None:
        return None
    v = float(value)
    if v >= 4.5:
        return 'A'
    if v >= 4.0:
        return 'B'
    if v >= 3.5:
        return 'C'
    if v >= 3.0:
        return 'D'
    return 'F'


def weighted_average(grades):
    """Weighted mean of an iterable of Grade rows, or None when there are none.

    Course marks are made of components that do not count equally — a final
    exam usually outweighs a midterm — so every average in the system runs
    through here instead of a plain mean.
    """
    total = Decimal('0')
    weight = 0
    for grade in grades:
        total += Decimal(grade.grade_value) * grade.weight
        weight += grade.weight
    if not weight:
        return None
    return (total / weight).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def weighted_mean(total, weight):
    """Round a summed product and summed weight into a course mark."""
    if not weight:
        return None
    return Decimal(str(total / weight)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP,
    )


def weighted_average_qs(qs):
    """Same figure as `weighted_average`, computed in SQL instead of Python.

    The dashboard and JSON endpoint used to load every Grade row just to
    multiply in a loop. On SQLite the product must be floated first or the
    division becomes integer division (350/100 → 3).
    """
    row = qs.aggregate(
        total=Cast(Sum(F('grade_value') * F('weight')), FloatField()),
        weight=Cast(Sum('weight'), FloatField()),
    )
    return weighted_mean(row['total'], row['weight'])


class User(AbstractUser):
    """Custom user model with role-based access control."""
    ROLE_CHOICES = [
        ('admin', _('Administrator')),
        ('teacher', _('Teacher')),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='teacher')
    department = models.CharField(max_length=100, blank=True)

    def is_admin(self):
        return self.role == 'admin'

    def is_teacher(self):
        return self.role == 'teacher'


    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class Student(models.Model):
    """Student record with personal and academic information."""
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
        """Weighted mean over every graded component this student has."""
        return weighted_average(Grade.objects.filter(enrollment__student=self))


class Course(models.Model):
    """Course offered by the institution."""
    SEMESTER_CHOICES = [
        ('Fall', _('Fall')),
        ('Spring', _('Spring')),
        ('Summer', _('Summer')),
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
        ('active', _('Active')),
        ('completed', _('Completed')),
        ('dropped', _('Dropped')),
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

    @property
    def final_grade(self):
        """Course mark: the weighted mean of this enrolment's components.

        Reads `self.grades.all()`, so a view that prefetches the relation pays
        no extra query per row.
        """
        return weighted_average(self.grades.all())

    @property
    def final_letter(self):
        return letter_for(self.final_grade)


class Grade(models.Model):
    """One graded component of an enrolment — a midterm, an exam, coursework.

    An enrolment carries several of these; `Enrollment.final_grade` combines
    them by weight into the course mark.
    """
    KIND_CHOICES = [
        ('coursework', _('Coursework')),
        ('midterm', _('Midterm')),
        ('final', _('Final exam')),
        ('retake', _('Retake')),
    ]
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='grades')
    kind = models.CharField(
        max_length=12, choices=KIND_CHOICES, default='final',
        help_text=_('Which part of the course this mark is for'),
    )
    weight = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text=_('How much this component counts towards the course mark'),
    )
    grade_value = models.DecimalField(
        max_digits=3, decimal_places=1,
        validators=[MinValueValidator(2.0), MaxValueValidator(5.0)],
        help_text=_('Grade from 2.0 (fail) to 5.0 (excellent)')
    )
    date_assigned = models.DateField(auto_now_add=True)
    comments = models.TextField(blank=True)
    assigned_by = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='grades_assigned',
        help_text=_('Account that last saved this grade'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_assigned', 'kind']

    def __str__(self):
        return f"{self.enrollment} — {self.get_kind_display()} {self.grade_value}"

    @property
    def letter_grade(self):
        return letter_for(self.grade_value)


class Attendance(models.Model):
    """Attendance tracking for students in a specific course."""
    STATUS_CHOICES = [
        ('present', _('Present')),
        ('absent', _('Absent')),
        ('late', _('Late')),
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
