from django.utils import timezone
from django.conf import settings
from django.core.management.base import BaseCommand
from virtualhost.models import User
from api.api import EjabberdAPI


class Command(BaseCommand):
    help = 'Block expired accounts'

    def add_arguments(self, parser):
        parser.add_argument('--token', type=str, default=settings.CRON_JOB_TOKEN)
        parser.add_argument('--reason', type=str, default='Your account has expired')

    def handle(self, *args, **options):

        users = User.objects.filter(expires__lt=timezone.now(), is_active=True)
        api = EjabberdAPI()
        api.fetch_token(options['token'])
        for user in users:
            data = dict(username=user.username, host=user.host, reason=options['reason'])
            api.block_user(data=data)
            if not api.success:
                self.stderr.write(self.style.ERROR('status_code: {}\nresponse {}'.format(api.status_code, api.response)))
                return
        users.update(is_active=False)
