from django import template
register = template.Library()

RENAMING_MODELS_NAMES = {
    'group': 'circle',
    'groupchat': 'group',
}

@register.filter
def get_first_part(self):
    return self.split('_')[0]

@register.filter
def model_renaming(self):
    try:
        return RENAMING_MODELS_NAMES[self]
    except KeyError:
        return self