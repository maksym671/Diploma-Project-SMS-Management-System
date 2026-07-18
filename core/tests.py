from django.test import TestCase
from core.models import User, Student, Course, Enrollment, Grade

class CoreModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='teststudent', password='password', role='student')
        self.teacher = User.objects.create_user(username='testteacher', password='password', role='teacher')
        
        self.student = Student.objects.create(
            user=self.user,
            first_name='Ivan',
            last_name='Ivanov',
            email='ivan@example.com',
            student_number='S12345',
            study_program='Computer Science',
            date_enrolled='2024-09-01'
        )
        
        self.course = Course.objects.create(
            course_name='Math 101',
            course_code='MATH101',
            semester='Fall',
            credits=5,
            teacher=self.teacher,
            max_students=30
        )
        
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='active'
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
                    first_name='Petr', last_name='Petrov', email='petr@example.com',
                    student_number='S54321', study_program='IT', date_enrolled='2024-09-01'
                ),
                course=self.course
            ),
            grade_value=3.2
        )
        self.assertEqual(grade2.letter_grade, 'D')

    def test_student_average_grade(self):
        Grade.objects.create(enrollment=self.enrollment, grade_value=4.0)
        
        course2 = Course.objects.create(
            course_name='Physics 101', course_code='PHYS101', semester='Fall', credits=4, max_students=30
        )
        enrollment2 = Enrollment.objects.create(student=self.student, course=course2)
        Grade.objects.create(enrollment=enrollment2, grade_value=5.0)
        
        self.assertEqual(self.student.average_grade, 4.5)
