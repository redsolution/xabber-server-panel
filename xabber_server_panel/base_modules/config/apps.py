from django.apps import AppConfig


class ConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'xabber_server_panel.base_modules.config'

    def ready(self):
        from . import signals
