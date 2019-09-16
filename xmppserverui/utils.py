import os
import time
import subprocess
import string
import random

from django.core.urlresolvers import reverse
from django.contrib.auth import logout

from xmppserverui import settings
from xmppserverinstaller.utils import set_installation_mode


def get_xabber_web_suffix():
    return ''.join(random.choice(string.ascii_lowercase) for i in range(5))


def is_xmpp_server_installed():
    return os.path.isfile(os.path.join(settings.EJABBERD_CONFIG_PATH, 'ejabberd.yml'))


def is_xmpp_server_should_start():
    if not os.path.isfile(settings.EJABBERD_STATE):
        return False
    server_state = int(open(settings.EJABBERD_STATE, "r").read(1))
    return server_state == settings.EJABBERD_STATE_ON


def get_default_url(user, admin=None):
    if is_xmpp_server_installed():
        if user.is_anonymous():
            return reverse('auth:login')
        # return reverse('server:dashboard')
        if admin is not None:
            if admin:
                return reverse('server:dashboard')
            else:
                return reverse('personal-area:profile')
        return reverse('personal-area:profile')
    else:
        set_installation_mode()
        return reverse('installer:stepper')


def logout_full(request):
    if request.user.is_authenticated():
        request.user.api.logout(host=request.session['_auth_user_host'])
        logout(request)


def execute_ejabberd_cmd(cmd):
    cmd_ejabberd = [settings.EJABBERDCTL, ] + cmd
    return subprocess.call(cmd_ejabberd,
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE) == 0


def start_ejabberd():
    if not is_xmpp_server_installed():
        return None
    if not is_xmpp_server_should_start():
        return None
    if is_ejabberd_running()['success']:
        return None
    cmd = ['start']
    response = {"success": execute_ejabberd_cmd(cmd)}

    while not is_ejabberd_running()['success']:
        time.sleep(1)
    started_ejabberd()
    return response


def started_ejabberd():
    if not is_xmpp_server_installed():
        return None
    if not is_xmpp_server_should_start():
        return None
    if is_ejabberd_running()['success']:
        return None
    cmd = ['started']
    response = {"success": execute_ejabberd_cmd(cmd)}
    return response


def is_ejabberd_running():
    cmd = ['status']
    return {"success": execute_ejabberd_cmd(cmd)}
