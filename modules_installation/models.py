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


def check_vhost(vhost):
    return vhost in [obj.name for obj in VirtualHost.objects.all()] or vhost == "global"


class BaseXmppModule(models.Model):
    class Meta:
        managed = False

    def __init__(self, vhost, name, module_options):
        self.vhost = vhost
        self.name = name
        self.module_options = module_options
        if not check_vhost(self.vhost):
            raise ValueError("Virtualhost doesn`t exist")
        if not isinstance(self.module_options, dict):
            raise ValueError("Module options must be a dictionary")

    def get_config(self):
        return {
            "type": "module",
            "vhost": self.vhost,
            "name": self.name,
            "module_options": self.module_options
        }

    def __str__(self):
        return self.name


class BaseXmppOption(models.Model):
    class Meta:
        managed = False

    def __init__(self, vhost, name, value):
        self.vhost = vhost
        self.name = name
        self.value = value
        if not check_vhost(self.vhost):
            raise ValueError("Virtualhost doesn`t exist")
        if isinstance(value, dict):
            raise ValueError("Value must not be a dictionary")

    def get_config(self):
        return {
            "type": "option",
            "vhost": self.vhost,
            "name": self.name,
            "value": self.value
        }

    def __str__(self):
        return self.name
