import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from core.models import User, Student, Course, Enrollment, Grade


class Command(BaseCommand):
    help = 'Seed database with realistic sample data for demonstration'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...\n')

        # ── Create Users ──
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'System',
                'last_name': 'Administrator',
                'email': 'admin@sms.edu',
                'role': 'admin',
                'department': 'Administration',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('demo1234')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Created admin user'))

        teacher1, created = User.objects.get_or_create(
            username='teacher',
            defaults={
                'first_name': 'James',
                'last_name': 'Wilson',
                'email': 'j.wilson@sms.edu',
                'role': 'teacher',
                'department': 'Computer Science',
            }
        )
        if created:
            teacher1.set_password('demo1234')
            teacher1.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Created teacher user (j.wilson)'))

        teacher2, created = User.objects.get_or_create(
            username='prof.martinez',
            defaults={
                'first_name': 'Elena',
                'last_name': 'Martinez',
                'email': 'e.martinez@sms.edu',
                'role': 'teacher',
                'department': 'Mathematics',
            }
        )
        if created:
            teacher2.set_password('demo1234')
            teacher2.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Created teacher user (e.martinez)'))

        teacher3, created = User.objects.get_or_create(
            username='prof.chen',
            defaults={
                'first_name': 'Wei',
                'last_name': 'Chen',
                'email': 'w.chen@sms.edu',
                'role': 'teacher',
                'department': 'Physics',
            }
        )
        if created:
            teacher3.set_password('demo1234')
            teacher3.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Created teacher user (w.chen)'))

        teachers = [teacher1, teacher2, teacher3]

        # ── Create Courses ──
        courses_data = [
            {'course_name': 'Introduction to Computer Science', 'course_code': 'CS101', 'semester': 'Fall', 'credits': 6, 'description': 'Fundamental concepts of computer science including algorithms, data structures, and programming basics.', 'teacher': teacher1, 'max_students': 40},
            {'course_name': 'Database Systems', 'course_code': 'CS201', 'semester': 'Spring', 'credits': 5, 'description': 'Design and implementation of relational databases, SQL, normalization, and transaction management.', 'teacher': teacher1, 'max_students': 35},
            {'course_name': 'Web Development', 'course_code': 'CS301', 'semester': 'Fall', 'credits': 5, 'description': 'Modern web technologies including HTML5, CSS3, JavaScript, and server-side programming.', 'teacher': teacher1, 'max_students': 30},
            {'course_name': 'Calculus I', 'course_code': 'MATH101', 'semester': 'Fall', 'credits': 6, 'description': 'Limits, derivatives, and integrals of single-variable functions.', 'teacher': teacher2, 'max_students': 45},
            {'course_name': 'Linear Algebra', 'course_code': 'MATH201', 'semester': 'Spring', 'credits': 5, 'description': 'Vectors, matrices, linear transformations, eigenvalues and eigenvectors.', 'teacher': teacher2, 'max_students': 40},
            {'course_name': 'Physics I — Mechanics', 'course_code': 'PHY101', 'semester': 'Fall', 'credits': 6, 'description': 'Classical mechanics, Newton\'s laws, energy, momentum, and rotational motion.', 'teacher': teacher3, 'max_students': 35},
            {'course_name': 'Data Structures & Algorithms', 'course_code': 'CS202', 'semester': 'Spring', 'credits': 6, 'description': 'Advanced data structures, algorithm design, complexity analysis, sorting and searching.', 'teacher': teacher1, 'max_students': 30},
            {'course_name': 'Statistics & Probability', 'course_code': 'MATH301', 'semester': 'Summer', 'credits': 4, 'description': 'Probability theory, random variables, statistical inference, and hypothesis testing.', 'teacher': teacher2, 'max_students': 35},
        ]

        courses = []
        for cd in courses_data:
            course, created = Course.objects.get_or_create(
                course_code=cd['course_code'],
                defaults=cd
            )
            courses.append(course)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created course: {course.course_code}'))

        # ── Create Students ──
        students_data = [
            {'first_name': 'Alexander', 'last_name': 'Kowalski', 'email': 'a.kowalski@student.edu', 'student_number': 'STU-2024-001', 'study_program': 'Computer Science', 'phone': '+48 512 345 678'},
            {'first_name': 'Maria', 'last_name': 'Nowak', 'email': 'm.nowak@student.edu', 'student_number': 'STU-2024-002', 'study_program': 'Computer Science', 'phone': '+48 523 456 789'},
            {'first_name': 'Jan', 'last_name': 'Wiśniewski', 'email': 'j.wisniewski@student.edu', 'student_number': 'STU-2024-003', 'study_program': 'Mathematics', 'phone': '+48 534 567 890'},
            {'first_name': 'Anna', 'last_name': 'Wójcik', 'email': 'a.wojcik@student.edu', 'student_number': 'STU-2024-004', 'study_program': 'Physics', 'phone': '+48 545 678 901'},
            {'first_name': 'Piotr', 'last_name': 'Kamiński', 'email': 'p.kaminski@student.edu', 'student_number': 'STU-2024-005', 'study_program': 'Computer Science', 'phone': '+48 556 789 012'},
            {'first_name': 'Katarzyna', 'last_name': 'Lewandowska', 'email': 'k.lewandowska@student.edu', 'student_number': 'STU-2024-006', 'study_program': 'Mathematics', 'phone': '+48 567 890 123'},
            {'first_name': 'Tomasz', 'last_name': 'Zieliński', 'email': 't.zielinski@student.edu', 'student_number': 'STU-2024-007', 'study_program': 'Computer Science', 'phone': '+48 578 901 234'},
            {'first_name': 'Magdalena', 'last_name': 'Szymańska', 'email': 'm.szymanska@student.edu', 'student_number': 'STU-2024-008', 'study_program': 'Physics', 'phone': '+48 589 012 345'},
            {'first_name': 'Michał', 'last_name': 'Woźniak', 'email': 'm.wozniak@student.edu', 'student_number': 'STU-2024-009', 'study_program': 'Computer Science', 'phone': '+48 590 123 456'},
            {'first_name': 'Agnieszka', 'last_name': 'Dąbrowska', 'email': 'a.dabrowska@student.edu', 'student_number': 'STU-2024-010', 'study_program': 'Mathematics', 'phone': '+48 601 234 567'},
            {'first_name': 'Krzysztof', 'last_name': 'Kozłowski', 'email': 'k.kozlowski@student.edu', 'student_number': 'STU-2024-011', 'study_program': 'Computer Science', 'phone': '+48 612 345 678'},
            {'first_name': 'Monika', 'last_name': 'Jankowska', 'email': 'm.jankowska@student.edu', 'student_number': 'STU-2024-012', 'study_program': 'Physics', 'phone': '+48 623 456 789'},
            {'first_name': 'Adam', 'last_name': 'Mazur', 'email': 'a.mazur@student.edu', 'student_number': 'STU-2025-001', 'study_program': 'Computer Science', 'phone': '+48 634 567 890'},
            {'first_name': 'Ewa', 'last_name': 'Krawczyk', 'email': 'e.krawczyk@student.edu', 'student_number': 'STU-2025-002', 'study_program': 'Mathematics', 'phone': '+48 645 678 901'},
            {'first_name': 'Łukasz', 'last_name': 'Piotrowicz', 'email': 'l.piotrowicz@student.edu', 'student_number': 'STU-2025-003', 'study_program': 'Computer Science', 'phone': '+48 656 789 012'},
            {'first_name': 'Natalia', 'last_name': 'Grabowska', 'email': 'n.grabowska@student.edu', 'student_number': 'STU-2025-004', 'study_program': 'Physics', 'phone': '+48 667 890 123'},
            {'first_name': 'Paweł', 'last_name': 'Pawlak', 'email': 'p.pawlak@student.edu', 'student_number': 'STU-2025-005', 'study_program': 'Computer Science', 'phone': '+48 678 901 234'},
            {'first_name': 'Joanna', 'last_name': 'Michalska', 'email': 'j.michalska@student.edu', 'student_number': 'STU-2025-006', 'study_program': 'Mathematics', 'phone': '+48 689 012 345'},
            {'first_name': 'Daniel', 'last_name': 'Król', 'email': 'd.krol@student.edu', 'student_number': 'STU-2025-007', 'study_program': 'Computer Science', 'phone': '+48 690 123 456'},
            {'first_name': 'Aleksandra', 'last_name': 'Wieczorek', 'email': 'a.wieczorek@student.edu', 'student_number': 'STU-2025-008', 'study_program': 'Physics', 'phone': '+48 701 234 567'},
            {'first_name': 'Marcin', 'last_name': 'Jabłoński', 'email': 'm.jablonski@student.edu', 'student_number': 'STU-2025-009', 'study_program': 'Mathematics', 'phone': '+48 712 345 678'},
            {'first_name': 'Karolina', 'last_name': 'Stępień', 'email': 'k.stepien@student.edu', 'student_number': 'STU-2025-010', 'study_program': 'Computer Science', 'phone': '+48 723 456 789'},
            {'first_name': 'Robert', 'last_name': 'Adamczyk', 'email': 'r.adamczyk@student.edu', 'student_number': 'STU-2025-011', 'study_program': 'Physics', 'phone': '+48 734 567 890'},
            {'first_name': 'Paulina', 'last_name': 'Dudek', 'email': 'p.dudek@student.edu', 'student_number': 'STU-2025-012', 'study_program': 'Computer Science', 'phone': '+48 745 678 901'},
            {'first_name': 'Jakub', 'last_name': 'Zawadzki', 'email': 'j.zawadzki@student.edu', 'student_number': 'STU-2025-013', 'study_program': 'Mathematics', 'phone': '+48 756 789 012'},
        ]

        students = []
        base_date = date(2024, 9, 1)
        for i, sd in enumerate(students_data):
            enroll_date = base_date + timedelta(days=random.randint(0, 365))
            dob = date(random.randint(1998, 2005), random.randint(1, 12), random.randint(1, 28))
            student, created = Student.objects.get_or_create(
                student_number=sd['student_number'],
                defaults={
                    **sd,
                    'date_enrolled': enroll_date,
                    'date_of_birth': dob,
                    'address': f'ul. Akademicka {random.randint(1, 100)}, Warsaw, Poland',
                    'is_active': True,
                }
            )
            students.append(student)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created student: {student.full_name}'))

        # ── Create Enrollments ──
        enrollment_count = 0
        for student in students:
            # Each student enrolls in 2-5 courses
            num_courses = random.randint(2, min(5, len(courses)))
            selected_courses = random.sample(courses, num_courses)
            for course in selected_courses:
                status = random.choice(['active', 'active', 'active', 'completed', 'completed'])
                enrollment, created = Enrollment.objects.get_or_create(
                    student=student,
                    course=course,
                    defaults={'status': status}
                )
                if created:
                    enrollment_count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {enrollment_count} enrollments'))

        # ── Create Grades ──
        grade_count = 0
        completed_enrollments = Enrollment.objects.filter(status='completed')
        active_enrollments = Enrollment.objects.filter(status='active')

        # All completed enrollments get grades
        for enrollment in completed_enrollments:
            if not hasattr(enrollment, 'grade') or not Grade.objects.filter(enrollment=enrollment).exists():
                grade_value = round(random.uniform(2.0, 5.0), 1)
                # Clamp to valid range and round to nearest 0.5
                grade_value = round(grade_value * 2) / 2
                grade_value = max(2.0, min(5.0, grade_value))

                comments_pool = [
                    'Good work throughout the semester.',
                    'Excellent performance on the final exam.',
                    'Needs improvement in practical assignments.',
                    'Strong analytical skills demonstrated.',
                    'Consistent participation in class discussions.',
                    'Outstanding project work.',
                    'Satisfactory overall performance.',
                    '',
                ]
                Grade.objects.create(
                    enrollment=enrollment,
                    grade_value=grade_value,
                    comments=random.choice(comments_pool),
                )
                grade_count += 1

        # Some active enrollments also have grades (midterm)
        for enrollment in active_enrollments[:len(active_enrollments) // 3]:
            if not Grade.objects.filter(enrollment=enrollment).exists():
                grade_value = round(random.uniform(2.5, 5.0), 1)
                grade_value = round(grade_value * 2) / 2
                grade_value = max(2.0, min(5.0, grade_value))
                Grade.objects.create(
                    enrollment=enrollment,
                    grade_value=grade_value,
                    comments='Midterm assessment.',
                )
                grade_count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {grade_count} grades'))

        self.stdout.write(self.style.SUCCESS('\n✅ Database seeded successfully!'))
        self.stdout.write(f'\n  Login credentials:')
        self.stdout.write(f'  Admin:   username=admin       password=demo1234')
        self.stdout.write(f'  Teacher: username=teacher      password=demo1234')
