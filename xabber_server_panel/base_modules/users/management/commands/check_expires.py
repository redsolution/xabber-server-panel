from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from xabber_server_panel.base_modules.users.models import User
from xabber_server_panel.base_modules.config.models import ModuleSettings
from xabber_server_panel.api.api import EjabberdAPI


class Command(BaseCommand):
    help = 'Check and update user status based on expiration'

    def add_arguments(self, parser):
        parser.add_argument('--token', type=str, default=settings.CRON_JOB_TOKEN)
        parser.add_argument('--reason', type=str, default='Your account has expired')

    def handle(self, *args, **options):
        # Get the current date and time
        current_time = timezone.now()
        reason = options['reason']

        # get cronjob token from db
        cronjob_token = ModuleSettings.objects.filter(host='global', module='mod_panel').first().get_options().get('cronjob_token')
        if not cronjob_token:
            cronjob_token = options['token']

        api = EjabberdAPI()
        api.fetch_token(cronjob_token)

        # Filter users whose expires field is less than the current time
        expired_users = User.objects.filter(expires__lt=current_time).exclude(status='EXPIRED')

        # block users in server
        for user in expired_users:
            api.block_user(
                {
                    'username': user.username,
                    'host': user.host,
                    'reason': reason
                }
            )

        # Update the status of expired users to 'EXPIRED'
        expired_users.update(status='EXPIRED', reason=reason)
