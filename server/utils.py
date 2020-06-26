import os
import time
import subprocess

from OpenSSL import crypto
from cryptography import x509
from django.template.loader import render_to_string
from django.conf import settings
from datetime import datetime

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
    update_admins_config()
    update_vhosts_config()
    reload_ejabberd_config()


def update_admins_config():
    template = 'ejabberd/admin_acl_template.yml'
    admins = User.objects.filter(is_admin=True).order_by('username')
    file = open(os.path.join(settings.EJABBERD_CONFIG_PATH,
                             settings.EJABBERD_ADMINS_CONFIG_FILE), 'w+')
    file.write(render_to_string(template, {'admins': admins}))
    file.close()


def update_vhosts_config():
    template = 'ejabberd/vhosts_template.yml'
    vhosts = VirtualHost.objects.all()
    if not vhosts.exists():
        return
    file = open(os.path.join(settings.EJABBERD_CONFIG_PATH,
                             settings.EJABBERD_VHOSTS_CONFIG_FILE), 'w+')
    file.write(render_to_string(template, {'vhosts': vhosts}))
    file.close()


def get_cert_info(cert_file):
    bin_data = cert_file.read_bytes()

    try:
        crypto.load_privatekey(crypto.FILETYPE_PEM, bin_data)
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, bin_data)
        cn = cert.get_subject().CN
        not_after = datetime.strptime(cert.get_notAfter().decode().replace('Z', '+0000'), '%Y%m%d%H%M%S%z')
        not_before = datetime.strptime(cert.get_notBefore().decode().replace('Z', '+0000'), '%Y%m%d%H%M%S%z')
    except:
        return {}
    cert = cert.to_cryptography()
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except:
        ext = None
    if ext:
        names = [
            name
            for name in ext.get_values_for_type(x509.DNSName)
            if name is not None
        ]
        names.extend(
            str(name) for name in ext.get_values_for_type(x509.IPAddress)
        )
    else:
        names = []

    if not names:
        names = [cn]
    return {'names': names, 'not_after': not_after, 'not_before': not_before}
