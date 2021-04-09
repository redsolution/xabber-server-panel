from importlib import import_module

from django.conf import settings
from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()


@register.simple_tag
def get_modules():
    modules_list = []

    for module in list(filter(lambda k: 'modules.' in k, settings.INSTALLED_APPS)):
        module = module.split('.')[1]
        try:
            url = reverse('modules:%s:info' % module)
        except NoReverseMatch:
            url = '/admin/server/modules/%s' % module + \
                  reverse('info', urlconf="modules." + module + '.urls')
        modules_list.append({
            'name': module,
            'url': url
        })
    return modules_list


@register.simple_tag
def get_menu_subitems():
    subitems_list = []

    for module in list(filter(lambda k: 'modules.' in k, settings.INSTALLED_APPS)):
        try:
            module_object = import_module(module + ".apps")
            config = getattr(module_object, 'ModuleConfig')
            module = module.split('.')[1]
            if hasattr(config, 'CREATE_ITEMS'):
                for subitem in config.CREATE_ITEMS:
                    try:
                        url = reverse('modules:%s:%s' % (module, subitem['url_name']))
                    except NoReverseMatch:
                        url = '/admin/server/modules/%s' % module + \
                              reverse('%s' % subitem['url_name'], urlconf="modules." + module + '.urls')
                    subitems_list.append({
                        'menu_item': 'create',
                        'subitem': subitem['name'],
                        'url': url
                    })
        except ImportError or AttributeError:
            pass
    return subitems_list