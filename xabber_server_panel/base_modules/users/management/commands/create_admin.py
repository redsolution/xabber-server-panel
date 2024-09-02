from django.core.management.base import BaseCommand

from xabber_server_panel.base_modules.users.forms import UserForm


class Command(BaseCommand):
    help = 'Create new admin'

    def add_arguments(self, parser):
        parser.add_argument('--host', '-H', type=str, required=True)
        parser.add_argument('--username', '-u', type=str, required=True)
        parser.add_argument('--password', '-p', type=str, required=True)

    def handle(self, *args, **options):
        host = options['host']
        username = options['username']
        password = options['password']

        data = {
            'host': host,
            'username': username,
            'password': password,
            'is_admin': True
        }

        form = UserForm(data)

        if form.is_valid():
            form.save()
            print('Admin "%s" created successfully!' % username)
        else:
            print(form.errors)