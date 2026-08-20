from datetime import date

from django.core import mail
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from core.models import User, Student, Course, Enrollment, Grade, Attendance


class CoreModelTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='testteacher', password='password', role='teacher'
        )

        self.student = Student.objects.create(
            first_name='Ivan',
            last_name='Ivanov',
            email='ivan@example.com',
            student_number='S12345',
            study_program='Computer Science',
            date_enrolled='2024-09-01',
        )

        self.course = Course.objects.create(
            course_name='Math 101',
            course_code='MATH101',
            semester='Fall',
            credits=5,
            teacher=self.teacher,
            max_students=30,
        )

        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='active',
        )

    def test_student_str_representation(self):
        self.assertEqual(str(self.student), 'Ivan Ivanov (S12345)')
        self.assertEqual(self.student.full_name, 'Ivan Ivanov')

    def test_course_available_seats(self):
        self.assertEqual(self.course.enrolled_count, 1)
        self.assertEqual(self.course.available_seats, 29)

    def test_grade_letter(self):
        grade1 = Grade.objects.create(enrollment=self.enrollment, grade_value=4.6)
        self.assertEqual(grade1.letter_grade, 'A')

        grade2 = Grade.objects.create(
            enrollment=Enrollment.objects.create(
                student=Student.objects.create(
                    first_name='Petr',
                    last_name='Petrov',
                    email='petr@example.com',
                    student_number='S54321',
                    study_program='IT',
                    date_enrolled='2024-09-01',
                ),
                course=self.course,
            ),
            grade_value=3.2,
        )
        self.assertEqual(grade2.letter_grade, 'D')

    def test_student_average_grade(self):
        Grade.objects.create(enrollment=self.enrollment, grade_value=4.0)

        course2 = Course.objects.create(
            course_name='Physics 101',
            course_code='PHYS101',
            semester='Fall',
            credits=4,
            max_students=30,
        )
        enrollment2 = Enrollment.objects.create(student=self.student, course=course2)
        Grade.objects.create(enrollment=enrollment2, grade_value=5.0)

        self.assertEqual(self.student.average_grade, 4.5)

    def test_user_role_helpers(self):
        admin = User.objects.create_user(username='admin1', password='x', role='admin')
        self.assertTrue(admin.is_admin())
        self.assertTrue(self.teacher.is_teacher())

    def test_attendance_unique_per_day(self):
        Attendance.objects.create(
            enrollment=self.enrollment,
            date=date(2024, 10, 1),
            status='present',
        )
        with self.assertRaises(Exception):
            Attendance.objects.create(
                enrollment=self.enrollment,
                date=date(2024, 10, 1),
                status='absent',
            )


class AuthAndAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin', password='pass12345', role='admin'
        )
        self.teacher = User.objects.create_user(
            username='teacher', password='pass12345', role='teacher',
            first_name='Anna', last_name='Nowak',
        )
        self.student = Student.objects.create(
            first_name='Ola',
            last_name='Kowalska',
            email='ola@example.com',
            student_number='S100',
            study_program='Computer Science',
            date_enrolled='2024-09-01',
        )

    def test_login_success_redirects_to_dashboard(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'teacher', 'password': 'pass12345'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))

    def test_login_failure(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'teacher', 'password': 'wrong'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_teacher_can_open_dashboard(self):
        self.client.login(username='teacher', password='pass12345')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)


class DashboardApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin', password='pass12345', role='admin'
        )
        self.teacher = User.objects.create_user(
            username='teacher', password='pass12345', role='teacher'
        )
        student = Student.objects.create(
            first_name='Ola',
            last_name='Kowalska',
            email='ola@example.com',
            student_number='S100',
            study_program='Computer Science',
            date_enrolled='2024-09-01',
        )
        course = Course.objects.create(
            course_name='Algorithms',
            course_code='CS201',
            semester='Fall',
            credits=6,
            teacher=self.teacher,
        )
        enrollment = Enrollment.objects.create(student=student, course=course)
        Grade.objects.create(enrollment=enrollment, grade_value=4.7)

    def test_api_requires_auth(self):
        response = self.client.get(reverse('api_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_api_admin_payload(self):
        self.client.login(username='admin', password='pass12345')
        response = self.client.get(reverse('api_dashboard'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['role'], 'admin')
        self.assertIn('grade_distribution', data)
        self.assertIn('course_labels', data)
        self.assertEqual(data['total_grades'], 1)
        self.assertEqual(data['grade_distribution']['A'], 1)

    def test_api_teacher_scoped(self):
        self.client.login(username='teacher', password='pass12345')
        response = self.client.get(reverse('api_dashboard'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['role'], 'teacher')
        self.assertEqual(data['total_courses'], 1)



@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='sms@test.local',
)
class PasswordResetEmailTests(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_user(
            username='resetme',
            password='pass12345',
            email='resetme@example.com',
            role='teacher',
        )

    def test_password_reset_sends_email(self):
        response = self.client.post(
            reverse('password_reset'),
            {'email': 'resetme@example.com'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('password', mail.outbox[0].subject.lower())
        self.assertIn('resetme@example.com', mail.outbox[0].to)

    def test_password_reset_unknown_email_still_redirects(self):
        response = self.client.post(
            reverse('password_reset'),
            {'email': 'nobody@example.com'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)


class CrudFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin', password='pass12345', role='admin'
        )
        self.teacher = User.objects.create_user(
            username='teacher', password='pass12345', role='teacher'
        )
        self.client.login(username='admin', password='pass12345')

    def test_create_student(self):
        response = self.client.post(
            reverse('student_create'),
            {
                'first_name': 'Jan',
                'last_name': 'Kowalski',
                'email': 'jan@example.com',
                'student_number': 'S999',
                'study_program': 'IT',
                'date_enrolled': '2025-01-15',
                'phone': '',
                'address': '',
                'is_active': True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Student.objects.filter(student_number='S999').exists())

    def test_create_course(self):
        response = self.client.post(
            reverse('course_create'),
            {
                'course_name': 'Databases',
                'course_code': 'DB101',
                'semester': 'Spring',
                'credits': 5,
                'description': 'Intro DB',
                'teacher': self.teacher.pk,
                'max_students': 25,
                'is_active': True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Course.objects.filter(course_code='DB101').exists())
