import os
import subprocess
import psycopg2
from psycopg2 import sql
import json
import string
import secrets
import threading

from django.template.loader import get_template
from django.conf import settings
from requests.utils import certs

from xabber_server_panel.base_modules.config.utils import make_xmpp_config, update_vhosts_config, get_dns_records, create_config_file
from xabber_server_panel.base_modules.circles.models import Circle
from xabber_server_panel.base_modules.config.models import VirtualHost, ModuleSettings, AddSettings
from xabber_server_panel.base_modules.users.forms import UserForm
from xabber_server_panel.base_modules.users.utils import update_permissions
from xabber_server_panel.utils import get_system_group_suffix, start_ejabberd, stop_ejabberd, is_ejabberd_started
from xabber_server_panel.certificates.utils import update_or_create_certs
from xabber_server_panel.crontab.models import CronJob


def generate_secret(length=32):
    alphabet = string.ascii_letters + string.digits
    secret = ''.join(secrets.choice(alphabet) for i in range(length))
    return secret


def database_exists(data):
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(
            dbname=data['db_name'],
            user=data['db_user'],
            password=data['db_user_pass'],
            host=data['db_host']
        )
    except psycopg2.Error:
        print("Can't connect to database. Maybe you enter wrong data.")
        return False

    try:
        conn.autocommit = True
        cursor = conn.cursor()

        # Check if the database exists
        cursor.execute(sql.SQL("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s"), [data['db_name']])
        exists = cursor.fetchone()
        if exists:
            return True
        else:
            return False
    except psycopg2.OperationalError as e:
        print("Error connecting to PostgreSQL:", e)
        return False
    finally:
        if conn:
            conn.close()


def is_database_empty(data):
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(
            dbname=data['db_name'],
            user=data['db_user'],
            password=data['db_user_pass'],
            host=data['db_host']
        )
    except psycopg2.Error:
        print("Can't connect to database. Maybe you enter wrong data.")
        return False

    try:
        conn.autocommit = True
        cursor = conn.cursor()

        # Check if the database is empty
        cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public')")
        exists = cursor.fetchone()[0]
        return not exists
    except psycopg2.OperationalError as e:
        print("Error connecting to PostgreSQL:", e)
        return False
    finally:
        if conn:
            conn.close()


def migrate_db(data):
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(
            dbname=data['db_name'],
            user=data['db_user'],
            password=data['db_user_pass'],
            host=data['db_host']
        )

    except psycopg2.Error:
        print("Can't connect to database. Maybe you enter wrong data.")
        return False

    try:
        # Open a cursor to perform database operations
        cursor = conn.cursor()

        # Read the SQL dump file
        with open(settings.XMPP_SERVER_DB_DUMP, 'r', encoding='utf-8') as f:
            sql_commands = f.read()

        # Execute each command from the dump file
        cursor.execute(sql_commands)

        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        cursor.close()
        conn.close()

        return True
    except psycopg2.Error as e:
        print("Error:", e)
        return False


def create_vhost(data):
    try:

        # check srv records
        records = get_dns_records(data['host'])
        if 'error' in records:
            srv_records = False
        else:
            srv_records = True

        # check cert records
        records = get_dns_records(data['host'], type='A')
        if settings.CHALLENGE_RECORD in records.get('_acme-challenge', []):
            cert_records = True
        else:
            cert_records = False

        issue_cert = srv_records and cert_records

        VirtualHost.objects.get_or_create(
            name=data['host'],
            defaults={
                'srv_records': srv_records,
                'cert_records': cert_records,
                'issue_cert': issue_cert,
            }
        )
        return True
    except:
        return False


def generate_webhooks_secret(data):
    # generate webhook secret
    webhooks_secret = generate_secret()
    module_settings, created = ModuleSettings.objects.get_or_create(
        host='global',
        module='mod_webhooks'
    )

    panel_address = AddSettings.objects.filter(module_name='webhooks', key='panel_address').first()
    if getattr(settings, 'MOD_WEBHOOKS_URL', False):
        webhooks_url = settings.MOD_WEBHOOKS_URL
    elif panel_address:
        webhooks_url = panel_address.value
    else:
        webhooks_url = "https://xabber.%s/webhooks/xmppserver/" % data['host']

    module_settings.set_options(
        {
            'secret': f'\"{webhooks_secret}\"',
            'url': f'\"{webhooks_url}\"'
        }
    )
    module_settings.save()


def generate_cronjob_token(data):
    # generate cronjob token
    cronjob_token = generate_secret()
    module_settings, created = ModuleSettings.objects.get_or_create(
        host='global',
        module='mod_panel'
    )

    module_settings.set_options(
        {
            'cronjob_token': f"\"{cronjob_token}\"",
        }
    )
    module_settings.save()


def create_config(data):
    add_config = os.path.join(settings.XMPP_SERVER_CONFIG_PATH, settings.XMPP_SERVER_ADD_CONFIG_FILE)
    data['VHOST_FILE'] = os.path.join(settings.XMPP_SERVER_CONFIG_PATH, settings.XMPP_SERVER_VHOSTS_CONFIG_FILE)
    data['MODULES_FILE'] = os.path.join(settings.XMPP_SERVER_CONFIG_PATH, settings.XMPP_SERVER_MODULES_CONFIG_FILE)
    data['ADD_CONFIG'] = add_config
    data['CA_FILE'] = certs.where()
    data['settings'] = settings

    # Add config
    if not os.path.exists(add_config):
        create_config_file(add_config)

    # main config
    config_template = get_template('config/base_config.yml')
    config_path = os.path.join(settings.XMPP_SERVER_CONFIG_PATH, 'ejabberd.yml')
    create_config_file(config_path, config_template.render(context=data))

    # vhosts config
    update_vhosts_config([data['host']])

    # modules config
    make_xmpp_config()


def create_admin(data):
    data['is_admin'] = True
    # create user in db
    form = UserForm(data)
    if form.is_valid():
        # create user on server
        cmd_create_admin = [
            settings.XMPP_SERVER_CTL,
            'register',
            data['username'],
            data['host'],
            form.cleaned_data['password']
        ]
        cmd = subprocess.Popen(
            cmd_create_admin,
            stdin=subprocess.PIPE,
            # stdout=open('/dev/null', 'w'),
            stderr=subprocess.STDOUT
        )
        cmd.communicate()
        if cmd.returncode == 0:
            form.save()
            return True
    return False


def set_created_user_as_admin(data):
    cmd_create_admin = [settings.XMPP_SERVER_CTL, 'panel_set_admin',
                          data['username'],
                          data['host']]
    cmd = subprocess.Popen(cmd_create_admin,
                           stdin=subprocess.PIPE,
                           # stdout=open('/dev/null', 'w'),
                           stderr=subprocess.STDOUT)
    cmd.communicate()
    return cmd.returncode == 0


def create_group(data):
    cmd_create_group = [settings.XMPP_SERVER_CTL, 'srg_create',
                        data['host'],
                        data['host'],
                        settings.XMPP_SERVER_DEFAULT_GROUP_NAME,
                        settings.XMPP_SERVER_DEFAULT_GROUP_DESCRIPTION,
                        ""]
    cmd = subprocess.Popen(cmd_create_group,
                           stdin=subprocess.PIPE,
                           stdout=open('/dev/null', 'w'),
                           stderr=subprocess.STDOUT)
    cmd.communicate()
    return cmd.returncode == 0


def assign_group_to_all(data):
    cmd_assign_to_all = [settings.XMPP_SERVER_CTL, 'srg_user_add',
                         '@all@',
                         data['host'],
                         data['host'],
                         data['host']]
    cmd = subprocess.Popen(cmd_assign_to_all,
                           stdin=subprocess.PIPE,
                           stdout=open('/dev/null', 'w'),
                           stderr=subprocess.STDOUT)
    cmd.communicate()
    return cmd.returncode == 0


def activate_base_cronjobs():
    CronJob.objects.filter(type='built_in_job').update(active=True)
    # update crontab
    from django.db.models.signals import post_save
    post_save.send(sender=CronJob, instance=CronJob(), created=False)


def start_installation_process(data):

    if not database_exists(data):
        msg = "Database does not exists."
        print(msg)
        return False, msg

    if not is_database_empty(data):
        msg = "Database is not empty."
        print(msg)
        return False, msg

    if not migrate_db(data):
        msg = "Can't migrate database."
        print(msg)
        return False, msg
    print("Successfully migrated database.")

    if not create_vhost(data):
        msg = "Cant create virtual host."
        print(msg)
        return False, msg
    print('Successfully host created')

    if data.get('base_cronjobs'):
        activate_base_cronjobs()
        print('Base cronjobs activated successfully.')

    # Create a thread to create certificates
    thread = threading.Thread(target=update_or_create_certs)
    thread.start()

    generate_webhooks_secret(data)
    print('Webhooks secret successfully created.')

    generate_cronjob_token(data)
    print('Cronjob token successfully created.')

    create_config(data)
    print("Successfully create config for ejabberd.")

    if not start_ejabberd(first_start=True):
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

    try:
        update_permissions()
        print('Permissions created successfuly')
    except:
        print('Permissions was not created')

    return True, None


def install_cmd(request, data):
    success, error_message = start_installation_process(data)
    if not success:
        if is_ejabberd_started():
            stop_ejabberd()
        return success, error_message

    # block installation mode
    open(settings.INSTALLATION_LOCK, 'a').close()
    os.chmod(settings.INSTALLATION_LOCK, 0o444)

    return success, error_message


def create_circles(data):

    circle = Circle.objects.create(
        circle=data['host'],
        host=data['host'],
        name=settings.XMPP_SERVER_DEFAULT_GROUP_NAME,
        description=settings.XMPP_SERVER_DEFAULT_GROUP_DESCRIPTION,
        prefix=get_system_group_suffix(),
        all_users=True
    )
    circle.save()


def load_predefined_config():
    data = {}
    path = settings.PREDEFINED_CONFIG_FILE_PATH

    if os.path.exists(path):
        with open(path) as file:
            try:
                data = json.load(file)
            except:
                pass

    return data