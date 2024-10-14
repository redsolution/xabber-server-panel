from django.conf import settings
from django.apps import apps
from collections import OrderedDict
from django.contrib import messages
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

import subprocess
import time
import os
import random
import string
import re


# ========== XABBER SERVER =============

def write_ejabberd_state(state):
    server_state_file = open(settings.XMPP_SERVER_STATE, "w+")
    server_state_file.write(str(state))
    server_state_file.close()


def execute_ejabberd_cmd(cmd):
    cmd_ejabberd = [settings.XMPP_SERVER_CTL, cmd]
    command = subprocess.call(
        cmd_ejabberd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return command == 0


def is_ejabberd_started():
    return execute_ejabberd_cmd('status')


def server_installed():
    return os.path.isfile(settings.INSTALLATION_LOCK)


def start_ejabberd(first_start=False):
    if is_ejabberd_started():
        return

    if not first_start and not server_installed():
        return

    response = execute_ejabberd_cmd('start')

    while not is_ejabberd_started():
        print('wait 1 sec')
        time.sleep(1)

    write_ejabberd_state(settings.XMPP_SERVER_STATE_ON)
    return response


def restart_ejabberd():
    if not server_installed():
        return

    response = execute_ejabberd_cmd('restart')

    while not is_ejabberd_started():
        time.sleep(1)

    write_ejabberd_state(settings.XMPP_SERVER_STATE_ON)
    return response


def stop_ejabberd(change_state=True):

    response = execute_ejabberd_cmd('stop')

    while is_ejabberd_started():
        time.sleep(1)

    if change_state:
        write_ejabberd_state(settings.XMPP_SERVER_STATE_OFF)

    return response


def update_app_list(app_list):

    apps.app_configs = OrderedDict()
    apps.apps_ready = apps.models_ready = apps.loading = apps.ready = False
    apps.clear_cache()
    apps.populate(app_list)


def reload_server():
    # try to reload server
    try:
        if os.environ.get("XABBER_PANEL_PF"):
            import signal
            pid = open(os.environ.get("XABBER_PANEL_PF")).read()
            os.kill(int(pid), signal.SIGHUP)
        else:
            os.utime(os.path.join(settings.BASE_DIR, 'xabber_server_panel/wsgi.py'), times=None)
    except:
        pass


# ============ VALIDATORS =============
def validate_link(value):
    """
    Custom validator to check if a URL is valid.
    """
    url_validator = URLValidator()

    try:
        # Use Django's built-in URLValidator to validate the URL
        url_validator(value)
    except ValidationError:
        # If validation fails, raise a ValidationError with a custom error message
        return False

    return True


def validate_cron_schedule(value):
    # Cron schedule pattern: minute hour day_of_month month day_of_week
    cron_pattern = re.compile(r'^(\*\/[0-9]+|[0-9]+|\*) (\*\/[0-9]+|[0-9]+|\*) (\*\/[0-9]+|[0-9]+|\*) (\*\/[0-9]+|[0-9]+|\*) (\*\/[0-9]+|[0-9]+|\*)$')

    if not cron_pattern.match(value):
        raise ValidationError(
            "Invalid cron schedule format.",
        )


# =============== OTHER ==============

def get_error_messages(request):
    error_messages = []

    # Get all messages for the current request
    message_list = messages.get_messages(request)

    # Filter messages with the 'error' tag
    for message in message_list:
        if message.tags == 'error':
            error_messages.append(message.message)

    return error_messages


def get_success_messages(request):
    success_messages = []

    # Get all messages for the current request
    message_list = messages.get_messages(request)

    # Filter messages with the 'error' tag
    for message in message_list:
        if message.tags == 'success':
            success_messages.append(message.message)

    return success_messages


def get_system_group_suffix():
    return ''.join(random.choices(string.ascii_lowercase, k=8))


def check_versions(current_version, new_version):

    """ Returns success = True if new version more than current version. """

    response = {
        'error': '',
        'success': True
    }

    try:
        current_version = tuple(map(int, current_version.split('.')))
        new_version = tuple(map(int, new_version.split('.')))
    except ValueError:
        response['error'] = "Invalid version format. Versions should be in the format 'mm.dd.v'."
        response['success'] = False
        return response

    if new_version < current_version:
        response['error'] = "You have a newer version installed. Downgrade is not allowed."
        response['success'] = False
    elif new_version == current_version:
        response['error'] = "You already have this version installed."
        response['success'] = False

    return response