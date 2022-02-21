import os
import time
import subprocess
import json

from django.template.loader import get_template, render_to_string
from django.conf import settings

from server.models import Configuration
from .signals import success_installation


def check_predefined_config():
    return os.path.isfile(os.path.join(settings.BASE_DIR, settings.PREDEFINED_CONFIG_FILE_PATH))


def load_predefined_config():
    with open(os.path.join(settings.BASE_DIR, settings.PREDEFINED_CONFIG_FILE_PATH)) as file:
        return json.load(file)


# TODO refactor it
def write_ejabberd_state(state):
    server_state_file = open(settings.EJABBERD_STATE, "w+")
    server_state_file.write(str(state))
    server_state_file.close()


def check_db_conn(data):
    cmd_check_db_conn = [settings.PSQL_SCRIPT, data['db_name'],
                         '-h', data['db_host'], '-U', data['db_user']]
    cmd = subprocess.Popen(cmd_check_db_conn,
                           env={'PGPASSWORD': data['db_user_pass']},
                           stdin=subprocess.PIPE,
                           stdout=open('/dev/null', 'w'),
                           stderr=subprocess.STDOUT)
    cmd.communicate()
    return cmd.returncode == 0


def migrate_db(data):
    cmd_migrate_db = [settings.PSQL_SCRIPT, data['db_name'],
                      '-h', data['db_host'], '-U', data['db_user'],
                      '-f', settings.EJABBERD_DUMP]
    cmd = subprocess.Popen(cmd_migrate_db,
                           env={'PGPASSWORD': data['db_user_pass']},
                           stdin=subprocess.PIPE,
                           stdout=open('/dev/null', 'w'),
                           stderr=subprocess.STDOUT)
    cmd.communicate()
    return cmd.returncode == 0


def update_vhosts_config(data):
    template = 'ejabberd/vhosts_template.yml'
    vhosts = (data['xmpp_host'], )
    file = open(os.path.join(settings.EJABBERD_CONFIG_PATH,
                             settings.EJABBERD_VHOSTS_CONFIG_FILE), 'w+')
    file.write(render_to_string(template, {'vhosts': vhosts}))
    file.close()


def create_config(data):
    data['PROJECT_DIR'] = settings.PROJECT_DIR
    data['VHOST_FILE'] = os.path.join(settings.EJABBERD_CONFIG_PATH, settings.EJABBERD_VHOSTS_CONFIG_FILE)
    config_template = get_template('ejabberd/base_config.yml')
    config_file = open(os.path.join(settings.EJABBERD_CONFIG_PATH, 'ejabberd.yml'), "w+")
    config_file.write(config_template.render(context=data))
    config_file.close()
    entry = Configuration(pk=1, config=config_template.render(context=data))
    entry.save()
    update_vhosts_config(data)


def start_ejabberd():
    cmd_start_ejabberd = [settings.EJABBERDCTL, 'start']
    cmd = subprocess.Popen(cmd_start_ejabberd,
                           stdin=subprocess.PIPE,
                           stdout=open('/dev/null', 'w'),
                           stderr=subprocess.STDOUT)
    cmd.communicate()
    cmd_result = cmd.returncode == 0
    if cmd_result:
        write_ejabberd_state(settings.EJABBERD_STATE_ON)
    return cmd_result


def stop_ejabberd():
    cmd_stop_ejabberd = [settings.EJABBERDCTL, 'stop']
    cmd = subprocess.Popen(cmd_stop_ejabberd,
                           stdin=subprocess.PIPE,
                           stdout=open('/dev/null', 'w'),
                           stderr=subprocess.STDOUT)
    cmd.communicate()
    cmd_result = cmd.returncode == 0
    if cmd_result:
        write_ejabberd_state(settings.EJABBERD_STATE_OFF)
    return cmd_result


def check_status():
    cmd_check_status = [settings.EJABBERDCTL, 'status']
    cmd = subprocess.Popen(cmd_check_status,
                           stdin=subprocess.PIPE,
                           stdout=open('/dev/null', 'w'),
                           stderr=subprocess.STDOUT)
    cmd.communicate()
    return cmd.returncode == 0


def create_admin(data):
    while not check_status():
        print('waiting for 1 second...')
        time.sleep(1)

    cmd_create_admin = [settings.EJABBERDCTL, 'register',
                          data['admin_username'],
                          data['xmpp_host'],
                          data['admin_password']]
    cmd = subprocess.Popen(cmd_create_admin,
                           stdin=subprocess.PIPE,
                           # stdout=open('/dev/null', 'w'),
                           stderr=subprocess.STDOUT)
    cmd.communicate()
    return cmd.returncode == 0


def set_created_user_as_admin(data):
    while not check_status():
        print('waiting for 1 second...')
        time.sleep(1)

    cmd_create_admin = [settings.EJABBERDCTL, 'panel_set_admin',
                          data['admin_username'],
                          data['xmpp_host']]
    cmd = subprocess.Popen(cmd_create_admin,
                           stdin=subprocess.PIPE,
                           # stdout=open('/dev/null', 'w'),
                           stderr=subprocess.STDOUT)
    cmd.communicate()
    return cmd.returncode == 0


def create_group(data):
    cmd_create_group = [settings.EJABBERDCTL, 'srg_create',
                        data['xmpp_host'],
                        data['xmpp_host'],
                        settings.EJABBERD_EVERYBODY_DEFAULT_GROUP_NAME,
                        settings.EJABBERD_EVERYBODY_DEFAULT_GROUP_DESCRIPTION,
                        ""]
    cmd = subprocess.Popen(cmd_create_group,
                           stdin=subprocess.PIPE,
                           stdout=open('/dev/null', 'w'),
                           stderr=subprocess.STDOUT)
    cmd.communicate()
    return cmd.returncode == 0


def assign_group_to_all(data):
    cmd_assign_to_all = [settings.EJABBERDCTL, 'srg_user_add',
                         '@all@',
                         data['xmpp_host'],
                         data['xmpp_host'],
                         data['xmpp_host']]
    cmd = subprocess.Popen(cmd_assign_to_all,
                           stdin=subprocess.PIPE,
                           stdout=open('/dev/null', 'w'),
                           stderr=subprocess.STDOUT)
    cmd.communicate()
    return cmd.returncode == 0


def start_installation_process(data):
    if not check_db_conn(data):
        msg = "Can't connect to database. Maybe you enter wrong data."
        print(msg)
        return False, msg
    print("Successfully connected to database.")

    if not migrate_db(data):
        msg = "Can't migrate database."
        print(msg)
        return False, msg
    print("Successfully migrated database.")

    create_config(data)
    print("Successfully create config for ejabberd.")

    if not start_ejabberd():
        msg = "Can't start ejabberd."
        print(msg)
        return False, msg
    print("Successfully started ejabberd.")

    if not create_admin(data):
        msg = "Can't create admin in Xabber server database."
        print(msg)
        return False, msg

    if not set_created_user_as_admin(data):
        msg = "Can't set created user as admin in Xabber server database."
        print(msg)
        return False, msg

    if not create_group(data):
        msg = "Can`t create default roster group"
        print(msg)
        return False, msg

    if not assign_group_to_all(data):
        msg = "Can`t create default roster group"
        print(msg)
        return False, msg

    print("Successfully created admin in ejabberd.")

    return True, None


def install_cmd(request, data):
    success, error_message = start_installation_process(data)
    if not success:
        is_server_started = check_status()
        if is_server_started:
            stop_ejabberd()
        return success, error_message

    # block installation mode
    open(settings.INSTALLATION_LOCK, 'a').close()
    os.chmod(settings.INSTALLATION_LOCK, 0o444)

    success_installation.send(sender=None,
                              request=request,
                              **data)
    return success, error_message
