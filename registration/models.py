from django.db import models

from virtualhost.models import VirtualHost


class RegistrationSettings(models.Model):
    vhost = models.ForeignKey(VirtualHost, on_delete=models.CASCADE)
    status = models.CharField(default='disabled', max_length=50)


class RegistrationURL(models.Model):
    vhost = models.ForeignKey(VirtualHost, on_delete=models.CASCADE)
    value = models.CharField(max_length=150)
