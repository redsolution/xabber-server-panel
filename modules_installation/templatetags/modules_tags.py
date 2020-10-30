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
            'url': '/admin/server/modules/%s' % module['name'] +
                   reverse('info', urlconf="modules." + module['name'] + '.urls')
        })
    return list


@register.simple_tag
def get_menu_subitems():
    subitems = []

    for module in settings.MODULES_SPECS:
        if 'create_items' in module:
            for subitem in module['create_items']:
                subitems.append({
                    'menu_item': 'create',
                    'subitem': subitem['name'],
                    'url': '/admin/server/modules/%s' % module['name'] +
                           reverse('%s' % subitem['url_name'], urlconf="modules." + module['name'] + '.urls')
                })
    return subitems