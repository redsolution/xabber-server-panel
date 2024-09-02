from django.apps import AppConfig


class CertificatesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'xabber_server_panel.certificates'

    def ready(self):
        from . import signals