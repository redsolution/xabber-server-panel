from django.db import models
from virtualhost.models import VirtualHost


class BaseModuleConfig(models.Model):
    GLOBAL_HOST_NAME = "global"

    virtual_host = models.CharField(
        max_length=255,
        verbose_name="Related virtual host",
        blank=False,
        null=False
    )

    class Meta:
        managed = False
