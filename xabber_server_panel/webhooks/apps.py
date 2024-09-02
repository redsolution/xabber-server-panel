from django.apps import AppConfig


class ServerConfig(AppConfig):
    name = 'xabber_server_panel.webhooks'

    def ready(self):
        from . import signals