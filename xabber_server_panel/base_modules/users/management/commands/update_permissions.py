from django.core.management.base import BaseCommand
from xabber_server_panel.base_modules.users.utils import update_permissions


class Command(BaseCommand):
    help = ('Update permissions')
    can_import_settings = True

    def handle(self, *args, **options):
        update_permissions()