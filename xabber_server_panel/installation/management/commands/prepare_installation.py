from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.management import call_command
import subprocess

from xabber_server_panel.utils import is_ejabberd_started, server_installed, stop_ejabberd


class Command(BaseCommand):
    help = 'Clean db and delete .installation_lock'

    def add_arguments(self, parser):
        parser.add_argument('--server_db', '-s', type=str, required=True)

    def handle(self, *args, **options):
        server_db = options['server_db']

        # rollback
        call_command('migrate', 'circles', 'zero', interactive=False)
        call_command('migrate', 'config', 'zero', interactive=False)
        call_command('migrate', 'registration', 'zero', interactive=False)
        call_command('migrate', 'users', 'zero', interactive=False)

        # migrate
        call_command('migrate', interactive=False)

        if is_ejabberd_started():
            stop_ejabberd()

        # Drop the serever database
        try:
            self.stdout.write(f"Dropping database '{server_db}'...")
            subprocess.run(['dropdb', server_db], check=True)
        except Exception as e:
            print(e)

        # Create the server database
        try:
            self.stdout.write(f"Creating database '{server_db}'...")
            subprocess.run(['createdb', server_db], check=True)
        except Exception as e:
            print(e)

        # Delete installation lock
        if server_installed():
            subprocess.run(['rm', settings.INSTALLATION_LOCK])