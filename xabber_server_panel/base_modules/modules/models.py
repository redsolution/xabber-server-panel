import json

from django.db import models


class XServicesToken(models.Model):

    token = models.TextField(unique=True)
    expires = models.DateTimeField()
    jid = models.EmailField(unique=True)


class ModuleServerConfig(models.Model):
    module = models.ForeignKey(
        'config.Module',
        on_delete=models.CASCADE,
        related_name='server_configs'
    )
    name = models.CharField(max_length=255)
    options = models.TextField(blank=True, default='{}')

    def set_options(self, options_dict):
        try:
            self.options = json.dumps(options_dict)
        except Exception:
            self.options = '{}'

    def get_options(self):
        try:
            return json.loads(self.options)
        except Exception:
            return {}

    class Meta:
        unique_together = ('module', 'name')

    def __str__(self):
        return '%s - %s' % (self.module.name, self.name)
