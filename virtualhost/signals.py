from django.contrib.auth import login
from django.dispatch import receiver

from xmppserverinstaller.signals import success_installation
from auth.forms import LoginForm


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
