from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from .models import Student, Course, Enrollment, Grade, User, Attendance


class LoginForm(AuthenticationForm):
    """Custom login form with styled widgets."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Username'),
            'id': 'login-username',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Password'),
            'id': 'login-password',
            'autocomplete': 'current-password',
        })
    )


class StudentForm(forms.ModelForm):
    """Form for creating and editing student records."""
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'email', 'student_number',
            'study_program', 'date_enrolled', 'phone', 'address',
            'date_of_birth', 'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('First Name')}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Last Name')}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Email Address')}),
            'student_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g., STU-2025-001')}),
            'study_program': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g., Computer Science')}),
            'date_enrolled': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Phone Number')}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Address')}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CourseForm(forms.ModelForm):
    """Form for creating and editing courses."""
    class Meta:
        model = Course
        fields = [
            'course_name', 'course_code', 'semester', 'credits',
            'description', 'teacher', 'max_students', 'is_active'
        ]
        widgets = {
            'course_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Course Name')}),
            'course_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g., CS101')}),
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'credits': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 30}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': _('Course description...')}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = User.objects.filter(role='teacher')
        self.fields['teacher'].required = False


class EnrollmentForm(forms.ModelForm):
    """Form for enrolling students in courses."""
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'status']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        course = cleaned_data.get('course')
        status = cleaned_data.get('status')

        if student and course:
            existing = Enrollment.objects.filter(student=student, course=course)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(_('This student is already enrolled in this course.'))

            if status == 'active':
                taken = course.enrollments.filter(status='active')
                if self.instance.pk:
                    taken = taken.exclude(pk=self.instance.pk)
                if taken.count() >= course.max_students:
                    raise forms.ValidationError(
                        _('%(code)s is full (%(seats)s seats). Increase the course '
                          'capacity or drop another enrollment first.')
                        % {'code': course.course_code, 'seats': course.max_students}
                    )

        return cleaned_data


class GradeForm(forms.ModelForm):
    """Form for assigning and editing grades."""
    class Meta:
        model = Grade
        fields = ['enrollment', 'grade_value', 'comments']
        widgets = {
            'enrollment': forms.Select(attrs={'class': 'form-select'}),
            'grade_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '2.0', 'max': '5.0', 'step': '0.1',
                'placeholder': '2.0 - 5.0'
            }),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Optional comments...')}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Only show enrollments without grades (unless editing existing)
        graded_ids = Grade.objects.values_list('enrollment_id', flat=True)
        qs = Enrollment.objects.exclude(id__in=graded_ids)
        if self.instance.pk:
            qs = qs | Enrollment.objects.filter(id=self.instance.enrollment_id)
        if user and user.is_teacher():
            qs = qs.filter(course__teacher=user)
        self.fields['enrollment'].queryset = qs


class AttendanceForm(forms.ModelForm):
    """Form for marking attendance."""
    class Meta:
        model = Attendance
        fields = ['enrollment', 'date', 'status', 'notes']
        widgets = {
            'enrollment': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Optional notes...')}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        qs = Enrollment.objects.all()
        if user and user.is_teacher():
            qs = qs.filter(course__teacher=user)
        self.fields['enrollment'].queryset = qs


class ProfileForm(forms.ModelForm):
    """Form for updating user profile."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
