from django.core.management.base import BaseCommand
from django.conf import settings

from xabber_server_panel.base_modules.users.models import User

import subprocess


class Command(BaseCommand):
    help = 'Check and update user status based on expiration'

    def add_arguments(self, parser):
        parser.add_argument('--username', '-u', type=str, required=True)
        parser.add_argument('--host', '-H', type=str, required=True)
        parser.add_argument('--password', '-p', type=str, required=True)

    def handle(self, *args, **options):
        username = options['username']
        host = options['host']
        password = options['password']

        try:
            user = User.objects.get(
                username=username,
                host=host
            )
        except User.DoesNotExist:
            print('User does not exists')
            return

        user.set_password(password)
        user.save()

        # change password on server
        cmd_create_admin = [
            settings.EJABBERDCTL,
            'change_password',
            username,
            host,
            password
        ]
        cmd = subprocess.Popen(
            cmd_create_admin,
            stdin=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        cmd.communicate()
        if cmd.returncode == 0:
            print('Password changed successfully')
        else:
            print('Something goes wrong')
