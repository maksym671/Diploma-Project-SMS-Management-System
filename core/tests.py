import json
import os
import re
import urllib.error
from datetime import date
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.conf import settings
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from core.forms import GradeForm
from core.models import User, Student, Course, Enrollment, Grade, Attendance
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

    def _reset_link(self):
        """Request a reset and pull the confirmation URL out of the email."""
        self.client.post(reverse('password_reset'), {'email': 'resetme@example.com'})
        match = re.search(r'https?://[^/]+(/accounts/reset/\S+)', mail.outbox[0].body)
        self.assertIsNotNone(match, 'the email must carry a reset link')
        return match.group(1)

    def test_reset_link_sets_a_new_password_and_revokes_the_old_one(self):
        # Django redirects the raw token to a /set-password/ URL that holds the
        # token in the session, so follow it before posting the new password.
        page = self.client.get(self._reset_link(), follow=True)
        self.assertTrue(page.context['validlink'])

        response = self.client.post(page.request['PATH_INFO'], {
            'new_password1': 'BrandNewPass!9876',
            'new_password2': 'BrandNewPass!9876',
        })
        self.assertRedirects(response, reverse('password_reset_complete'))

        user = User.objects.get(username='resetme')
        self.assertTrue(user.check_password('BrandNewPass!9876'))
        self.assertFalse(user.check_password('pass12345'))

        self.assertTrue(self.client.login(
            username='resetme', password='BrandNewPass!9876'
        ))

    def test_reset_link_cannot_be_used_twice(self):
        link = self._reset_link()
        page = self.client.get(link, follow=True)
        self.client.post(page.request['PATH_INFO'], {
            'new_password1': 'BrandNewPass!9876',
            'new_password2': 'BrandNewPass!9876',
        })

        # The token is consumed once the password changes.
        second = self.client.get(link, follow=True)
        self.assertFalse(second.context['validlink'])
        self.assertContains(second, 'Invalid Link')

    def test_reset_email_follows_the_interface_language(self):
        self.client.post(reverse('set_language'), {'language': 'pl', 'next': '/'})
        self.client.post(reverse('password_reset'), {'email': 'resetme@example.com'})

        self.assertIn('hasła', mail.outbox[0].subject)
        self.assertIn('Otwórz poniższy link', mail.outbox[0].body)

    def test_reset_pages_render_for_a_signed_in_visitor(self):
        """These pages sit outside the app shell, so they must not come back blank."""
        self.client.login(username='resetme', password='pass12345')

        for url in [reverse('password_reset'), reverse('password_reset_done')]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'login-card')


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


class MailConfigurationTests(TestCase):
    """The deploy check must catch a mail setup that silently drops resets."""

    def _run_checks(self, **overrides):
        from core.checks import check_email_configuration

        with override_settings(**overrides):
            return {w.id for w in check_email_configuration(None)}

    def test_debug_deployment_is_not_nagged(self):
        self.assertEqual(self._run_checks(DEBUG=True), set())

    def test_console_backend_in_production_is_flagged(self):
        found = self._run_checks(
            DEBUG=False,
            EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
        )
        self.assertIn('mail.W001', found)

    def test_smtp_without_credentials_is_flagged(self):
        found = self._run_checks(
            DEBUG=False,
            EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
            EMAIL_HOST_USER='',
            EMAIL_HOST_PASSWORD='',
            DEFAULT_FROM_EMAIL='noreply@sms.local',
        )
        self.assertEqual(found, {'mail.W002', 'mail.W003', 'mail.W004'})

    def test_fully_configured_smtp_is_clean(self):
        found = self._run_checks(
            DEBUG=False,
            EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
            EMAIL_HOST_USER='sms@gmail.com',
            EMAIL_HOST_PASSWORD='app-password',
            DEFAULT_FROM_EMAIL='SMS <sms@gmail.com>',
        )
        self.assertEqual(found, set())


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class PasswordResetResilienceTests(TestCase):
    """A dead mail server must not turn the reset page into a 500."""

    def setUp(self):
        self.client = Client()
        User.objects.create_user(
            username='resilient', password='pass12345',
            email='resilient@example.com', role='teacher',
        )

    def test_smtp_failure_still_shows_the_confirmation_page(self):
        import smtplib

        with mock.patch(
            'django.contrib.auth.forms.PasswordResetForm.save',
            side_effect=smtplib.SMTPAuthenticationError(535, b'auth failed'),
        ):
            with self.assertLogs('core.views', level='ERROR') as captured:
                response = self.client.post(
                    reverse('password_reset'),
                    {'email': 'resilient@example.com'},
                )

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertIn('could not be delivered', '\n'.join(captured.output))

    def test_working_mail_server_is_unaffected(self):
        response = self.client.post(
            reverse('password_reset'),
            {'email': 'resilient@example.com'},
        )
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)


@override_settings(
    EMAIL_BACKEND='core.mail.BrevoAPIBackend',
    BREVO_API_KEY='test-key',
    DEFAULT_FROM_EMAIL='Student Management System <sms@example.com>',
)
class BrevoBackendTests(TestCase):
    """Delivery over HTTPS, because the host firewalls outbound SMTP."""

    def setUp(self):
        self.client = Client()
        User.objects.create_user(
            username='brevo-user', password='pass12345',
            email='brevo@example.com', role='teacher',
        )

    def _capture(self):
        """Patch urlopen and hand back the request it was given."""
        captured = {}

        class _Response:
            def read(self):
                return b'{"messageId":"1"}'

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def fake_urlopen(request, timeout=None):
            captured['request'] = request
            captured['body'] = json.loads(request.data.decode('utf-8'))
            return _Response()

        return captured, mock.patch('core.mail.urllib.request.urlopen', fake_urlopen)

    def test_reset_mail_goes_out_as_an_https_api_call(self):
        captured, patcher = self._capture()
        with patcher:
            response = self.client.post(
                reverse('password_reset'), {'email': 'brevo@example.com'}
            )

        self.assertRedirects(response, reverse('password_reset_done'))
        request = captured['request']
        self.assertEqual(request.full_url, 'https://api.brevo.com/v3/smtp/email')
        self.assertEqual(request.get_header('Api-key'), 'test-key')

    def test_the_payload_carries_sender_recipient_and_the_reset_link(self):
        captured, patcher = self._capture()
        with patcher:
            self.client.post(reverse('password_reset'), {'email': 'brevo@example.com'})

        body = captured['body']
        self.assertEqual(body['sender'],
                         {'name': 'Student Management System', 'email': 'sms@example.com'})
        self.assertEqual(body['to'], [{'email': 'brevo@example.com'}])
        self.assertIn('/accounts/reset/', body['textContent'])

    def test_a_provider_outage_does_not_become_a_500(self):
        """An unreachable provider must not surface as a server error.

        Django 6 already traps a delivery failure inside
        `PasswordResetForm.save()` and logs it, so the visitor still gets the
        ordinary confirmation page. This pins that behaviour down for this
        backend too, since the failure arrives as a URLError rather than an
        SMTP one.
        """
        def boom(request, timeout=None):
            raise urllib.error.URLError('brevo unreachable')

        with mock.patch('core.mail.urllib.request.urlopen', boom):
            with self.assertLogs('django.contrib.auth', level='ERROR') as captured:
                response = self.client.post(
                    reverse('password_reset'), {'email': 'brevo@example.com'}
                )

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertIn('Failed to send password reset email',
                      '\n'.join(captured.output))

    def test_a_missing_api_key_is_reported_not_swallowed(self):
        from core.mail import BrevoAPIBackend
        from django.core.mail import EmailMessage

        backend = BrevoAPIBackend(api_key='')
        message = EmailMessage('subject', 'body', 'a@example.com', ['b@example.com'])
        with self.assertRaises(urllib.error.URLError):
            backend.send_messages([message])

    def test_deploy_check_flags_a_missing_key(self):
        from core.checks import check_email_configuration

        with override_settings(DEBUG=False, BREVO_API_KEY=''):
            found = {w.id for w in check_email_configuration(None)}
        self.assertIn('mail.W005', found)


class DemoAccountTests(TestCase):
    def test_every_seeded_account_can_receive_a_reset_email(self):
        """An account with no e-mail address can never recover its password."""
        call_command('seed_demo', stdout=StringIO())

        without_email = list(
            User.objects.filter(email='').values_list('username', flat=True)
        )
        self.assertEqual(without_email, [])


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
        """Turbo re-runs every body script in the same global scope.

        Top-level `let`/`const` therefore threw "Identifier has already been
        declared" on the second page, which aborted the whole file. The
        declarations must stay inside an IIFE, behind a run-once guard.
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
