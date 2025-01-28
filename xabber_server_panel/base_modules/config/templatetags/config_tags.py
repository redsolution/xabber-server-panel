from django import template
from django.shortcuts import reverse

from xabber_server_panel.base_modules.config.utils import check_modules, get_create_views
from xabber_server_panel.base_modules.config.models import Module
from xabber_server_panel.utils import check_versions



register = template.Library()


@register.simple_tag()
def get_external_modules():
    check_modules()

    modules = Module.objects.all()
    return modules


@register.simple_tag()
def get_create_views_data():
    return get_create_views()


@register.simple_tag
def check_module_versions(module: Module, new_module_data: dict):

    """ Check avaliable updates for module and return update links """

    result = {}

    if isinstance(module, Module) and isinstance(new_module_data, dict):
        new_module_free = new_module_data.get('free')
        new_module_paid = new_module_data.get('paid')
        if not module.custom:
            if module.track == 'free':
                if new_module_free:
                    if check_versions(module.version, new_module_free.get('release')).get('success'):
                        result['upgrade'] = reverse('config:upload_module', kwargs={'module_name': module.name, 'track': 'free'})
                if new_module_paid:
                    if check_versions(module.version, new_module_paid.get('release'), equals_ok=True).get('success'):
                        result['buy'] = reverse('config:upload_module', kwargs={'module_name': module.name, 'track': 'paid'})
            elif module.track == 'paid':
                if new_module_paid:
                    if check_versions(module.version, new_module_paid.get('release')).get('success'):
                        result['upgrade'] = reverse('config:upload_module', kwargs={'module_name': module.name, 'track': 'paid'})

    return result