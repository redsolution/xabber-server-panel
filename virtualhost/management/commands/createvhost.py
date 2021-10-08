from django.core.management.base import BaseCommand
from virtualhost.models import VirtualHost


class Command(BaseCommand):
    help = 'Create virtual xmpp host (only in panel)'

    def handle(self, *args, **options):
        VirtualHost.objects.create(name=options['xmpp_host'])

    def add_arguments(self, parser):
        parser.add_argument('xmpp_host')
