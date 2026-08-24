import os
from datetime import date
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core import mail
from django.core.management import call_command
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


class TeacherDataIsolationTests(TestCase):
    """A teacher must only reach records belonging to their own courses."""

    def setUp(self):
        self.client = Client()
        self.own = User.objects.create_user(username='own', password='pass12345', role='teacher')
        self.other = User.objects.create_user(username='other', password='pass12345', role='teacher')

        self.own_course = Course.objects.create(
            course_name='Own', course_code='OWN1', semester='Fall', credits=5, teacher=self.own
        )
        self.other_course = Course.objects.create(
            course_name='Other', course_code='OTH1', semester='Fall', credits=5, teacher=self.other
        )

        self.own_student = Student.objects.create(
            first_name='Mine', last_name='Student', email='mine@example.com',
            student_number='S-MINE', study_program='IT', date_enrolled='2024-09-01',
        )
        self.other_student = Student.objects.create(
            first_name='Foreign', last_name='Student', email='foreign@example.com',
            student_number='S-FOREIGN', study_program='IT', date_enrolled='2024-09-01',
        )
        Enrollment.objects.create(student=self.own_student, course=self.own_course)
        Enrollment.objects.create(student=self.other_student, course=self.other_course)

        self.client.login(username='own', password='pass12345')

    def test_own_student_detail_is_visible(self):
        response = self.client.get(reverse('student_detail', args=[self.own_student.pk]))
        self.assertEqual(response.status_code, 200)

    def test_foreign_student_detail_is_hidden(self):
        response = self.client.get(reverse('student_detail', args=[self.other_student.pk]))
        self.assertEqual(response.status_code, 404)

    def test_own_course_detail_is_visible(self):
        response = self.client.get(reverse('course_detail', args=[self.own_course.pk]))
        self.assertEqual(response.status_code, 200)

    def test_foreign_course_detail_is_hidden(self):
        response = self.client.get(reverse('course_detail', args=[self.other_course.pk]))
        self.assertEqual(response.status_code, 404)

    def test_student_csv_export_is_scoped(self):
        body = self.client.get(reverse('export_students_csv')).content.decode('utf-8-sig')
        self.assertIn('S-MINE', body)
        self.assertNotIn('S-FOREIGN', body)

    def test_enrollment_list_is_scoped_and_read_only(self):
        response = self.client.get(reverse('enrollment_list'))
        self.assertEqual(response.status_code, 200)

        rows = response.context['page_obj'].object_list
        self.assertEqual([e.course_id for e in rows], [self.own_course.pk])

        # No management controls for a teacher, and the endpoints stay closed.
        self.assertNotContains(response, reverse('enrollment_create'))
        self.assertEqual(self.client.get(reverse('enrollment_create')).status_code, 302)

    def test_cannot_touch_grades_of_foreign_courses(self):
        foreign_enrollment = Enrollment.objects.get(course=self.other_course)
        foreign_grade = Grade.objects.create(enrollment=foreign_enrollment, grade_value=5.0)

        for url in [
            reverse('grade_update', args=[foreign_grade.pk]),
            reverse('grade_delete', args=[foreign_grade.pk]),
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, reverse('grade_list'))

        self.client.post(reverse('grade_delete', args=[foreign_grade.pk]))
        self.assertTrue(Grade.objects.filter(pk=foreign_grade.pk).exists())

    def test_admin_sees_everything(self):
        User.objects.create_user(username='root', password='pass12345', role='admin')
        self.client.login(username='root', password='pass12345')

        self.assertEqual(
            self.client.get(reverse('student_detail', args=[self.other_student.pk])).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse('course_detail', args=[self.other_course.pk])).status_code, 200
        )


class LogoutSafetyTests(TestCase):
    """Logout must not be reachable by GET (link prefetching would end sessions)."""

    def setUp(self):
        self.client = Client()
        User.objects.create_user(username='teacher', password='pass12345', role='teacher')
        self.client.login(username='teacher', password='pass12345')

    def test_get_request_is_rejected_and_session_kept(self):
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    def test_post_request_logs_out(self):
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)


class PaginationTests(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_user(username='admin', password='pass12345', role='admin')
        self.client.login(username='admin', password='pass12345')

        for i in range(25):
            Student.objects.create(
                first_name=f'S{i}', last_name='Test', email=f's{i}@example.com',
                student_number=f'N{i}', study_program='IT', date_enrolled='2024-09-01',
            )

    def test_first_page_is_limited(self):
        response = self.client.get(reverse('student_list'))
        self.assertEqual(len(response.context['page_obj'].object_list), 20)
        self.assertTrue(response.context['page_obj'].has_next())

    def test_second_page_holds_the_remainder(self):
        response = self.client.get(reverse('student_list'), {'page': 2})
        self.assertEqual(len(response.context['page_obj'].object_list), 5)

    def test_filters_survive_pagination_links(self):
        response = self.client.get(reverse('student_list'), {'q': 'Test', 'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'q=Test')


class GradeAuditTests(TestCase):
    """Every grade must record which account put it there."""

    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            username='teacher', password='pass12345', role='teacher',
            first_name='Anna', last_name='Kowalska',
        )
        self.admin = User.objects.create_user(
            username='admin', password='pass12345', role='admin',
        )
        self.course = Course.objects.create(
            course_name='Databases', course_code='DB101', semester='Fall',
            credits=5, teacher=self.teacher,
        )
        self.student = Student.objects.create(
            first_name='Jan', last_name='Nowak', email='jan@example.com',
            student_number='S-1', study_program='CS', date_enrolled=date(2025, 9, 1),
        )
        self.enrollment = Enrollment.objects.create(student=self.student, course=self.course)

    def test_creating_a_grade_records_its_author(self):
        self.client.login(username='teacher', password='pass12345')
        self.client.post(reverse('grade_create'), {
            'enrollment': self.enrollment.pk, 'grade_value': '4.5', 'comments': '',
        })

        grade = Grade.objects.get(enrollment=self.enrollment)
        self.assertEqual(grade.assigned_by, self.teacher)

    def test_editing_a_grade_records_the_last_editor(self):
        grade = Grade.objects.create(
            enrollment=self.enrollment, grade_value=3.0, assigned_by=self.teacher,
        )

        self.client.login(username='admin', password='pass12345')
        self.client.post(reverse('grade_update', args=[grade.pk]), {
            'enrollment': self.enrollment.pk, 'grade_value': '5.0', 'comments': 'corrected',
        })

        grade.refresh_from_db()
        self.assertEqual(grade.grade_value, Decimal('5.0'))
        self.assertEqual(grade.assigned_by, self.admin)

    def test_author_is_shown_in_the_list_and_the_csv_export(self):
        Grade.objects.create(
            enrollment=self.enrollment, grade_value=4.0, assigned_by=self.teacher,
        )
        self.client.login(username='admin', password='pass12345')

        self.assertContains(self.client.get(reverse('grade_list')), 'Anna Kowalska')

        csv_body = self.client.get(reverse('export_grades_csv')).content.decode('utf-8-sig')
        self.assertIn('Assigned By', csv_body)
        self.assertIn('Anna Kowalska', csv_body)


class LocalizationTests(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_user(username='teacher', password='pass12345', role='teacher')
        self.client.login(username='teacher', password='pass12345')

    def test_html_lang_attribute_is_populated(self):
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, '<html lang="en"')
        self.assertNotContains(response, 'lang=""')

    def test_switching_to_polish_translates_the_interface(self):
        self.client.post(reverse('set_language'), {'language': 'pl', 'next': '/'})

        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, '<html lang="pl"')
        self.assertContains(response, 'Panel Główny')

        # Every list page must be fully translated, not a mix of both languages.
        for url, polish, english in [
            (reverse('student_list'), 'Numer albumu', 'Student Number'),
            (reverse('course_list'), 'Punkty ECTS', 'Credits</th>'),
            (reverse('grade_list'), 'Data wystawienia', 'Date Assigned'),
            (reverse('attendance_list'), 'Akcje', 'Actions</th>'),
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, polish)
                self.assertNotContains(response, english)


class EnrollmentCapacityTests(TestCase):
    """max_students is advertised in the UI, so it must actually be enforced."""

    def setUp(self):
        self.client = Client()
        User.objects.create_user(username='admin', password='pass12345', role='admin')
        self.client.login(username='admin', password='pass12345')

        self.course = Course.objects.create(
            course_name='Tiny', course_code='TINY1', semester='Fall',
            credits=3, max_students=1,
        )
        self.first = Student.objects.create(
            first_name='First', last_name='S', email='first@example.com',
            student_number='C1', study_program='IT', date_enrolled='2024-09-01',
        )
        self.second = Student.objects.create(
            first_name='Second', last_name='S', email='second@example.com',
            student_number='C2', study_program='IT', date_enrolled='2024-09-01',
        )
        Enrollment.objects.create(student=self.first, course=self.course)

    def test_enrolling_beyond_capacity_is_rejected(self):
        response = self.client.post(reverse('enrollment_create'), {
            'student': self.second.pk, 'course': self.course.pk, 'status': 'active',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is full')
        self.assertEqual(self.course.enrollments.count(), 1)
        self.assertEqual(self.course.available_seats, 0)

    def test_dropped_enrollments_free_a_seat(self):
        self.course.enrollments.update(status='dropped')
        response = self.client.post(reverse('enrollment_create'), {
            'student': self.second.pk, 'course': self.course.pk, 'status': 'active',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Enrollment.objects.filter(student=self.second, course=self.course).exists()
        )

    def test_duplicate_enrollment_is_rejected(self):
        big = Course.objects.create(
            course_name='Big', course_code='BIG1', semester='Fall', credits=3, max_students=50
        )
        Enrollment.objects.create(student=self.first, course=big)
        response = self.client.post(reverse('enrollment_create'), {
            'student': self.first.pk, 'course': big.pk, 'status': 'active',
        })
        self.assertContains(response, 'already enrolled')


class SmokeRenderTests(TestCase):
    """Every page must render without template or query errors, for both roles."""

    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            username='teacher', password='pass12345', role='teacher'
        )
        User.objects.create_user(username='admin', password='pass12345', role='admin')

        student = Student.objects.create(
            first_name='Ola', last_name='Kowalska', email='ola@example.com',
            student_number='S100', study_program='IT', date_enrolled='2024-09-01',
        )
        course = Course.objects.create(
            course_name='Algorithms', course_code='CS201', semester='Fall',
            credits=6, teacher=self.teacher,
        )
        enrollment = Enrollment.objects.create(student=student, course=course)
        self.grade = Grade.objects.create(enrollment=enrollment, grade_value=4.5)
        self.attendance = Attendance.objects.create(enrollment=enrollment, date='2025-03-03')
        self.student, self.course, self.enrollment = student, course, enrollment

    def _list_and_detail_urls(self):
        return [
            reverse('dashboard'),
            reverse('api_dashboard'),
            reverse('student_list'),
            reverse('student_detail', args=[self.student.pk]),
            reverse('course_list'),
            reverse('course_detail', args=[self.course.pk]),
            reverse('grade_list'),
            reverse('attendance_list'),
            reverse('profile'),
            reverse('export_students_csv'),
            reverse('export_grades_csv'),
        ]

    def test_teacher_pages_render(self):
        self.client.login(username='teacher', password='pass12345')
        for url in self._list_and_detail_urls() + [reverse('enrollment_list')]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_pages_render(self):
        self.client.login(username='admin', password='pass12345')
        urls = self._list_and_detail_urls() + [
            reverse('enrollment_list'),
            reverse('student_create'),
            reverse('student_update', args=[self.student.pk]),
            reverse('student_delete', args=[self.student.pk]),
            reverse('course_create'),
            reverse('course_update', args=[self.course.pk]),
            reverse('enrollment_create'),
            reverse('enrollment_update', args=[self.enrollment.pk]),
            reverse('grade_update', args=[self.grade.pk]),
            reverse('attendance_create'),
            reverse('attendance_update', args=[self.attendance.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_teacher_cannot_reach_admin_only_pages(self):
        self.client.login(username='teacher', password='pass12345')
        for url in [
            reverse('student_create'),
            reverse('course_create'),
            reverse('enrollment_create'),
            reverse('enrollment_update', args=[self.enrollment.pk]),
            reverse('enrollment_delete', args=[self.enrollment.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)

    def test_teacher_manages_grades_and_attendance_of_own_courses(self):
        self.client.login(username='teacher', password='pass12345')
        for url in [
            reverse('grade_update', args=[self.grade.pk]),
            reverse('grade_delete', args=[self.grade.pk]),
            reverse('attendance_update', args=[self.attendance.pk]),
            reverse('attendance_delete', args=[self.attendance.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


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


class DeploymentSeedTests(TestCase):
    """`seed_demo` runs on every deploy, so it must never destroy live data."""

    def test_seeds_an_empty_database(self):
        call_command('seed_demo', stdout=StringIO())

        self.assertTrue(Student.objects.exists())
        self.assertTrue(Course.objects.exists())
        self.assertTrue(User.objects.filter(username='admin', role='admin').exists())

    def test_rerun_leaves_existing_data_untouched(self):
        Student.objects.create(
            first_name='Live',
            last_name='Record',
            email='live@example.com',
            student_number='STU-LIVE-1',
            date_of_birth=date(2000, 1, 1),
            study_program='Computer Science',
            date_enrolled='2024-09-01',
        )

        call_command('seed_demo', stdout=StringIO())

        self.assertEqual(Student.objects.count(), 1)

    def test_admin_password_comes_from_the_environment(self):
        call_command('seed_demo', stdout=StringIO())

        with mock.patch.dict(os.environ, {'DJANGO_ADMIN_PASSWORD': 'env-set-p4ssword'}):
            call_command('seed_demo', stdout=StringIO())

        admin = User.objects.get(username='admin')
        self.assertTrue(admin.check_password('env-set-p4ssword'))
        self.assertFalse(admin.check_password('demo1234'))
