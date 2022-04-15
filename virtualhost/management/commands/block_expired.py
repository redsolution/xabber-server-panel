import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from virtualhost.models import User


class Command(BaseCommand):
    help = 'Block expired users'

    def handle(self, *args, **options):
        time_now = timezone.now()
        users = User.objects.filter(expires__lt=time_now)
        for obj in users:
            obj.is_active = False
            obj.expires = datetime.datetime.now()
            obj.save()
