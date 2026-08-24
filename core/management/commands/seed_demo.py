import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.models import Student, User

FIXTURE = 'demo_data'
ADMIN_PASSWORD_ENV = 'DJANGO_ADMIN_PASSWORD'


class Command(BaseCommand):
    help = (
        'Prepare a deployment: load the demonstration data set into an empty '
        'database and, when DJANGO_ADMIN_PASSWORD is set, replace the public '
        'demo password on the admin account. Safe to run on every deploy — an '
        'already-populated database keeps its data.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Load the fixture even if the database already has students.',
        )

    def handle(self, *args, **options):
        self._seed(force=options['force'])
        self._secure_admin()

    def _seed(self, *, force):
        existing = Student.objects.count()

        if existing and not force:
            self.stdout.write(
                f'Database already holds {existing} students — skipping seed.'
            )
            return

        call_command('loaddata', FIXTURE, verbosity=0)
        self.stdout.write(
            self.style.SUCCESS(
                f'Loaded demonstration data ({Student.objects.count()} students).'
            )
        )

    def _secure_admin(self):
        """The fixture ships a published demo password; override it if asked."""
        password = os.environ.get(ADMIN_PASSWORD_ENV)
        if not password:
            self.stdout.write(
                f'{ADMIN_PASSWORD_ENV} not set — the admin account keeps the '
                'documented demo password.'
            )
            return

        admin = User.objects.filter(username='admin').first()
        if admin is None:
            self.stderr.write('No "admin" account found — password not changed.')
            return

        admin.set_password(password)
        admin.save(update_fields=['password'])
        self.stdout.write(self.style.SUCCESS('Reset the admin password from the environment.'))
