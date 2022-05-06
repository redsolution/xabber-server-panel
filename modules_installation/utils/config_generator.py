import importlib
import os
import copy
from django.conf import settings
from django.apps import apps
from virtualhost.models import VirtualHost
from modules_installation.models import BaseXmppModule, BaseXmppOption


def update_modules_config_file():
    configs = []
    for name, app in apps.app_configs.items():
        if hasattr(app.module, 'config') and app.module.config is not None:
            configs.append(app.module.config.get_module_config())
    config_list = '\n'.join(configs)
    file = open(os.path.join(settings.EJABBERD_CONFIG_PATH,
                             settings.EJABBERD_MODULES_CONFIG_FILE), 'w+')
    file.write(config_list)
    file.close()


def get_modules_config():
    configs = []
    for app in apps.app_configs.values():
        try:
            module_config = importlib.import_module(".config", package=app.name)
            configs.extend(module_config.get_xmpp_server_config())
        except Exception:
            pass
    return [el.get_config() for el in configs if isinstance(el, BaseXmppModule) or isinstance(el, BaseXmppOption)]


def make_xmpp_config():
    module_configs = get_modules_config()
    config_path = os.path.join(settings.EJABBERD_CONFIG_PATH, settings.EJABBERD_MODULES_CONFIG_FILE)
    vhosts = VirtualHost.objects.all()
    global_options = {}
    host_config = {el.name: {} for el in vhosts}
    append_host_config = copy.deepcopy(host_config)
    for config in module_configs:
        try:
            if config.get('type') == "module":
                if config.get('vhost') == "global":
                    [el.update({config.get('name'): config.get('module_options')}) for el in
                     append_host_config.values()]
                else:
                    [value.update({config.get('name'): config.get('module_options')}) for key, value in
                     append_host_config.items() if key == config.get('vhost')]
            if config.get('type') == "option":
                if config.get('vhost') == "global":
                    global_options.update({config.get('name'): config.get('value')})
                else:
                    host_config.get(config.get('vhost')).update({config.get('name'): config.get('value')})
        except Exception:
            pass

    with open(config_path, "w") as f:
        for key, value in global_options.items():
            f.write(get_value(key, value, level=0))

        if [el for el in host_config.values() if el]:
            f.write("host_config:\n")
            for key, value in host_config.items():
                if value:
                    f.write('  "{}":\n'.format(key))
                    for key1, val1 in value.items():
                        f.write(get_value(key1, val1, level=3))

        f.write("append_host_config:\n")
        for key, value in append_host_config.items():
            if value:
                f.write('  "{}":\n'.format(key) + "    modules:\n")
                for key1, val1 in value.items():
                    f.write(get_value(key1, val1, level=3))
            else:
                f.write('  "{}":\n'.format(key) + "    modules: []\n")


def get_value(key, value, level):
    shift = '  ' * level
    result = ''
    if isinstance(value, list):
        result += "{}:\n".format(key)
        for el in value:
            result += shift + "  - {}\n".format(el)
    elif isinstance(value, dict):
        if value:
            result += "{}:\n".format(key)
            for subkey, subvalue in value.items():
                result += get_value(subkey, subvalue, level + 1)
        else:
            result += "{}: {}\n".format(key, "{}")
    else:
        result += "{}: {}\n".format(key, value)
    return shift + result

