from datetime import datetime

from django import template

from virtualhost.models import User


register = template.Library()


DATE_INPUT_FORMATS = [
    '%Y-%m-%dT%H:%M:%SZ',
    '%Y-%m-%dT%H:%M:%S.%fZ',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S'
]


@register.filter
def pretty_date(timestamp, o_format='%b %d, %Y %H:%M'):
    if not timestamp:
        return ''

    if isinstance(timestamp, datetime):
        return timestamp.strftime(o_format)

    dt = None
    for i_format in DATE_INPUT_FORMATS:
        try:
            dt = datetime.strptime(timestamp, i_format)
            break
        except ValueError:
            continue

    return dt.strftime(o_format)


@register.simple_tag
def get_user_initials(user):
    if not user:
        return None

    if isinstance(user, User):
        if user.first_name and user.last_name:
            return u"{}{}".format(user.first_name[0], user.last_name[0])
        return user.username[0:2]
    elif isinstance(user, dict):
        if user["first_name"] and user["last_name"]:
            return u"{}{}".format(user["first_name"][0], user["last_name"][0])
        return user["username"][0:2]
    else:
        return user[0:2]


@register.simple_tag(takes_context=True)
def check_user_perms(context, content_type_app_label):
    username = context.get('request').session.get('_auth_user_username')
    host = context.get('request').session.get('_auth_user_host')
    try:
        user = User.objects.get(username=username, host=host)
        if content_type_app_label == 'is_admin' and user.is_admin:
            return True
        else:
            if user.has_perm(content_type_app_label):
                return True
        return False
    except User.DoesNotExist:
        return None


@register.simple_tag
def has_perm_on_app(auth_user, module):
    try:
        user_perms = auth_user.user_permissions.all()
    except Exception:
        return False
    filtered_list = [obj for obj in user_perms if obj.content_type.app_label == module]
    return len(filtered_list) > 0
