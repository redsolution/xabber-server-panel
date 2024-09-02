from django.apps import AppConfig


class CrontabConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'xabber_server_panel.crontab'

    def ready(self):
        from . import signals