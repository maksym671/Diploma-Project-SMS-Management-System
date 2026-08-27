from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
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
    """Form for assigning and editing one graded component of an enrolment."""
    class Meta:
        model = Grade
        fields = ['enrollment', 'kind', 'weight', 'grade_value', 'comments']
        widgets = {
            'enrollment': forms.Select(attrs={'class': 'form-select'}),
            'kind': forms.Select(attrs={'class': 'form-select'}),
            'weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1', 'max': '100', 'step': '1',
            }),
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
        # An enrolment now takes several components, so every enrolment stays
        # selectable; a teacher still only sees their own courses.
        qs = Enrollment.objects.select_related('student', 'course')
        if user and user.is_teacher():
            qs = qs.filter(course__teacher=user)
        self.fields['enrollment'].queryset = qs

    def clean(self):
        cleaned_data = super().clean()
        enrollment = cleaned_data.get('enrollment')
        weight = cleaned_data.get('weight')

        if enrollment and weight:
            # The components of one course must not add up to more than a
            # whole course, or the weighted mark stops meaning anything.
            others = enrollment.grades.exclude(pk=self.instance.pk)
            used = sum(grade.weight for grade in others)
            if used + weight > 100:
                raise forms.ValidationError(
                    _('The components of %(code)s already use %(used)s%% of the '
                      'course weight, so this one can be at most %(free)s%%.')
                    % {
                        'code': enrollment.course.course_code,
                        'used': used,
                        'free': 100 - used,
                    }
                )

        return cleaned_data


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


class TeacherForm(forms.ModelForm):
    """Create or edit a teacher account. Password is required only on create."""

    password1 = forms.CharField(
        label=_('Password'),
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
    )
    password2 = forms.CharField(
        label=_('Confirm password'),
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'department', 'is_active',
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
            }),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Computer Science'),
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        creating = self.instance.pk is None
        self.fields['password1'].required = creating
        self.fields['password2'].required = creating
        if not creating:
            self.fields['username'].disabled = True
            self.fields['password1'].help_text = _(
                'Leave blank to keep the current password.'
            )

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            return email
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                _('A staff account with this email already exists.')
            )
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1') or ''
        password2 = cleaned.get('password2') or ''
        creating = self.instance.pk is None

        if password1 or password2:
            if password1 != password2:
                self.add_error('password2', _('The two passwords do not match.'))
            elif password1:
                try:
                    validate_password(password1, user=self.instance)
                except DjangoValidationError as exc:
                    self.add_error('password1', exc)
        elif creating:
            self.add_error('password1', _('This field is required.'))
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'teacher'
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


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
