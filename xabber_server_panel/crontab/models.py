from django.db import models
from ast import literal_eval
import json

from xabber_server_panel.utils import validate_cron_schedule


class CronJob(models.Model):

    TYPE_CHOICES = [
        ('internal_command', 'Internal command'),
        ('function', 'Function'),
        ('console_command', 'Console command'),
        ('built_in_job', 'Built-in job'),
    ]
    active = models.BooleanField(
        default=True
    )
    type = models.CharField(
        choices=TYPE_CHOICES,
        default='internal_command',
        max_length=20
    )
    schedule = models.CharField(
        max_length=100,
        validators=[validate_cron_schedule]
    )
    args = models.TextField(
        blank=True,
        null=True,
        help_text='Arguments should be represented as a list of values.'
    )
    kwargs = models.TextField(
        blank=True,
        null=True,
        help_text='Key-value arguments should be a valid JSON.'
    )
    command = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.command

    def get_kwargs(self):
        try:
            return json.loads(self.kwargs)
        except:
            return {}

    def get_args(self):
        try:
            return literal_eval(self.args)
        except:
            return []

    def get_job(self):
        if self.type in ('internal_command', 'built_in_job'):
            job = (self.schedule, 'django.core.management.call_command', [self.command], self.get_kwargs())
        elif self.type == 'function':
            job = (self.schedule, 'xabber_server_panel.crontab.utils.%s' % self.command, self.get_args(), self.get_kwargs())
        else:
            job = (self.schedule, 'xabber_server_panel.crontab.utils.run_terminal_function', [self.command, *self.get_args()])
        return job

