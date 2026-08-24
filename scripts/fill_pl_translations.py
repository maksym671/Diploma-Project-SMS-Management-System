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
    'Status': 'Status',
    'Date': 'Data',
    'Actions': 'Akcje',
    'Program': 'Program',
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
    'Student Information': 'Informacje o studencie',
    'Study Program': 'Program studiów',
    'Date Enrolled': 'Data zapisu',
    'Email': 'E-mail',
    'Phone': 'Telefon',
    'Date of Birth': 'Data urodzenia',
    'Address': 'Adres',
    'Total Courses': 'Liczba kursów',
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

    # --- Profile -----------------------------------------------------------
    'My Profile': 'Mój profil',
    'Profile': 'Profil',
    'Update your personal information': 'Zaktualizuj swoje dane osobowe',
    'Security': 'Bezpieczeństwo',
    'Save Changes': 'Zapisz zmiany',

    # --- Password reset ----------------------------------------------------
    'Reset Password': 'Zmiana hasła',
    "Enter your email address and we'll send you a link to reset your password.":
        'Podaj swój adres e-mail, a wyślemy Ci link do zmiany hasła.',
    'Send Reset Link': 'Wyślij link',
    'Back to Login': 'Powrót do logowania',
    'Email Sent': 'Wiadomość wysłana',
    "We've emailed you instructions for setting your password, if an account exists with "
    'the email you entered. You should receive them shortly.':
        'Jeśli konto z podanym adresem e-mail istnieje, wysłaliśmy instrukcję ustawienia '
        'hasła. Wiadomość powinna dotrzeć w ciągu kilku minut.',
    'Return to Login': 'Powrót do logowania',
    'Set New Password': 'Ustaw nowe hasło',
    'Please enter your new password twice so we can verify you typed it in correctly.':
        'Wpisz nowe hasło dwukrotnie, aby potwierdzić jego poprawność.',
    'Change Password': 'Zmień hasło',
    'Invalid Link': 'Nieprawidłowy link',
    'The password reset link was invalid, possibly because it has already been used. Please '
    'request a new password reset.':
        'Link do zmiany hasła jest nieprawidłowy — prawdopodobnie został już użyty. '
        'Poproś o nowy link.',
    'Request New Link': 'Poproś o nowy link',
    'Password Reset Complete': 'Hasło zostało zmienione',
    'Your password has been set. You may go ahead and log in now.':
        'Twoje hasło zostało ustawione. Możesz się teraz zalogować.',
    'Log In': 'Zaloguj się',
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


HEADER_FIELDS = {
    'Project-Id-Version': 'Student Management System 1.0',
    'Last-Translator': 'Maksym Shpak',
    'Language-Team': 'Polish',
}


def fill_header(block: str) -> str:
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
