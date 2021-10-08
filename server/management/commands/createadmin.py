from django.core.management.base import BaseCommand
from virtualhost.models import User

class Command(BaseCommand):
    help = 'Create admin (only in panel)'

    def handle(self, *args, **options):

        user = User.objects.create(username=options['uname'],
                                   host=options['hname'],
                                   is_admin=True)
        user.set_password(options['password'])
        user.save()

    def add_arguments(self, parser):
        parser.add_argument('uname')
        parser.add_argument('hname')
        parser.add_argument('password')
