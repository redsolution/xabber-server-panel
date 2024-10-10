from django.core.management.base import BaseCommand

from xabber_server_panel.certificates.utils import update_or_create_certs
from xabber_server_panel.base_modules.config.models import ModuleSettings
from xabber_server_panel.api.api import EjabberdAPI


class Command(BaseCommand):
    help = 'Create or update domain certificates'

    def handle(self, *args, **options):
        cronjob_token = ModuleSettings.objects.filter(host='global', module='mod_panel'). \
            first().get_options().get('cronjob_token')
        if not cronjob_token:
            cronjob_token = options['token']
        api = EjabberdAPI()
        api.fetch_token(cronjob_token)
        update_or_create_certs('', api)
