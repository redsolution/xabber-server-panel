from django.core.management.base import BaseCommand
from django.utils import timezone

from xabber_server_panel.base_modules.modules.models import XServicesToken


class Command(BaseCommand):
    help = "Delete expired XServicesToken entries"

    def handle(self, *args, **options):
        now = timezone.now()
        expired = XServicesToken.objects.filter(
            # expires__lt=now
        )
        count = expired.count()

        expired.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} expired XServicesToken objects"))
