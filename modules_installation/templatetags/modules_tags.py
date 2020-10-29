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


@register.simple_tag
def get_menu_subitems():
    subitems = []

    for module in settings.MODULES_SPECS:
        if 'menu_subitems' in module:
            for menu_item in module['menu_subitems']:
                for subitem in module['menu_subitems'][menu_item]:
                    subitems.append({
                        'menu_item': menu_item,
                        'subitem': subitem['name'],
                        'url': reverse('modules:%s:%s' % (module['name'], subitem['url_name']))
                    })
        if 'create_items' in module:
            for subitem in module['create_items']:
                print(subitem)
                subitems.append({
                    'menu_item': 'create',
                    'subitem': subitem['name'],
                    'url': reverse('modules:%s:%s' % (module['name'], subitem['url_name']))
                })
    return subitems