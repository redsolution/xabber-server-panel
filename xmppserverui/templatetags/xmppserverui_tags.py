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
