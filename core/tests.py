import json
import os
import re
from datetime import date
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.conf import settings
from django.db import connection
from django.test import TestCase, Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext

from sms_project.settings import database_config

from core.forms import GradeForm
from core.models import (
    User, Student, Course, Enrollment, Grade, Attendance,
    weighted_average, weighted_average_qs,
)
from core.templatetags.sms_extras import avatar_tone, initials


class AvatarHelperTests(TestCase):
    def test_two_word_names_use_first_and_last_initial(self):
        self.assertEqual(initials('Anna Kowalska'), 'AK')
        self.assertEqual(initials('Wei Chen'), 'WC')

    def test_single_word_uses_the_first_two_letters(self):
        self.assertEqual(initials('Madonna'), 'MA')
        self.assertEqual(initials(''), '?')

    def test_avatar_tone_is_stable_for_the_same_name(self):
        self.assertEqual(avatar_tone('Ola Kowalska'), avatar_tone('Ola Kowalska'))
        self.assertIn(avatar_tone('Ola Kowalska'), range(6))


class CustomDomainTests(TestCase):
    def test_apex_adds_www(self):
        from sms_project.settings import hosts_for_custom_domain
        self.assertEqual(
            hosts_for_custom_domain('thesms.me'),
            ['thesms.me', 'www.thesms.me'],
        )

    def test_www_adds_apex(self):
        from sms_project.settings import hosts_for_custom_domain
        self.assertEqual(
            hosts_for_custom_domain('https://www.thesms.me/'),
            ['thesms.me', 'www.thesms.me'],
        )

    def test_https_origins_skip_localhost(self):
        from sms_project.settings import https_origins_from_hosts
        self.assertEqual(
            https_origins_from_hosts(['localhost', 'thesms.me']),
            ['https://thesms.me'],
        )


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
        # 422, not 200: Turbo discards a 200 answer to a form POST, and the
        # rejection notice would never reach the screen.
        self.assertEqual(response.status_code, 422)
        self.assertContains(response, 'Invalid username or password', status_code=422)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_teacher_can_open_dashboard(self):
        self.client.login(username='teacher', password='pass12345')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_login_does_not_offer_self_service_password_reset(self):
        page = self.client.get(reverse('login'))
        self.assertNotContains(page, 'Forgot your password')
        self.assertNotContains(page, '/accounts/password_reset/')
        self.assertContains(
            page,
            'Accounts and passwords are issued by an administrator',
        )

    def test_password_reset_routes_are_absent(self):
        self.assertEqual(self.client.get('/accounts/password_reset/').status_code, 404)
        self.assertEqual(self.client.get('/accounts/password_reset/done/').status_code, 404)


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

    def test_html_dashboard_stays_within_a_query_budget(self):
        """KPI + charts used to load every Grade row; keep this a handful of aggregates."""
        self.client.login(username='admin', password='pass12345')
        self.client.get(reverse('dashboard'))
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(captured), 18,
            'Dashboard issued %d queries:\n%s' % (
                len(captured),
                '\n'.join(q['sql'] for q in captured),
            ),
        )




class WeightedGradeTests(TestCase):
    """A course mark is built from components that do not count equally."""

    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            username='wg-teacher', password='pass12345', role='teacher',
        )
        self.course = Course.objects.create(
            course_name='Databases', course_code='WG101', semester='Fall',
            credits=5, teacher=self.teacher, max_students=30,
        )
        self.student = Student.objects.create(
            first_name='Ola', last_name='Nowak', email='ola.wg@example.com',
            student_number='S-WG-1', study_program='Computer Science',
            date_enrolled=date(2024, 9, 1),
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, course=self.course,
        )
        self.client.login(username='wg-teacher', password='pass12345')

    def test_one_enrollment_now_holds_several_components(self):
        Grade.objects.create(enrollment=self.enrollment, kind='midterm',
                             weight=40, grade_value=Decimal('3.0'))
        Grade.objects.create(enrollment=self.enrollment, kind='final',
                             weight=60, grade_value=Decimal('5.0'))

        self.assertEqual(self.enrollment.grades.count(), 2)

    def test_course_mark_is_weighted_not_a_plain_mean(self):
        Grade.objects.create(enrollment=self.enrollment, kind='midterm',
                             weight=40, grade_value=Decimal('3.0'))
        Grade.objects.create(enrollment=self.enrollment, kind='final',
                             weight=60, grade_value=Decimal('5.0'))

        # Plain mean would be 4.00; weighted is 0.4*3 + 0.6*5 = 4.20.
        self.assertEqual(self.enrollment.final_grade, Decimal('4.20'))
        self.assertEqual(self.enrollment.final_letter, 'B')

    def test_sql_weighted_average_matches_python(self):
        Grade.objects.create(enrollment=self.enrollment, kind='midterm',
                             weight=40, grade_value=Decimal('3.0'))
        Grade.objects.create(enrollment=self.enrollment, kind='final',
                             weight=60, grade_value=Decimal('5.0'))
        python = weighted_average(self.enrollment.grades.all())
        sql = weighted_average_qs(Grade.objects.filter(enrollment=self.enrollment))
        self.assertEqual(python, Decimal('4.20'))
        self.assertEqual(sql, python)
        self.assertIsNone(weighted_average_qs(Grade.objects.none()))

    def test_an_ungraded_enrollment_has_no_mark(self):
        self.assertIsNone(self.enrollment.final_grade)
        self.assertIsNone(self.enrollment.final_letter)

    def test_student_average_matches_the_list_annotation(self):
        Grade.objects.create(enrollment=self.enrollment, kind='midterm',
                             weight=25, grade_value=Decimal('2.0'))
        Grade.objects.create(enrollment=self.enrollment, kind='final',
                             weight=75, grade_value=Decimal('4.0'))

        # 0.25*2 + 0.75*4 = 3.50
        self.assertEqual(self.student.average_grade, Decimal('3.50'))

        response = self.client.get(reverse('student_list'))
        row = response.context['page_obj'].object_list[0]
        self.assertAlmostEqual(
            float(row.annotated_average_grade), float(self.student.average_grade),
            places=2,
        )

    def test_components_cannot_exceed_a_whole_course(self):
        Grade.objects.create(enrollment=self.enrollment, kind='midterm',
                             weight=70, grade_value=Decimal('4.0'))

        form = GradeForm(
            {'enrollment': self.enrollment.pk, 'kind': 'final', 'weight': 40,
             'grade_value': '5.0', 'comments': ''},
            user=self.teacher,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('at most 30%', ' '.join(form.errors['__all__']))

    def test_editing_a_component_does_not_count_itself_twice(self):
        midterm = Grade.objects.create(
            enrollment=self.enrollment, kind='midterm', weight=70,
            grade_value=Decimal('4.0'),
        )

        form = GradeForm(
            {'enrollment': self.enrollment.pk, 'kind': 'midterm', 'weight': 90,
             'grade_value': '4.0', 'comments': ''},
            instance=midterm, user=self.teacher,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_every_enrollment_stays_selectable_for_a_second_component(self):
        Grade.objects.create(enrollment=self.enrollment, kind='midterm',
                             weight=50, grade_value=Decimal('4.0'))

        form = GradeForm(user=self.teacher)
        self.assertIn(self.enrollment, form.fields['enrollment'].queryset)

    def test_the_grade_list_renders_components_and_the_course_mark(self):
        Grade.objects.create(enrollment=self.enrollment, kind='midterm',
                             weight=40, grade_value=Decimal('3.0'))
        Grade.objects.create(enrollment=self.enrollment, kind='final',
                             weight=60, grade_value=Decimal('5.0'))

        response = self.client.get(reverse('grade_list'))
        self.assertContains(response, 'Midterm')
        self.assertContains(response, 'Final exam')
        self.assertContains(response, '4.20')

    def test_csv_export_carries_the_component_and_the_mark(self):
        Grade.objects.create(enrollment=self.enrollment, kind='midterm',
                             weight=40, grade_value=Decimal('3.0'))
        Grade.objects.create(enrollment=self.enrollment, kind='final',
                             weight=60, grade_value=Decimal('5.0'))

        body = self.client.get(reverse('export_grades_csv')).content.decode('utf-8-sig')
        self.assertIn('Component', body)
        self.assertIn('Course Mark', body)
        self.assertIn('Midterm', body)
        self.assertIn('4.20', body)


class BulkAttendanceTests(TestCase):
    """One screen marks a whole group; the per-record form stays for fixes."""

    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            username='ba-teacher', password='pass12345', role='teacher',
        )
        self.colleague = User.objects.create_user(
            username='ba-colleague', password='pass12345', role='teacher',
        )
        self.course = Course.objects.create(
            course_name='Databases', course_code='BA101', semester='Fall',
            credits=5, teacher=self.teacher, max_students=30,
        )
        self.foreign_course = Course.objects.create(
            course_name='Physics', course_code='BA999', semester='Fall',
            credits=5, teacher=self.colleague, max_students=30,
        )

        self.enrollments = []
        for i in range(3):
            student = Student.objects.create(
                first_name=f'Stud{i}', last_name='Test',
                email=f'ba{i}@example.com', student_number=f'S-BA-{i}',
                study_program='Computer Science', date_enrolled=date(2024, 9, 1),
            )
            self.enrollments.append(
                Enrollment.objects.create(student=student, course=self.course)
            )

        self.day = date(2025, 3, 12)
        self.client.login(username='ba-teacher', password='pass12345')

    def _post(self, **statuses):
        payload = {'course': self.course.pk, 'date': self.day.isoformat()}
        payload.update(statuses)
        return self.client.post(reverse('attendance_bulk'), payload)

    def test_the_whole_group_is_saved_in_one_request(self):
        response = self._post(**{
            f'status_{self.enrollments[0].pk}': 'present',
            f'status_{self.enrollments[1].pk}': 'absent',
            f'status_{self.enrollments[2].pk}': 'late',
        })
        self.assertEqual(response.status_code, 302)

        records = Attendance.objects.filter(date=self.day)
        self.assertEqual(records.count(), 3)
        self.assertEqual(
            sorted(records.values_list('status', flat=True)),
            ['absent', 'late', 'present'],
        )

    def test_saving_twice_updates_instead_of_failing_on_the_unique_rule(self):
        self._post(**{f'status_{self.enrollments[0].pk}': 'present'})
        self._post(**{f'status_{self.enrollments[0].pk}': 'absent'})

        record = Attendance.objects.get(
            enrollment=self.enrollments[0], date=self.day
        )
        self.assertEqual(record.status, 'absent')
        self.assertEqual(Attendance.objects.filter(date=self.day).count(), 1)

    def test_not_marked_removes_an_existing_record(self):
        self._post(**{f'status_{self.enrollments[0].pk}': 'present'})
        self.assertTrue(Attendance.objects.filter(date=self.day).exists())

        self._post(**{f'status_{self.enrollments[0].pk}': 'none'})
        self.assertFalse(Attendance.objects.filter(date=self.day).exists())

    def test_the_roster_comes_back_pre_selected(self):
        self._post(**{f'status_{self.enrollments[1].pk}': 'late'})

        response = self.client.get(
            reverse('attendance_bulk'),
            {'course': self.course.pk, 'date': self.day.isoformat()},
        )
        by_enrollment = {
            row['enrollment'].pk: row['status'] for row in response.context['roster']
        }
        self.assertEqual(by_enrollment[self.enrollments[1].pk], 'late')
        self.assertEqual(by_enrollment[self.enrollments[0].pk], '')

    def test_only_active_enrollments_are_listed(self):
        Enrollment.objects.filter(pk=self.enrollments[2].pk).update(status='dropped')

        response = self.client.get(
            reverse('attendance_bulk'), {'course': self.course.pk}
        )
        listed = {row['enrollment'].pk for row in response.context['roster']}
        self.assertNotIn(self.enrollments[2].pk, listed)
        self.assertEqual(len(listed), 2)

    def test_a_colleagues_course_is_not_reachable(self):
        response = self.client.get(
            reverse('attendance_bulk'), {'course': self.foreign_course.pk}
        )
        self.assertEqual(response.status_code, 404)

    def test_a_colleagues_course_cannot_be_marked_either(self):
        response = self.client.post(reverse('attendance_bulk'), {
            'course': self.foreign_course.pk, 'date': self.day.isoformat(),
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Attendance.objects.count(), 0)

    def test_an_unreadable_date_falls_back_to_today_instead_of_crashing(self):
        response = self.client.get(
            reverse('attendance_bulk'),
            {'course': self.course.pk, 'date': 'not-a-date'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_date'], timezone.localdate())

    def test_admin_can_mark_any_course(self):
        User.objects.create_user(username='ba-admin', password='pass12345', role='admin')
        self.client.login(username='ba-admin', password='pass12345')

        response = self.client.post(reverse('attendance_bulk'), {
            'course': self.foreign_course.pk, 'date': self.day.isoformat(),
        })
        self.assertEqual(response.status_code, 302)



class DemoAccountTests(TestCase):
    def test_seed_demo_creates_staff_who_can_sign_in(self):
        # Clear the override so the result does not depend on the developer's .env.
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('DJANGO_ADMIN_PASSWORD', None)
            call_command('seed_demo', stdout=StringIO())
        self.assertTrue(User.objects.filter(username='admin', role='admin').exists())
        self.assertTrue(self.client.login(username='admin', password='demo1234'))

    def test_seed_demo_replaces_the_published_admin_password(self):
        """In production DJANGO_ADMIN_PASSWORD must retire the documented one."""
        with mock.patch.dict(os.environ, {'DJANGO_ADMIN_PASSWORD': 'not-the-demo-one'}):
            call_command('seed_demo', stdout=StringIO())
        self.assertFalse(self.client.login(username='admin', password='demo1234'))
        self.assertTrue(self.client.login(username='admin', password='not-the-demo-one'))


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
            'enrollment': self.enrollment.pk, 'kind': 'final', 'weight': '100',
            'grade_value': '4.5', 'comments': '',
        })

        grade = Grade.objects.get(enrollment=self.enrollment)
        self.assertEqual(grade.assigned_by, self.teacher)

    def test_editing_a_grade_records_the_last_editor(self):
        grade = Grade.objects.create(
            enrollment=self.enrollment, grade_value=3.0, assigned_by=self.teacher,
        )

        self.client.login(username='admin', password='pass12345')
        self.client.post(reverse('grade_update', args=[grade.pk]), {
            'enrollment': self.enrollment.pk, 'kind': 'final', 'weight': '100',
            'grade_value': '5.0', 'comments': 'corrected',
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
        self.assertContains(response, 'lang-switch')
        self.assertContains(response, 'is-active')

    def test_stored_catalog_values_follow_the_active_language(self):
        teacher = User.objects.get(username='teacher')
        student = Student.objects.create(
            first_name='Ola', last_name='Nowak', email='ola.nowak@example.com',
            student_number='S-PL-1', study_program='Computer Science',
            date_enrolled='2024-09-01',
        )
        Course.objects.create(
            course_name='Web Development', course_code='CS301',
            semester='Fall', credits=5, teacher=teacher,
        )
        Enrollment.objects.create(
            student=student,
            course=Course.objects.get(course_code='CS301'),
        )

        self.client.post(reverse('set_language'), {'language': 'pl', 'next': '/'})

        dashboard = self.client.get(reverse('dashboard'))
        self.assertContains(dashboard, 'Informatyka')
        self.assertContains(dashboard, 'Kierunek')
        self.assertContains(dashboard, 'Stan')
        self.assertNotContains(dashboard, 'Computer Science')

        courses = self.client.get(reverse('course_list'))
        self.assertContains(courses, 'Tworzenie aplikacji webowych')
        self.assertContains(courses, 'Jesienny')
        self.assertNotContains(courses, '>Fall<')
        self.assertNotContains(courses, 'Web Development')

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
        self.assertEqual(response.status_code, 422)
        self.assertContains(response, 'is full', status_code=422)
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
        self.assertContains(response, 'already enrolled', status_code=422)


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

    def test_people_tables_use_initial_avatars(self):
        self.client.login(username='admin', password='pass12345')
        response = self.client.get(reverse('student_list'))
        self.assertContains(response, 'person-avatar')
        self.assertContains(response, '>OK<')
        self.assertContains(response, 'lang-switch')
        self.assertContains(response, 'images/logo.svg')
        self.assertNotContains(response, 'dropdown-toggle')

        login_page = Client().get(reverse('login'))
        self.assertContains(login_page, 'images/logo.svg')

    def test_chrome_is_wired_for_fast_turbo_navigation(self):
        """Scripts stay in <head>; CSV must not be prefetched as HTML."""
        self.client.login(username='admin', password='pass12345')
        page = self.client.get(reverse('dashboard'))
        html = page.content.decode()
        head, body = html.split('</head>', 1)
        self.assertIn('chart.umd.min.js', head)
        self.assertIn('js/main.js', head)
        self.assertNotIn('bootstrap.bundle', html)
        self.assertContains(page, 'data-turbo-permanent')
        self.assertContains(page, 'data-turbo="false"')
        self.assertContains(page, 'data-turbo-prefetch="false"')
        self.assertNotIn('chart.umd.min.js', body)
        self.assertNotIn('js/main.js', body)

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
            reverse('teacher_list'),
            reverse('teacher_create'),
            reverse('teacher_update', args=[self.teacher.pk]),
            reverse('teacher_delete', args=[self.teacher.pk]),
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
            reverse('teacher_list'),
            reverse('teacher_create'),
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

    def test_create_teacher_and_they_can_sign_in(self):
        response = self.client.post(reverse('teacher_create'), {
            'username': 'newlecturer',
            'first_name': 'Ewa',
            'last_name': 'Nowak',
            'email': 'ewa.nowak@sms.edu',
            'department': 'Computer Science',
            'password1': 'BrandNewPass!9876',
            'password2': 'BrandNewPass!9876',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        teacher = User.objects.get(username='newlecturer')
        self.assertEqual(teacher.role, 'teacher')
        self.assertTrue(teacher.check_password('BrandNewPass!9876'))

        self.client.logout()
        self.assertTrue(self.client.login(
            username='newlecturer', password='BrandNewPass!9876'
        ))

    def test_admin_can_set_a_new_teacher_password(self):
        response = self.client.post(
            reverse('teacher_update', args=[self.teacher.pk]),
            {
                'first_name': 'Jane',
                'last_name': 'Wilson',
                'email': 'j.wilson@sms.edu',
                'department': 'Computer Science',
                'password1': 'ResetPass!4321',
                'password2': 'ResetPass!4321',
                'is_active': True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password('ResetPass!4321'))
        self.assertFalse(self.teacher.check_password('pass12345'))

    def test_teacher_list_does_not_show_administrators(self):
        page = self.client.get(reverse('teacher_list'))
        listed = [teacher.username for teacher in page.context['teachers']]
        self.assertIn(self.teacher.username, listed)
        self.assertNotIn(self.admin.username, listed)


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


class RegressionTests(TestCase):
    """Guards for bugs that were found by walking the running site."""

    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            username='reg-teacher', password='pass12345', role='teacher'
        )
        self.colleague = User.objects.create_user(
            username='reg-colleague', password='pass12345', role='teacher'
        )

        # The teacher runs two courses; the colleague runs a third.
        self.course_a = Course.objects.create(
            course_name='Course A', course_code='REGA', semester='Fall',
            credits=5, teacher=self.teacher, max_students=30,
        )
        self.course_b = Course.objects.create(
            course_name='Course B', course_code='REGB', semester='Fall',
            credits=5, teacher=self.teacher, max_students=30,
        )
        self.foreign_course = Course.objects.create(
            course_name='Course C', course_code='REGC', semester='Fall',
            credits=5, teacher=self.colleague, max_students=30,
        )

        # One student sits in all three courses.
        self.student = Student.objects.create(
            first_name='Ola', last_name='Nowak', email='ola@example.com',
            student_number='S-REG-1', study_program='Computer Science',
            date_enrolled='2024-09-01',
        )
        self.enr_a = Enrollment.objects.create(student=self.student, course=self.course_a)
        self.enr_b = Enrollment.objects.create(student=self.student, course=self.course_b)
        self.enr_foreign = Enrollment.objects.create(
            student=self.student, course=self.foreign_course
        )

        Grade.objects.create(enrollment=self.enr_a, grade_value=Decimal('3.0'))
        Grade.objects.create(enrollment=self.enr_foreign, grade_value=Decimal('5.0'))

        self.client.login(username='reg-teacher', password='pass12345')

    def test_student_detail_summary_excludes_other_teachers_courses(self):
        """The summary card must not aggregate over a colleague's courses."""
        response = self.client.get(reverse('student_detail', args=[self.student.pk]))

        # Two of the three enrolments belong to this teacher.
        self.assertEqual(response.context['course_count'], 2)
        # Only the 3.0 from REGA counts; the colleague's 5.0 must not leak in.
        self.assertEqual(response.context['average_grade'], Decimal('3.00'))
        # The unscoped model properties would have said 3 courses / 4.0.
        self.assertEqual(self.student.enrollment_count, 3)
        self.assertEqual(self.student.average_grade, 4.0)

    def test_admin_student_detail_still_sees_the_whole_record(self):
        User.objects.create_user(username='reg-admin', password='pass12345', role='admin')
        self.client.login(username='reg-admin', password='pass12345')

        response = self.client.get(reverse('student_detail', args=[self.student.pk]))

        self.assertEqual(response.context['course_count'], 3)
        self.assertEqual(response.context['average_grade'], Decimal('4.00'))

    def test_program_chart_total_matches_the_student_kpi(self):
        """Joining through enrolments used to count a student once per course."""
        response = self.client.get(reverse('dashboard'))

        program_data = json.loads(response.context['program_data'])

        self.assertEqual(response.context['total_students'], 1)
        self.assertEqual(sum(program_data), 1)

    def test_course_detail_reports_active_and_total_separately(self):
        """The roster header and the capacity card must not contradict."""
        Enrollment.objects.filter(pk=self.enr_a.pk).update(status='dropped')

        response = self.client.get(reverse('course_detail', args=[self.course_a.pk]))

        self.assertEqual(response.context['course'].enrolled_count, 0)
        self.assertEqual(response.context['enrollments'].count(), 1)
        self.assertContains(response, '0 active of 1 enrolled')

    def test_main_js_is_wrapped_against_double_evaluation(self):
        """Keep declarations inside an IIFE so a second include cannot clash.

        Chart.js and main.js now live in <head> (Turbo does not re-run those),
        but the run-once guard still stops duplicate document listeners.
        """
        source = (settings.BASE_DIR / 'static' / 'js' / 'main.js').read_text(encoding='utf-8')

        # Strip the leading block comments to find the first real statement.
        code = re.sub(r'/\*.*?\*/', '', source, flags=re.S).strip()

        self.assertTrue(
            code.startswith('(function ()'),
            'main.js must open with an IIFE so its declarations stay local.',
        )
        self.assertTrue(
            code.endswith('})();'),
            'main.js must close the IIFE that wraps it.',
        )
        self.assertIn(
            'window.__smsAppLoaded', code,
            'main.js needs a run-once guard so document listeners bind once.',
        )

    def test_render_build_forces_threaded_gunicorn(self):
        """Dashboard start command may lag render.yaml; the build patches it."""
        import importlib.util
        from pathlib import Path
        import tempfile

        build = (settings.BASE_DIR / 'build.sh').read_text(encoding='utf-8')
        self.assertIn('patch_gunicorn_for_render', build)
        conf = (settings.BASE_DIR / 'gunicorn.conf.py').read_text(encoding='utf-8')
        self.assertIn('threads = 8', conf)
        self.assertIn('workers = 1', conf)

        spec = importlib.util.spec_from_file_location(
            'patch_gunicorn_for_render',
            settings.BASE_DIR / 'scripts' / 'patch_gunicorn_for_render.py',
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with tempfile.TemporaryDirectory() as tmp:
            launcher = Path(tmp) / 'gunicorn'
            launcher.write_text('#!/usr/bin/env python\nprint("old")\n', encoding='utf-8')
            config = Path(tmp) / 'gunicorn.conf.py'
            config.write_text('threads = 8\n', encoding='utf-8')
            mod.patch_launcher(launcher, config)
            text = launcher.read_text(encoding='utf-8')
            self.assertIn('-c', text)
            self.assertIn('--threads', text)
            self.assertIn(str(config), text)


class DashboardScriptLoadingTests(TestCase):
    """The dashboard fills its counters and charts from a `turbo:load` handler.

    Turbo starts as soon as the document reaches readyState "interactive",
    which happens *before* deferred scripts execute. A deferred main.js
    therefore registers its listener after the event has already fired, and a
    cold load — exactly what a visitor gets right after signing in — leaves
    every counter at 0 and every chart blank.
    """

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='script-teacher', password='pass12345', role='teacher'
        )
        self.client.force_login(self.teacher)

    def test_app_javascript_is_not_deferred(self):
        html = self.client.get(reverse('dashboard')).content.decode()
        tag = re.search(r'<script[^>]*js/main[^>]*>', html)
        self.assertIsNotNone(tag, 'main.js is not loaded at all')
        self.assertNotIn('defer', tag.group(0))

    def test_template_comments_do_not_leak_into_the_page(self):
        """Django's {# #} is single-line; a wrapped one renders as text."""
        html = self.client.get(reverse('dashboard')).content.decode()
        body = html[html.index('<body'):]
        self.assertNotIn('#}', body)
        self.assertNotIn('{#', body)


class TurboFormStatusTests(TestCase):
    """An invalid submission must come back as 422, never 200.

    Turbo Drive refuses to render a 200 response to a form POST — it logs
    "Form responses must redirect to another location" and leaves the old page
    on screen. Every validation message in the application would be invisible.
    """

    FORM_VIEWS = [
        'student_create', 'course_create', 'enrollment_create',
        'grade_create', 'attendance_create', 'teacher_create',
    ]

    def setUp(self):
        self.admin = User.objects.create_user(
            username='turbo-admin', password='pass12345', role='admin'
        )

    def test_invalid_login_is_unprocessable(self):
        response = self.client.post(
            reverse('login'), {'username': 'turbo-admin', 'password': 'nope'}
        )
        self.assertEqual(response.status_code, 422)

    def test_form_pages_answer_get_with_200(self):
        self.client.force_login(self.admin)
        for name in self.FORM_VIEWS:
            with self.subTest(view=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_invalid_submissions_are_unprocessable(self):
        self.client.force_login(self.admin)
        for name in self.FORM_VIEWS:
            with self.subTest(view=name):
                response = self.client.post(reverse(name), {})
                self.assertEqual(response.status_code, 422)


class ErrorPageTests(TestCase):
    """A mistyped URL in production must not drop the visitor onto bare text."""

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['*'])
    def test_404_uses_the_branded_template(self):
        response = self.client.get('/definitely-not-a-page/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Page not found', status_code=404)
        self.assertContains(response, 'Back to the dashboard', status_code=404)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['*'])
    def test_404_is_branded_for_a_signed_in_user_too(self):
        user = User.objects.create_user(
            username='lost-teacher', password='pass12345', role='teacher'
        )
        self.client.force_login(user)
        response = self.client.get('/definitely-not-a-page/')
        self.assertContains(response, 'Page not found', status_code=404)

    def test_500_template_renders_without_a_request(self):
        """Django renders 500.html with an empty context — it must not need one."""
        from django.template.loader import get_template

        html = get_template('500.html').render({})
        self.assertIn('Something went wrong', html)


class TranslationCatalogueTests(TestCase):
    """A fuzzy or empty entry silently falls back to English on a Polish page."""

    def setUp(self):
        self.catalogue = (
            settings.BASE_DIR / 'locale' / 'pl' / 'LC_MESSAGES' / 'django.po'
        ).read_text(encoding='utf-8')

    def test_no_entry_is_marked_fuzzy(self):
        """msgfmt drops fuzzy entries, so the English string ships instead."""
        self.assertNotIn('#, fuzzy', self.catalogue)

    def test_every_message_is_translated(self):
        entries = re.findall(
            r'\nmsgid "((?:[^"\\]|\\.)+)"\nmsgstr ""\n(?!")', self.catalogue
        )
        self.assertEqual(entries, [], f'untranslated: {entries[:5]}')

    def test_the_new_pages_speak_polish(self):
        with translation.override('pl'):
            self.assertEqual(gettext('Page not found'), 'Nie znaleziono strony')
            self.assertEqual(gettext('Weight'), 'Waga')
            self.assertEqual(
                gettext('Back to the dashboard'), 'Powrót do panelu głównego'
            )


class HealthProbeTests(TestCase):
    """The probe exists to keep a suspended database awake, so it must query."""

    def test_probe_is_open_and_reports_ok(self):
        response = self.client.get(reverse('healthz'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_probe_actually_touches_the_database(self):
        with CaptureQueriesContext(connection) as queries:
            self.client.get(reverse('healthz'))
        self.assertGreaterEqual(len(queries), 1)

    def test_the_login_page_would_not_have_kept_it_awake(self):
        """Why the probe exists: /login/ renders without a single query."""
        with CaptureQueriesContext(connection) as queries:
            self.client.get(reverse('login'))
        self.assertEqual(len(queries), 0)


class DatabaseConnectionPolicyTests(TestCase):
    """Reconnecting per request costs a TCP and TLS handshake before any page."""

    def test_a_direct_postgres_host_keeps_its_connection(self):
        config = database_config(
            'postgresql://u:p@ep-x.eu-central-1.aws.neon.tech/db', debug=False
        )
        self.assertEqual(config['CONN_MAX_AGE'], 600)
        self.assertTrue(config['CONN_HEALTH_CHECKS'])
        self.assertNotIn('DISABLE_SERVER_SIDE_CURSORS', config)

    def test_a_pooled_host_keeps_it_too_but_on_the_pooler_s_terms(self):
        config = database_config(
            'postgresql://u:p@ep-x-pooler.eu-central-1.aws.neon.tech/db', debug=False
        )
        self.assertEqual(config['CONN_MAX_AGE'], 600)
        self.assertTrue(config['DISABLE_SERVER_SIDE_CURSORS'])
        self.assertIsNone(config['OPTIONS']['prepare_threshold'])

    def test_sqlite_is_left_alone(self):
        config = database_config('sqlite:///db.sqlite3', debug=True)
        self.assertEqual(config['CONN_MAX_AGE'], 0)
        self.assertFalse(config['CONN_HEALTH_CHECKS'])
        self.assertNotIn('DISABLE_SERVER_SIDE_CURSORS', config)
