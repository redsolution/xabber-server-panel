import os
from django.conf import settings
from django import template
from django.urls import reverse

register = template.Library()

@register.simple_tag
def get_modules():
    list = []

    for module in settings.MODULES_SPECS:
        list.append({
            'name': module['name'],
            'url': reverse('modules:%s:info' % module['name'])
        })
    return list