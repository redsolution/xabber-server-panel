import os
from django.conf import settings
from django.apps import apps


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
