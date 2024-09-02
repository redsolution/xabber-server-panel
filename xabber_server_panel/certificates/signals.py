from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.conf import settings

from xabber_server_panel.certificates.models import Certificate

import os


@receiver(pre_delete, sender=Certificate)
def delete_cert_data(sender, *args, **kwargs):
    instance = kwargs.get('instance')
    cert_path = os.path.join(settings.CERTS_DIR, instance.name)

    if os.path.exists(cert_path):
        os.remove(cert_path)