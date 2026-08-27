"""Fill the Polish catalogue with translations for the UI strings.

Run after `manage.py makemessages -l pl` to translate newly extracted strings
and clear the bogus "fuzzy" guesses gettext copies from similar messages:

    python scripts/fill_pl_translations.py
    python manage.py compilemessages -l pl

Keys and values are written in .po escaping (\\" for quotes, \\n for newlines).
"""
import re
from pathlib import Path

PO_PATH = Path(__file__).resolve().parent.parent / 'locale' / 'pl' / 'LC_MESSAGES' / 'django.po'

TRANSLATIONS = {
    # --- Flash messages / views -------------------------------------------
    'You do not have permission to access this page.': 'Nie masz uprawnień do tej strony.',
    'Welcome back, %(name)s!': 'Witaj ponownie, %(name)s!',
    'Invalid username or password.': 'Nieprawidłowa nazwa użytkownika lub hasło.',
    'You have been logged out.': 'Zostałeś wylogowany.',
    'Student \\"%(name)s\\" has been created successfully.':
        'Student \\"%(name)s\\" został pomyślnie dodany.',
    'Student \\"%(name)s\\" has been updated.': 'Dane studenta \\"%(name)s\\" zostały zaktualizowane.',
    'Student \\"%(name)s\\" has been deleted.': 'Student \\"%(name)s\\" został usunięty.',
    'Teacher \\"%(name)s\\" has been created.': 'Nauczyciel \\"%(name)s\\" został dodany.',
    'Teacher \\"%(name)s\\" has been updated.': 'Dane nauczyciela \\"%(name)s\\" zostały zaktualizowane.',
    'Teacher \\"%(name)s\\" has been deleted.': 'Nauczyciel \\"%(name)s\\" został usunięty.',
    'A staff account with this email already exists.':
        'Konto pracownika z tym adresem e-mail już istnieje.',
    'Leave blank to keep the current password.':
        'Pozostaw puste, aby zachować obecne hasło.',
    'The two passwords do not match.': 'Hasła nie są zgodne.',
    'Course \\"%(name)s\\" has been created.': 'Kurs \\"%(name)s\\" został utworzony.',
    'Course \\"%(name)s\\" has been updated.': 'Kurs \\"%(name)s\\" został zaktualizowany.',
    'Course \\"%(name)s\\" has been deleted.': 'Kurs \\"%(name)s\\" został usunięty.',
    '%(student)s enrolled in %(course)s.': '%(student)s został zapisany na %(course)s.',
    'Enrollment updated successfully.': 'Zapis został zaktualizowany.',
    'Enrollment has been removed.': 'Zapis został usunięty.',
    'Grade %(value)s assigned successfully.': 'Ocena %(value)s została wystawiona.',
    'Grade updated successfully.': 'Ocena została zaktualizowana.',
    'Grade has been deleted.': 'Ocena została usunięta.',
    'You can only edit grades for your own courses.':
        'Możesz edytować oceny tylko na swoich kursach.',
    'You can only delete grades for your own courses.':
        'Możesz usuwać oceny tylko na swoich kursach.',
    'Attendance marked for %(name)s.': 'Odnotowano obecność: %(name)s.',
    'Attendance updated.': 'Obecność została zaktualizowana.',
    'Attendance record deleted.': 'Wpis obecności został usunięty.',
    'You can only edit attendance for your own courses.':
        'Możesz edytować obecność tylko na swoich kursach.',
    'You can only delete attendance for your own courses.':
        'Możesz usuwać obecność tylko na swoich kursach.',
    'Profile updated successfully.': 'Profil został zaktualizowany.',

    # --- Forms validation --------------------------------------------------
    'This student is already enrolled in this course.':
        'Ten student jest już zapisany na ten kurs.',
    '%(code)s is full (%(seats)s seats). Increase the course capacity or drop another '
    'enrollment first.':
        '%(code)s jest pełny (%(seats)s miejsc). Zwiększ limit kursu lub usuń najpierw '
        'inny zapis.',

    # --- Page titles -------------------------------------------------------
    'Add New Student': 'Dodaj studenta',
    'Edit Student': 'Edytuj studenta',
    'Add New Course': 'Dodaj kurs',
    'Edit Course': 'Edytuj kurs',
    'New Enrollment': 'Nowy zapis',
    'Edit Enrollment': 'Edytuj zapis',
    'Assign Grade': 'Wystaw ocenę',
    'Edit Grade': 'Edytuj ocenę',
    'Mark Attendance': 'Odnotuj obecność',
    'Edit Attendance': 'Edytuj obecność',

    # --- Shared vocabulary -------------------------------------------------
    'Student': 'Student',
    'Course': 'Kurs',
    'Grade': 'Ocena',
    'Enrollment': 'Zapis',
    'Status': 'Stan',
    'Date': 'Data',
    'Actions': 'Akcje',
    'Program': 'Kierunek',
    'Semester': 'Semestr',
    'Credits': 'Punkty ECTS',
    'Teacher': 'Prowadzący',
    'Code': 'Kod',
    'Letter': 'Litera',
    'Comments': 'Komentarze',
    'Enrolled': 'Zapisano',
    'Active': 'Aktywny',
    'Inactive': 'Nieaktywny',
    'Unassigned': 'Nieprzypisany',
    'Not graded': 'Brak oceny',
    'Present': 'Obecny',
    'Absent': 'Nieobecny',
    'Late': 'Spóźniony',
    'Completed': 'Zakończony',
    'Dropped': 'Wycofany',
    'Fall': 'Jesienny',
    'Spring': 'Wiosenny',
    'Summer': 'Letni',
    'View': 'Podgląd',
    'Edit': 'Edytuj',
    'Delete': 'Usuń',
    'Remove': 'Usuń',
    'Cancel': 'Anuluj',
    'Filter': 'Filtruj',
    'Search': 'Szukaj',
    'Clear': 'Wyczyść',
    'View All': 'Zobacz wszystkie',
    'Back to List': 'Powrót do listy',
    'Please correct the errors below.': 'Popraw poniższe błędy.',
    'Please correct the error below.': 'Popraw poniższy błąd.',
    'No results matching your search': 'Brak wyników dla Twojego zapytania',

    # --- Students ----------------------------------------------------------
    'Manage student records and academic information':
        'Zarządzaj danymi studentów i informacjami akademickimi',
    'Students enrolled in your courses': 'Studenci zapisani na Twoje kursy',
    'Add Student': 'Dodaj studenta',
    'Search students...': 'Szukaj studentów...',
    'All Programs': 'Wszystkie programy',
    'All Status': 'Wszystkie statusy',
    'Student Number': 'Numer albumu',
    'Avg. Grade': 'Średnia',
    'No Students Found': 'Nie znaleziono studentów',
    'No students matching \\"%(query)s\\"': 'Brak studentów pasujących do \\"%(query)s\\"',
    'Get started by adding your first student': 'Zacznij od dodania pierwszego studenta',
    'No students are enrolled in your courses yet':
        'Na Twoje kursy nie zapisał się jeszcze żaden student',

    # --- Teachers ----------------------------------------------------------
    'Teachers': 'Nauczyciele',
    'Teacher': 'Nauczyciel',
    'Issue lecturer accounts and set their passwords':
        'Nadawaj konta wykładowcom i ustawiaj ich hasła',
    'Add Teacher': 'Dodaj nauczyciela',
    'Edit Teacher': 'Edytuj nauczyciela',
    'Search teachers...': 'Szukaj nauczycieli...',
    'No Teachers Found': 'Nie znaleziono nauczycieli',
    'No teachers matching \\"%(query)s\\"': 'Brak nauczycieli pasujących do \\"%(query)s\\"',
    'Get started by adding your first teacher': 'Zacznij od dodania pierwszego nauczyciela',
    'Update the lecturer details or set a new password.':
        'Zaktualizuj dane wykładowcy lub ustaw nowe hasło.',
    'Create the account and give the lecturer a username and password.':
        'Utwórz konto i przekaż wykładowcy nazwę użytkownika oraz hasło.',
    'New password': 'Nowe hasło',
    'Confirm password': 'Potwierdź hasło',
    'Password': 'Hasło',
    'Active account': 'Aktywne konto',
    'Update Teacher': 'Zapisz nauczyciela',
    'Create Teacher': 'Utwórz nauczyciela',
    'Delete Teacher': 'Usuń nauczyciela',
    'Are you sure you want to delete <strong>%(name)s</strong>? Their courses will stay in the catalogue, unassigned. This action cannot be undone.':
        'Czy na pewno chcesz usunąć <strong>%(name)s</strong>? Kursy pozostaną w katalogu, bez przypisanego wykładowcy. Tej operacji nie można cofnąć.',
    'This field is required.': 'To pole jest wymagane.',
    'Admin Panel': 'Panel administracyjny',
    'Department': 'Katedra',

    'Student Information': 'Informacje o studencie',
    'Study Program': 'Program studiów',
    'Date Enrolled': 'Data zapisu',
    'Email': 'E-mail',
    'Phone': 'Telefon',
    'Date of Birth': 'Data urodzenia',
    'Address': 'Adres',
    'Total Courses': 'Liczba kursów',

    # --- Staff-facing framing ----------------------------------------------
    'Staff Portal': 'Portal wykładowcy',
    'Staff sign-in — manage your courses, grades and attendance':
        'Logowanie dla pracowników — zarządzaj kursami, ocenami i obecnością',
    'Accounts and passwords are issued by an administrator. Students do not sign in here.':
        'Konta i hasła nadaje administrator. Studenci nie logują się tutaj.',

    # --- Grade components ---------------------------------------------------
    'Coursework': 'Praca semestralna',
    'Midterm': 'Kolokwium',
    'Final exam': 'Egzamin',
    'Retake': 'Poprawka',
    'Component': 'Składowa',
    'Components': 'Składowe',
    'Course Mark': 'Ocena końcowa',
    'Weight %': 'Waga %',
    '%(weight)s%% of the course': '%(weight)s%% oceny końcowej',
    'Which part of the course this mark is for':
        'Której części kursu dotyczy ta ocena',
    'How much this component counts towards the course mark':
        'Ile ta składowa waży w ocenie końcowej',
    'The components of %(code)s already use %(used)s%% of the course weight, so this '
    'one can be at most %(free)s%%.':
        'Składowe kursu %(code)s zajmują już %(used)s%% wagi, więc ta może mieć '
        'najwyżej %(free)s%%.',

    # --- Bulk attendance ----------------------------------------------------
    'Mark Class Attendance': 'Odnotuj obecność grupy',
    'Mark Class': 'Obecność grupy',
    'Single Record': 'Pojedynczy wpis',
    'All Records': 'Wszystkie wpisy',
    'Pick a course and a date, then mark the whole group at once.':
        'Wybierz kurs i datę, a następnie odnotuj całą grupę naraz.',
    'Select a course…': 'Wybierz kurs…',
    'Load Group': 'Wczytaj grupę',
    'Choose a course to begin': 'Wybierz kurs, aby zacząć',
    'The roster for that course loads here, ready to mark.':
        'Lista studentów tego kursu pojawi się tutaj, gotowa do odnotowania.',
    'No active students on this course': 'Brak aktywnych studentów na tym kursie',
    'Only active enrolments can be marked.':
        'Odnotować można tylko aktywne zapisy.',
    '%(code)s — %(count)s students': '%(code)s — %(count)s studentów',
    'Set all:': 'Ustaw wszystkim:',
    'Not marked': 'Nieodnotowany',
    'Save Attendance': 'Zapisz obecność',
    'Attendance': 'Obecność',
    'Attendance saved for %(count)s students in %(code)s on %(date)s.':
        'Zapisano obecność %(count)s studentów na kursie %(code)s w dniu %(date)s.',
    'Nothing to save — no students were marked.':
        'Nie ma czego zapisać — żaden student nie został odnotowany.',
    'That date could not be read. Using today instead.':
        'Nie udało się odczytać daty. Użyto dzisiejszej.',
    'Student Management System': 'System Zarządzania Studentami',
    'Your Courses': 'Twoje kursy',
    'Average in Your Courses': 'Średnia na Twoich kursach',
    'Enrolled Courses & Grades': 'Kursy i oceny',
    'Your Courses & Grades for this Student': 'Twoje kursy i oceny tego studenta',
    'No enrollments yet': 'Brak zapisów',
    'Update student information': 'Zaktualizuj dane studenta',
    'Fill in the student details below': 'Wypełnij poniższe dane studenta',
    'First Name': 'Imię',
    'Last Name': 'Nazwisko',
    'Email Address': 'Adres e-mail',
    'Active Student': 'Aktywny student',
    'Update Student': 'Zaktualizuj studenta',
    'Create Student': 'Dodaj studenta',
    'Delete Student': 'Usuń studenta',
    '\\n            Are you sure you want to delete <strong>%(name)s</strong> (%(number)s)?\\n'
    '            This will also remove all their enrollments and grades.\\n'
    '            This action cannot be undone.\\n            ':
        '\\n            Czy na pewno chcesz usunąć <strong>%(name)s</strong> (%(number)s)?\\n'
        '            Usunięte zostaną także wszystkie zapisy i oceny tego studenta.\\n'
        '            Tej operacji nie można cofnąć.\\n            ',

    # --- Courses -----------------------------------------------------------
    'Manage academic courses and their details': 'Zarządzaj kursami i ich szczegółami',
    'Courses you teach': 'Kursy, które prowadzisz',
    'Add Course': 'Dodaj kurs',
    'Search courses...': 'Szukaj kursów...',
    'All Semesters': 'Wszystkie semestry',
    'No Courses Found': 'Nie znaleziono kursów',
    'No courses matching \\"%(query)s\\"': 'Brak kursów pasujących do \\"%(query)s\\"',
    'Get started by creating your first course': 'Zacznij od utworzenia pierwszego kursu',
    'No courses are assigned to you yet': 'Nie przypisano Ci jeszcze żadnego kursu',
    'Course Information': 'Informacje o kursie',
    'Course Code': 'Kod kursu',
    'Course Name': 'Nazwa kursu',
    'Max Students': 'Limit studentów',
    'Enrolled / Max': 'Zapisani / Limit',
    'Available Seats': 'Wolne miejsca',
    'Description': 'Opis',
    'Enrolled Students (%(count)s)': 'Zapisani studenci (%(count)s)',
    'Students — %(active)s active of %(total)s enrolled':
        'Studenci — %(active)s aktywnych z %(total)s zapisanych',
    'No students enrolled in this course yet.':
        'Na ten kurs nie zapisał się jeszcze żaden student.',
    'Update course information': 'Zaktualizuj informacje o kursie',
    'Fill in the course details below': 'Wypełnij poniższe dane kursu',
    'Active Course': 'Aktywny kurs',
    'Update Course': 'Zaktualizuj kurs',
    'Create Course': 'Utwórz kurs',
    'Delete Course': 'Usuń kurs',
    '\\n            Are you sure you want to delete <strong>%(name)s</strong> (%(code)s)?\\n'
    '            This will also remove all enrollments and grades for this course.\\n'
    '            This action cannot be undone.\\n            ':
        '\\n            Czy na pewno chcesz usunąć <strong>%(name)s</strong> (%(code)s)?\\n'
        '            Usunięte zostaną także wszystkie zapisy i oceny na tym kursie.\\n'
        '            Tej operacji nie można cofnąć.\\n            ',

    # --- Enrollments -------------------------------------------------------
    'Manage student-course enrollments': 'Zarządzaj zapisami studentów na kursy',
    'Student-course enrollments for your courses (read-only)':
        'Zapisy studentów na Twoje kursy (tylko do odczytu)',
    'No Enrollments Found': 'Nie znaleziono zapisów',
    'Create a new enrollment to get started': 'Utwórz nowy zapis, aby rozpocząć',
    'Update enrollment status': 'Zaktualizuj status zapisu',
    'Assign a student to a course': 'Przypisz studenta do kursu',
    'A course cannot take more active enrollments than its capacity':
        'Kurs nie może mieć więcej aktywnych zapisów niż wynosi jego limit',
    'Update Enrollment': 'Zaktualizuj zapis',
    'Create Enrollment': 'Utwórz zapis',
    'Remove Enrollment': 'Usuń zapis',
    '\\n            Are you sure you want to remove <strong>%(student)s</strong>\\n'
    '            from <strong>%(course)s</strong> (%(code)s)?\\n'
    '            Any associated grade will also be deleted.\\n            ':
        '\\n            Czy na pewno chcesz usunąć <strong>%(student)s</strong>\\n'
        '            z kursu <strong>%(course)s</strong> (%(code)s)?\\n'
        '            Powiązana ocena również zostanie usunięta.\\n            ',

    # --- Grades ------------------------------------------------------------
    'View and manage grades for your courses':
        'Przeglądaj i zarządzaj ocenami na swoich kursach',
    'Manage academic grades and results': 'Zarządzaj ocenami i wynikami',
    'Date Assigned': 'Data wystawienia',
    'Assigned By': 'Wystawił',
    'No Grades Found': 'Nie znaleziono ocen',
    'Assign grades to student enrollments': 'Wystawiaj oceny do zapisów studentów',
    'Update grade information': 'Zaktualizuj informacje o ocenie',
    'Select an enrollment and assign a grade': 'Wybierz zapis i wystaw ocenę',
    'Only enrollments without grades are shown': 'Pokazywane są tylko zapisy bez ocen',
    'Grade Value': 'Wartość oceny',
    'Scale: 5.0 = Excellent (A) | 4.5 = Very Good (B) | 4.0 = Good (B) | 3.5 = Satisfactory '
    '(C) | 3.0 = Pass (D) | &lt;3.0 = Fail (F)':
        'Skala: 5.0 = bardzo dobry (A) | 4.5 = dobry plus (B) | 4.0 = dobry (B) | '
        '3.5 = dostateczny plus (C) | 3.0 = dostateczny (D) | &lt;3.0 = niedostateczny (F)',
    'Update Grade': 'Zaktualizuj ocenę',
    'Delete Grade': 'Usuń ocenę',
    '\\n            Are you sure you want to delete the grade <strong>%(value)s</strong>\\n'
    '            for <strong>%(student)s</strong> in <strong>%(course)s</strong>?\\n            ':
        '\\n            Czy na pewno chcesz usunąć ocenę <strong>%(value)s</strong>\\n'
        '            studenta <strong>%(student)s</strong> na kursie <strong>%(course)s</strong>?\\n'
        '            ',

    # --- Attendance --------------------------------------------------------
    'Track and view student attendance records': 'Rejestruj i przeglądaj obecność studentów',
    'Attendance records for your courses': 'Obecność na Twoich kursach',
    'Search by student or course...': 'Szukaj po studencie lub kursie...',
    'No Attendance Records': 'Brak wpisów obecności',
    'Start by marking attendance for a class': 'Zacznij od odnotowania obecności na zajęciach',
    'Update attendance record': 'Zaktualizuj wpis obecności',
    'Record a new attendance entry': 'Dodaj nowy wpis obecności',
    'Notes (Optional)': 'Notatki (opcjonalnie)',
    'Save Record': 'Zapisz wpis',
    'Save and Add Another': 'Zapisz i dodaj następny',
    'Back to Attendance': 'Powrót do obecności',
    'Delete Attendance': 'Usuń obecność',
    'Delete Record?': 'Usunąć wpis?',
    'Yes, Delete Record': 'Tak, usuń wpis',
    '\\n            Are you sure you want to delete the attendance record for\\n'
    '            <strong>%(student)s</strong> on <strong>%(date)s</strong>?\\n'
    '            This action cannot be undone.\\n            ':
        '\\n            Czy na pewno chcesz usunąć wpis obecności studenta\\n'
        '            <strong>%(student)s</strong> z dnia <strong>%(date)s</strong>?\\n'
        '            Tej operacji nie można cofnąć.\\n            ',

    # --- Model choices and help texts --------------------------------------
    'Administrator': 'Administrator',
    'Teacher': 'Prowadzący',
    'Grade from 2.0 (fail) to 5.0 (excellent)':
        'Ocena od 2.0 (niedostateczny) do 5.0 (bardzo dobry)',
    'Account that last saved this grade': 'Konto, które ostatnio zapisało tę ocenę',

    # --- Form placeholders -------------------------------------------------
    'e.g., STU-2025-001': 'np. STU-2025-001',
    'e.g., Computer Science': 'np. Informatyka',
    'e.g., CS101': 'np. CS101',
    'Phone Number': 'Numer telefonu',
    'Course description...': 'Opis kursu...',
    'Optional comments...': 'Komentarz (opcjonalnie)...',
    'Optional notes...': 'Notatka (opcjonalnie)...',

    # --- Pagination --------------------------------------------------------
    'Pagination': 'Paginacja',
    'Previous': 'Poprzednia',
    'Next': 'Następna',
    '\\n        Showing %(start)s–%(end)s of %(total)s\\n        ':
        '\\n        Wyświetlanie %(start)s–%(end)s z %(total)s\\n        ',
    '\\n            Page %(current)s of %(total)s\\n            ':
        '\\n            Strona %(current)s z %(total)s\\n            ',

    # --- Dashboard ---------------------------------------------------------
    'Students by Program': 'Studenci według programu',
    'Recent Students': 'Ostatnio dodani studenci',
    'Recent Enrollments': 'Ostatnie zapisy',
    'No students yet': 'Brak studentów',
    'New students will appear here once they are added.':
        'Nowi studenci pojawią się tutaj po dodaniu.',
    'Recent course enrollments will show up here.':
        'Ostatnie zapisy na kursy pojawią się w tym miejscu.',
    'Language': 'Język',

    # --- Profile -----------------------------------------------------------
    'My Profile': 'Mój profil',
    'Profile': 'Profil',
    'Update your personal information': 'Zaktualizuj swoje dane osobowe',
    'Security': 'Bezpieczeństwo',
    'Save Changes': 'Zapisz zmiany',
    'Toggle theme': 'Przełącz motyw',

    # --- Theme / chrome ----------------------------------------------------
    'Active Enrollments': 'Aktywne zapisy',
    'Enrollment Date': 'Data zapisu',

    # --- Stored demo data (shown through trans_db) -------------------------
    'Computer Science': 'Informatyka',
    'Mathematics': 'Matematyka',
    'Physics': 'Fizyka',
    'Administration': 'Administracja',
    'Introduction to Computer Science': 'Wstęp do informatyki',
    'Database Systems': 'Systemy baz danych',
    'Web Development': 'Tworzenie aplikacji webowych',
    'Calculus I': 'Analiza matematyczna I',
    'Linear Algebra': 'Algebra liniowa',
    'Physics I — Mechanics': 'Fizyka I — Mechanika',
    'Data Structures & Algorithms': 'Struktury danych i algorytmy',
    'Statistics & Probability': 'Statystyka i rachunek prawdopodobieństwa',
    'Fundamental concepts of computer science including algorithms, data structures, and programming basics.':
        'Podstawy informatyki: algorytmy, struktury danych i wstęp do programowania.',
    'Design and implementation of relational databases, SQL, normalization, and transaction management.':
        'Projektowanie i implementacja relacyjnych baz danych, SQL, normalizacja i transakcje.',
    'Modern web technologies including HTML5, CSS3, JavaScript, and server-side programming.':
        'Nowoczesne technologie webowe: HTML5, CSS3, JavaScript oraz programowanie po stronie serwera.',
    'Limits, derivatives, and integrals of single-variable functions.':
        'Granice, pochodne i całki funkcji jednej zmiennej.',
    'Vectors, matrices, linear transformations, eigenvalues and eigenvectors.':
        'Wektory, macierze, przekształcenia liniowe, wartości i wektory własne.',
    "Classical mechanics, Newton's laws, energy, momentum, and rotational motion.":
        'Mechanika klasyczna, prawa Newtona, energia, pęd i ruch obrotowy.',
    'Advanced data structures, algorithm design, complexity analysis, sorting and searching.':
        'Zaawansowane struktury danych, projektowanie algorytmów, złożoność, sortowanie i wyszukiwanie.',
    'Probability theory, random variables, statistical inference, and hypothesis testing.':
        'Rachunek prawdopodobieństwa, zmienne losowe, wnioskowanie statystyczne i testowanie hipotez.',
}


def po_quote(value: str) -> str:
    """Render a translation as .po msgstr lines, splitting on escaped newlines."""
    if '\\n' not in value:
        return f'msgstr "{value}"'

    # Keep the \n at the end of each chunk, mirroring gettext's own style.
    chunks = value.split('\\n')
    lines = ['msgstr ""']
    for index, chunk in enumerate(chunks):
        suffix = '\\n' if index < len(chunks) - 1 else ''
        if chunk or suffix:
            lines.append(f'"{chunk}{suffix}"')
    return '\n'.join(lines)


# Plural messages. Polish takes four forms — 1, 2-4, 5+, and the fractional
# case — so these cannot live in TRANSLATIONS, which holds one string each.
PLURAL_TRANSLATIONS = {
    '%(counter)s component': [
        '%(counter)s składowa',
        '%(counter)s składowe',
        '%(counter)s składowych',
        '%(counter)s składowej',
    ],
}


HEADER_FIELDS = {
    'Project-Id-Version': 'Student Management System 1.0',
    'Last-Translator': 'Maksym Shpak',
    'Language-Team': 'Polish',
}


def fill_header(block: str) -> str:
    block = re.sub(r'^#, fuzzy\n', '', block, flags=re.M)
    for field, value in HEADER_FIELDS.items():
        block = re.sub(rf'"{field}: .*?\\n"', f'"{field}: {value}\\\\n"', block)
    return block


def main() -> None:
    text = PO_PATH.read_text(encoding='utf-8')
    blocks = text.split('\n\n')
    blocks[:2] = [fill_header(b) for b in blocks[:2]]
    filled = missing = 0
    unknown = []

    for i, block in enumerate(blocks):
        match = re.search(r'^msgid ((?:".*"\n?)+)', block, re.M)
        if not match:
            continue
        msgid = ''.join(re.findall(r'"(.*)"', match.group(1)))
        if not msgid:
            continue

        if 'msgid_plural' in block:
            forms = PLURAL_TRANSLATIONS.get(msgid)
            if forms is None:
                if re.search(r'^msgstr\[0\] ""$', block, re.M):
                    unknown.append(msgid)
                    missing += 1
                continue
            block = re.sub(r'^#\| .*\n', '', block, flags=re.M)
            block = re.sub(r'^#, fuzzy(, )?', lambda m: '#, ' if m.group(1) else '',
                           block, flags=re.M)
            for index, form in enumerate(forms):
                block = re.sub(
                    rf'^msgstr\[{index}\] ".*"$',
                    lambda _m, f=form: f'msgstr[{index}] "{f}"',
                    block, flags=re.M,
                )
            blocks[i] = block
            filled += 1
            continue

        translation = TRANSLATIONS.get(msgid)
        if translation is None:
            if re.search(r'^msgstr ""$', block, re.M):
                unknown.append(msgid)
                missing += 1
            continue

        # Drop the fuzzy flag and gettext's "previous msgid" hints.
        block = re.sub(r'^#\| .*\n', '', block, flags=re.M)
        block = re.sub(r'^#, fuzzy(, )?', lambda m: '#, ' if m.group(1) else '', block, flags=re.M)
        block = re.sub(r'^#, *$\n', '', block, flags=re.M)

        # A lambda keeps backslash sequences in the translation literal; a plain
        # replacement string would let re.sub expand "\n" into a real newline.
        replacement = po_quote(translation) + '\n'
        block = re.sub(r'^msgstr ((?:".*"\n?)+)', lambda _m: replacement,
                       block, flags=re.M).rstrip('\n')
        blocks[i] = block
        filled += 1

    PO_PATH.write_text('\n\n'.join(blocks), encoding='utf-8')

    print(f'translated: {filled}')
    print(f'still untranslated: {missing}')
    for msgid in unknown:
        print(f'  MISSING: {msgid!r}')


if __name__ == '__main__':
    main()
