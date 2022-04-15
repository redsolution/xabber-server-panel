import os
import time
import subprocess

from django.template.loader import render_to_string
from django.conf import settings

from virtualhost.models import User, VirtualHost
# def execute_ejabberd_cmd(cmd):
#     cmd_ejabberd = [settings.EJABBERDCTL, ] + cmd
#     cmd = subprocess.Popen(cmd_ejabberd,
#                            stdin=subprocess.PIPE,
#                            stdout=subprocess.PIPE,
#                            stderr=subprocess.STDOUT)
#     output, error = cmd.communicate()
#     return {"success": cmd.returncode == 0,
#             "output": output,
#             "error": error}
#
#


def write_ejabberd_state(state):
    server_state_file = open(settings.EJABBERD_STATE, "w+")
    server_state_file.write(str(state))
    server_state_file.close()


def execute_ejabberd_cmd(cmd):
    cmd_ejabberd = [settings.EJABBERDCTL, ] + cmd
    return subprocess.call(cmd_ejabberd,
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE) == 0


def start_ejabberd():
    if not os.path.isfile(settings.INSTALLATION_LOCK):
        return None
    cmd = ['start']
    response = {"success": execute_ejabberd_cmd(cmd)}

    while not is_ejabberd_running()['success']:
        time.sleep(1)

    write_ejabberd_state(settings.EJABBERD_STATE_ON)
    return response


def restart_ejabberd():
    if not os.path.isfile(settings.INSTALLATION_LOCK):
        return None
    cmd = ['restart']
    response = {"success": execute_ejabberd_cmd(cmd)}

    while not is_ejabberd_running()['success']:
        time.sleep(1)

    write_ejabberd_state(settings.EJABBERD_STATE_ON)
    return response


def stop_ejabberd(change_state=True):
    cmd = ['stop']
    response = {"success": execute_ejabberd_cmd(cmd)}

    while is_ejabberd_running()['success']:
        time.sleep(1)
    if change_state:
        write_ejabberd_state(settings.EJABBERD_STATE_OFF)
    return response


def reload_ejabberd_config():
    cmd = ['reload_config']
    return {"success": execute_ejabberd_cmd(cmd)}


def is_ejabberd_running():
    cmd = ['status']
    return {"success": execute_ejabberd_cmd(cmd)}


def update_ejabberd_config():
    update_vhosts_config()
    from modules_installation.utils.config_generator import make_xmpp_config
    make_xmpp_config()
    reload_ejabberd_config()


def update_vhosts_config():
    template = 'ejabberd/vhosts_template.yml'
    vhosts = VirtualHost.objects.all()
    if not vhosts.exists():
        return
    file = open(os.path.join(settings.EJABBERD_CONFIG_PATH,
                             settings.EJABBERD_VHOSTS_CONFIG_FILE), 'w+')
    file.write(render_to_string(template, {'vhosts': vhosts}))
    file.close()

