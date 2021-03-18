from django.conf import settings
from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()

@register.simple_tag
def get_modules():
    modules_list = []

    for module in settings.MODULES_SPECS:
        try:
            url = reverse('modules:%s:info' % module['name'])
        except NoReverseMatch:
            url = '/admin/server/modules/%s' % module['name'] + \
                  reverse('info', urlconf="modules." + module['name'] + '.urls')
        modules_list.append({
            'name': module['name'],
            'url': url
        })
    return modules_list


@register.simple_tag
def get_menu_subitems():
    subitems_list = []

    for module in settings.MODULES_SPECS:
        if 'create_items' in module:
            for subitem in module['create_items']:
                try:
                    url = reverse('modules:%s:%s' % (module['name'], subitem['url_name']))
                except NoReverseMatch:
                    url = '/admin/server/modules/%s' % module['name'] + \
                          reverse('%s' % subitem['url_name'], urlconf="modules." + module['name'] + '.urls')
                subitems_list.append({
                    'menu_item': 'create',
                    'subitem': subitem['name'],
                    'url': url
                })
    return subitems_list