from django import template

from xabber_server_panel.base_modules.config.utils import check_modules, get_create_views
from xabber_server_panel.base_modules.config.models import Module

register = template.Library()


@register.simple_tag()
def get_external_modules():
    check_modules()

    modules = Module.objects.all()
    return modules


@register.simple_tag()
def get_create_views_data():
    return get_create_views()