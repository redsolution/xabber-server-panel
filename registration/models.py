from django.db import models

from virtualhost.models import VirtualHost


class RegistrationSettings(models.Model):
    vhost = models.ForeignKey(VirtualHost, on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=False)
    is_enabled_by_key = models.BooleanField(default=False)
