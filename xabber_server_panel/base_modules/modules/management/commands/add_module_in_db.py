from django.core.management.base import BaseCommand
from django.conf import settings
from django.apps import apps
from django.core import management
from django.utils.timezone import now

from django.template.utils import get_app_template_dirs

from importlib import import_module

from xabber_server_panel.utils import update_app_list, reload_server
from xabber_server_panel.base_modules.config.models import Module
from xabber_server_panel.utils import check_versions
from xabber_server_panel.base_modules.config.utils import make_xmpp_config

import os


class Command(BaseCommand):
    help = 'Install or update module (without file operations)'

    def add_arguments(self, parser):
        parser.add_argument('module_name', type=str)
        parser.add_argument('version', type=str)
        parser.add_argument('--custom', action='store_true')
        parser.add_argument('--track', type=str, default='free')
        parser.add_argument('--description', type=str, default='')
        parser.add_argument('--refresh_token', type=str, default='')

    def handle(self, *args, **options):
        module_name = options['module_name'].lower()
        version = options['version'].lower()
        custom = options['custom']
        track = options['track']
        description = options['description']
        refresh_token = options['refresh_token']
        created = now().date()

        self._check_version(module_name, version, custom, track)

        self._install_module(module_name)

        self._after_install(
            module_name=module_name,
            version=version,
            custom=custom,
            track=track,
            description=description,
            refresh_token=refresh_token,
            created=created,
        )

        self.stdout.write(self.style.SUCCESS(f'Module "{module_name}" installed successfully'))

    def _install_module(self, module_name):
        app_name = f'modules.{module_name}'
        target_path = os.path.join(settings.MODULES_DIR, module_name)

        if not os.path.exists(target_path):
            raise Exception(f'Module "{module_name}" not found in MODULES_DIR')

        if not apps.is_installed(app_name):
            settings.INSTALLED_APPS += [app_name]
            update_app_list(settings.INSTALLED_APPS)

        # migrate db if module has migrations
        if os.path.exists(os.path.join(target_path, 'migrations', '__init__.py')):
            management.call_command('migrate', module_name, interactive=False)

        management.call_command('collectstatic', '--noinput', interactive=False)

    def _check_version(self, module_name, version, custom, track):
        module = Module.objects.filter(name=module_name).first()

        if module:
            if module.custom and not custom:
                raise Exception('You can not install original module over custom.')
            elif not module.custom and custom:
                raise Exception('You can not install custom module over original.')

            equals_ok = module.track == 'free' and track == 'paid'
            version_result = check_versions(module.version, version, equals_ok=equals_ok)

            if not version_result.get('success'):
                raise Exception(version_result.get('error'))

    def _after_install(self, module_name, version, custom, track, description, refresh_token, created):

        try:
            module_app = import_module('.apps', package=f'modules.{module_name}')
        except Exception:
            module_app = None

        verbose_name = ''
        root_page = False
        global_module = False

        if module_app:
            module_config = getattr(module_app, 'ModuleConfig', None)

            if module_config:
                verbose_name = getattr(module_config, 'verbose_name', module_name)
                root_page = getattr(module_config, 'root_page', False)
                global_module = getattr(module_config, 'global_module', False)

        Module.objects.update_or_create(
            name=module_name,
            defaults={
                'version': version,
                'verbose_name': verbose_name,
                'files': '',  # больше не используем
                'root_page': root_page,
                'global_module': global_module,
                'custom': custom,
                'track': track,
                'created': created,
                'description': description,
                'refresh_token': refresh_token,
            }
        )

        management.call_command('update_permissions')

        make_xmpp_config()
        get_app_template_dirs.cache_clear()
        reload_server()