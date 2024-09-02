from django.db.models.signals import pre_delete
from django.dispatch import receiver

from xabber_server_panel.base_modules.config.models import VirtualHost, ModuleSettings, DiscoUrls
from xabber_server_panel.base_modules.registration.models import RegistrationUrl
from xabber_server_panel.certificates.models import Certificate


@receiver(pre_delete, sender=VirtualHost)
def delete_host_data(sender, *args, **kwargs):
    instance = kwargs.get('instance')

    ModuleSettings.objects.filter(host=instance.name).delete()
    Certificate.objects.filter(domain=instance.name).delete()
    DiscoUrls.objects.filter(host=instance.name).delete()
    RegistrationUrl.objects.filter(host=instance.name).delete()