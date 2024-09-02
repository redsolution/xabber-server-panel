from django.core.management.base import BaseCommand

from xabber_server_panel.certificates.utils import update_or_create_certs


class Command(BaseCommand):
    help = 'Create or update domain certificates'

    def handle(self, *args, **options):
        update_or_create_certs()