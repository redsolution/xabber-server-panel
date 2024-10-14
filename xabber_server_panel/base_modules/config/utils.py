from django.template.loader import render_to_string
from django.conf import settings
from django.apps import apps
from django.urls import reverse, resolve, NoReverseMatch
import stat

from xabber_server_panel.base_modules.config.models import VirtualHost, Module
from xabber_server_panel.utils import is_ejabberd_started
from xabber_server_panel.base_modules.config.models import BaseXmppModule, BaseXmppOption, check_vhost, DiscoUrls

import copy
import os
import requests
from importlib import util, import_module


# ========== XABBERSERVER CONFIG ==============

def get_value(key, value, level):

    """ Helper function to format key-value pairs with proper indentation """

    shift = '  ' * level
    result = ''

    # Handle lists
    if isinstance(value, list):
        result += "{}:\n".format(key)
        for el in value:
            if isinstance(el, dict):
                for key, value in el.items():
                    result += shift + "  - \"%s\" : \"%s\"\n" % (key, value)
            else:
                result += shift + "  - {}\n".format(el)

    # Handle dictionaries
    elif isinstance(value, dict):
        if value:
            result += "{}:\n".format(key)
            for subkey, subvalue in value.items():
                result += get_value(subkey, subvalue, level + 1)
        else:
            result += "{}: {}\n".format(key, "{}")

    # Handle other types
    else:
        result += "{}: {}\n".format(key, value)
    return shift + result


def get_modules_config():

    """ Returns list of xmpp module or xrmpp option configs """

    configs = []

    # loop over all apps and check xmpp_server_config
    for app in apps.app_configs.values():
        # Check if the module exists before attempting to import it
        module_spec = util.find_spec(".config", package=app.name)
        if module_spec:
            module_config = import_module('.config', package=app.name)
            if hasattr(module_config, 'get_xmpp_server_config'):
                config_list = module_config.get_xmpp_server_config()
                configs += [config.get_config() for config in config_list if isinstance(config, (BaseXmppModule, BaseXmppOption))]
    return configs


def make_xmpp_config():
    # Get module configurations from settings
    module_configs = get_modules_config()

    # Define the path for the Ejabberd configuration file
    config_path = os.path.join(settings.XMPP_SERVER_CONFIG_PATH, settings.XMPP_SERVER_MODULES_CONFIG_FILE)

    # Get all virtual hosts
    hosts = VirtualHost.objects.all()

    # Initialize dictionaries to store global and per-host configurations
    global_options = {}
    host_config = {host.name: {} for host in hosts}
    append_host_config = copy.deepcopy(host_config)

    # Loop through module configurations
    for module_config in module_configs:
        try:
            # Check if the configuration is a module
            if module_config.get('type') == "module":
                # Check if the module is for global or a specific virtual host
                if module_config.get('vhost') == "global":
                    # Update all host configurations with the module options
                    for config in append_host_config.values():
                        config.update({module_config.get('name'): module_config.get('module_options')})
                else:
                    # Update the specific virtual host configuration with the module options
                    for key, value in append_host_config.items():
                        if key == module_config.get('vhost'):
                            value.update({module_config.get('name'): module_config.get('module_options')})

            # Check if the configuration is an option
            elif module_config.get('type') == "option":
                # Check if the option is for global or a specific virtual host
                if module_config.get('vhost') == "global":
                    # Update global options with the option value
                    global_options.update({module_config.get('name'): module_config.get('value')})
                else:
                    # Update the specific virtual host configuration with the option value
                    host_config.get(module_config.get('vhost')).update(
                        {module_config.get('name'): module_config.get('value')})

        except Exception as e:
            # Print any exceptions that occur, but continue with the next iteration
            print(e)
            pass

    # Write the configurations to the Ejabberd configuration file
    if os.path.islink(config_path):
        target_path = os.readlink(config_path)
    else:
        target_path = config_path

    with open(target_path, "w") as f:
        # Write global options to the file
        for key, value in global_options.items():
            f.write(get_value(key, value, level=0))

        # Write host configurations to the file
        config_values = [config for config in host_config.values() if config]
        if config_values:
            f.write("host_config:\n")
            for key, value in host_config.items():
                if value:
                    f.write('  "{}":\n'.format(key))
                    for key1, val1 in value.items():
                        f.write(get_value(key1, val1, level=3))

        # Write append_host_config to the file
        f.write("append_host_config:\n")
        for key, value in append_host_config.items():
            if value:
                f.write('  "{}":\n'.format(key) + "    modules:\n")
                for key1, val1 in value.items():
                    f.write(get_value(key1, val1, level=3))
            else:
                f.write('  "{}":\n'.format(key) + "    modules: []\n")

    # Change the permissions
    os.chmod(target_path, desired_permissions)


def update_vhosts_config(hosts=None):
    template = 'config/hosts_template.yml'

    if not hosts:
        hosts = VirtualHost.objects.all()

    if not hosts:
        return

    vhosts_config_path = os.path.join(settings.XMPP_SERVER_CONFIG_PATH, settings.XMPP_SERVER_VHOSTS_CONFIG_FILE)
    xml = render_to_string(template, {'hosts': hosts})
    create_config_file(vhosts_config_path, xml)


def update_ejabberd_config():
    update_vhosts_config()
    make_xmpp_config()


def get_mod_disco_urls_items():
    configs = {}
    hosts = VirtualHost.objects.all()
    disco_urls_list = DiscoUrls.objects.all()

    def _add_config_items(host, items):
        if host not in configs:
            configs[host] = {}

        # set host data
        for key, value in items.items():
            configs[host][key] = value

    for obj in disco_urls_list:
        if check_vhost(obj.host):
            # set host dict
            if obj.host == 'global':
                for host in hosts:
                    _add_config_items(host.name, obj.get_items())
            else:
                _add_config_items(obj.host, obj.get_items())
    return configs


# Combine the desired permissions for config
desired_permissions = (
        stat.S_IRWXU |  # Owner: read, write, execute
        stat.S_IRGRP |  # Group: read
        stat.S_IXGRP |  # Group: execute
        stat.S_IROTH |  # Others: read
        stat.S_IXOTH |  # Others: execute
        stat.S_IWOTH  # Others: write
)


def create_config_file(path, content=""):
    if os.path.islink(path):
        target_path = os.readlink(path)
    else:
        target_path = path

    with open(target_path, 'w') as f:
        # Write an empty string to the file
        f.write(content)

    # Change the permissions
    os.chmod(path, desired_permissions)


# ========== DNS REQUESTS ===============

def check_hosts_dns():
    unchecked_hosts = VirtualHost.objects.filter(srv_records=False)

    srv_records_hosts = []
    for host in unchecked_hosts:
        records = get_dns_records(host.name)
        if not 'error' in records:
            srv_records_hosts += [host.id]

    unchecked_hosts = VirtualHost.objects.filter(cert_records=False)
    cert_records_hosts = []
    for host in unchecked_hosts:
        records = get_dns_records(host.name, type='A')
        if settings.CHALLENGE_RECORD in records.get('_acme-challenge', []):
            cert_records_hosts += [host.id]

    # update checked hosts
    VirtualHost.objects.filter(id__in=srv_records_hosts).update(srv_records=True)
    VirtualHost.objects.filter(id__in=cert_records_hosts).update(cert_records=True)


def get_dns_records(domain, type='SRV'):

    """ Request srv records from dns service """

    records = {}

    record_types = {
        'A': ['_acme-challenge', 'xabber'],
        'SRV': ['_xmpp-client._tcp', '_xmpp-server._tcp']
    }

    for service in record_types.get(type, []):
        try:
            response = requests.get(
                "%s?name=%s.%s&type=%s" % (settings.DNS_SERVICE, service, domain, type),
                headers={"accept": "application/dns-json"},
                timeout=2
            )

            # Check if response is successful
            if response.status_code == 200:
                data = response.json()
                if 'Answer' in data:
                    records[service] = []
                    for record in data['Answer']:
                        if type == 'SRV':
                            if 'data' in record and ' ' in record['data']:  # Check if data field contains SRV record
                                parts = record['data'].split()
                                if len(parts) == 4:
                                    records[service].append({
                                        'priority': int(parts[0]),
                                        'weight': int(parts[1]),
                                        'port': int(parts[2]),
                                        'target': parts[3]
                                    })
                        else:
                            records[service] += [record['data']]
                else:
                    records['error'] = "No %s records found for %s.%s" % (type, service, domain)
            else:
                records['error'] = "HTTP Error: %s" % response.status
        except requests.Timeout:
            # Handle timeout error
            records['error'] = "Timeout occurred while making the request."
        except requests.RequestException as e:
            # Handle other client errors
            records['error'] = "An error occurred while making the request: %s" % e
        except Exception as e:
            records['error'] = "Error: %s" % e

    return records


# ========= OTHER ===============
def check_modules():

    """ delete old modules objects """

    modules = get_modules()

    Module.objects.exclude(name__in=modules).delete()


def get_modules():
    if os.path.isdir(settings.MODULES_DIR):
        return os.listdir(settings.MODULES_DIR)
    return []


def get_create_views():

    """ Loop over installed modules and return list of urls to create objects """

    modules = get_modules()
    create_data_list = []
    for module in modules:

        # get apps file to append module verbose_name in data
        try:
            module_app = import_module('.apps', package='modules.%s' % module)
        except:
            module_app = None

        if module_app:
            module_config = getattr(module_app, 'ModuleConfig', None)

            if module_config:
                create_views_names = getattr(module_config, 'create_views_names', [])
                if create_views_names and isinstance(create_views_names, list):
                    for name in create_views_names:
                        try:
                            url = reverse('%s:%s' % (module, name))
                        except NoReverseMatch:
                            continue

                        resolver_match = resolve(url)
                        if resolver_match:
                            # Check if the resolved view is a class-based view
                            if hasattr(resolver_match.func, 'view_class'):
                                # If it's a class-based view, get the view class
                                view = resolver_match.func.view_class
                            else:
                                # If it's a function-based view, get the view function
                                view = resolver_match.func

                            create_data_list += [
                                {
                                    'url': url,
                                    'title': getattr(view, 'create_title', ''),
                                    'subtitle': getattr(view, 'create_subtitle', ''),
                                }
                            ]

    return create_data_list


def check_hosts(api):

    """
        Check registered users and create
        if it doesn't exist in django db
    """

    if is_ejabberd_started():
        response = api.get_vhosts()
        registered_hosts = response.get('vhosts')

        if response and not response.get('errors') and registered_hosts is not None:

            # Get a list of existing usernames from the User model
            existing_hosts = VirtualHost.objects.values_list('name', flat=True)

            # Filter the user_list to exclude existing usernames
            unknown_hosts = [host for host in registered_hosts if host not in existing_hosts]

            # create in db unknown users
            if unknown_hosts:
                hosts_to_create = [
                    VirtualHost(
                        name=host,
                    )
                    for host in unknown_hosts
                ]
                VirtualHost.objects.bulk_create(hosts_to_create)

            # get unregistered users in db and delete
            hosts_to_delete = VirtualHost.objects.exclude(name__in=registered_hosts)
            if hosts_to_delete:
                hosts_to_delete.delete()