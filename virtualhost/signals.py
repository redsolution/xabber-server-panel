import json
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import login
from django.dispatch import receiver
from django.http import HttpResponse
from django.utils import timezone

from .models import User
from xmppserverinstaller.signals import success_installation
from auth.forms import LoginForm
from webhooks.signals import webhook_received
from webhooks.utils import check_signature, WebHookResponse


def get_user_ip(request):
    try:
        real_ip = request.META['HTTP_X_FORWARDED_FOR']
    except KeyError:
        return request.META['REMOTE_ADDR']
    else:
        return real_ip.split(",")[0]


@receiver(success_installation, sender=None)
def success_installation_handler(sender, **kwargs):
    from server.models import ConfigData
    from virtualhost.models import User, VirtualHost
    ConfigData.objects.create(db_host=kwargs['db_host'],
                              db_name=kwargs['db_name'],
                              db_user=kwargs['db_user'],
                              db_user_pass=kwargs['db_user_pass'])
    VirtualHost.objects.create(name=kwargs['xmpp_host'])
    user = User.objects.create(username=kwargs['admin_username'],
                               host=kwargs['xmpp_host'],
                               is_admin=True)
    user.set_password(kwargs['admin_password'])
    user.save()

    request = kwargs['request']
    data = {
        'username': '{}@{}'.format(kwargs['admin_username'],
                                   kwargs['xmpp_host']),
        'password': '{}'.format(kwargs['admin_password']),
        'source_browser': request.META['HTTP_USER_AGENT'],
        'source_ip': get_user_ip(request)
    }
    form = LoginForm(data)
    if form.is_valid():
        login(request, form.user)
        request.session['_auth_user_username'] = kwargs['admin_username']
        request.session['_auth_user_host'] = kwargs['xmpp_host']


@receiver(webhook_received)
def webhook_received_handler(_sender, **kwargs):
    """
    Request path: "/xmppserver"
    Request body:
        { "target": "user",
          "action": "create/remove",
          "username": "bob",
          "host": "domain.com"
        }
    """

    path = kwargs.get('path')
    if path.rstrip('/') != 'xmppserver':
        return
    request = kwargs.get('request')
    if not check_signature(request):
        raise WebHookResponse(response=HttpResponse('Unauthorized', status=401))
    try:
        _json = json.loads(request.body)
    except:
        raise WebHookResponse(response=HttpResponse(status=400))
    if _json.get('target') == 'user':
        if _json.get('action') == 'create' and _json.get('username') and _json.get('host'):
            if User.objects.filter(username=_json.get('username'), host=_json.get('host')).exists():
                raise WebHookResponse(response=HttpResponse(status=201))
            new_user = User(username=_json.get('username'), host=_json.get('host'))
            if settings.DEFAULT_ACCOUNT_LIFETIME > 0:
                expires = timezone.now() + timedelta(days=settings.DEFAULT_ACCOUNT_LIFETIME)
                new_user.expires = expires
            new_user.save()
            raise WebHookResponse(response=HttpResponse(status=201))

        if _json.get('action') == 'remove' and _json.get('username') and _json.get('host'):
            User.objects.filter(username=_json.get('username'), host=_json.get('host')).delete()
            raise WebHookResponse(response=HttpResponse(status=201))
    return
