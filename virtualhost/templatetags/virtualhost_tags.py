from importlib import import_module

from django import template
from django.conf import settings

register = template.Library()

RENAMING_MODELS_NAMES = {
    'group': 'circle',
    'groupchat': 'group',
}


def update_module_permissions_names():
    for module_name in list(filter(lambda k: 'modules.' in k, settings.INSTALLED_APPS)):
        try:
            module = import_module(module_name + ".apps")
            config = getattr(module, 'ModuleConfig')
            renamed_models_dict = getattr(config, 'RENAMING_MODELS_NAMES')
            for key in renamed_models_dict:
                RENAMING_MODELS_NAMES.update({key: renamed_models_dict[key]})
        except (ImportError, AttributeError):
            pass


update_module_permissions_names()


@register.filter
def get_first_part(self):
    return self.split('_')[0]


@register.filter
def model_renaming(self):
    try:
        return RENAMING_MODELS_NAMES[self]
    except KeyError:
        return self
