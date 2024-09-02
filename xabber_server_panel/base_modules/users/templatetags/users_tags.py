from django import template
from ..models import User
from ..utils import check_permissions


register = template.Library()


@register.simple_tag()
def get_user_by_jid(jid):
    try:
        username, host = jid.split('@')
    except:
        return None

    user = User.objects.filter(username=username, host=host).first()

    return user


@register.simple_tag(takes_context=True)
def check_user_permissions(context, app, permission=None):
    request = context.get('request')
    return check_permissions(request.user, app, permission)