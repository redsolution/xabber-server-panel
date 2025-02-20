from django.core import management
from django.contrib import messages
from django.conf import settings
from django.apps import apps
from django.template.utils import get_app_template_dirs

from importlib import import_module

from xabber_server_panel.utils import update_app_list, reload_server
from xabber_server_panel.base_modules.config.models import Module
from xabber_server_panel.utils import check_versions
from xabber_server_panel.base_modules.config.utils import make_xmpp_config

import tarfile
import shutil
import os
import re
from datetime import date


class ModuleUploader:

    def __init__(
        self,
        uploaded_file=None,
        custom=False,
        track='',
        description='',
        created=date.today(),
        refresh_token=''
    ):
        self.uploaded_file = uploaded_file
        self.custom = custom
        self.track = track
        self.description = description
        self.refresh_token = refresh_token
        self.created = created
        self.temp_extract_dir = os.path.join(settings.BASE_DIR, 'temp_extract')

    def handle_upload(self):
        try:
            if not self.uploaded_file:
                raise Exception('Uploaded file is None.')

            # Create temporary dir for unpack
            os.makedirs(self.temp_extract_dir, exist_ok=True)

            # Unpack archieve in temporary dir
            with tarfile.open(fileobj=self.uploaded_file, mode='r:gz') as tar:
                tar.extractall(self.temp_extract_dir)

            module_name, version = self._check_version()

            # Get nested dir inside 'panel'
            panel_path = os.path.join(self.temp_extract_dir, 'panel')
            server_path = os.path.join(self.temp_extract_dir, 'server')
            module_path = os.path.join(panel_path, module_name)

            if os.path.isdir(module_path):

                # Copy module in modules dir
                self._install_module(panel_path, module_name)

                # Copy server files if it exists
                self._install_server_files(server_path)

                # after installation actions
                self._after_install(module_name, version, server_path)
            else:
                raise Exception('Module folder is missed.')
        except Exception as e:
            # Delete temporary dir
            shutil.rmtree(self.temp_extract_dir, ignore_errors=True)
            raise

    def _install_module(self, panel_path, module_dir, ):

        app_name = 'modules.%s' % module_dir

        target_path = os.path.join(settings.MODULES_DIR, module_dir)
        module_path = os.path.join(panel_path, module_dir)

        if os.path.exists(target_path):
            shutil.rmtree(target_path)

        shutil.copytree(module_path, target_path)

        if not apps.is_installed(app_name):
            # Append app in settings.py
            settings.INSTALLED_APPS += [app_name]

            # update app list
            update_app_list(settings.INSTALLED_APPS)

        # migrate db if module has migrations
        if os.path.exists(os.path.join(target_path, 'migrations', '__init__.py')):
            management.call_command('migrate', module_dir, interactive=False)

        management.call_command('collectstatic', '--noinput', interactive=False)

    def _check_version(self):

        # read module spec
        spec_path = os.path.join(self.temp_extract_dir, 'module.spec')
        if os.path.exists(spec_path):
            with open(spec_path, 'r') as file:
                content = file.read()
        else:
            raise Exception('Module spec information is missed.')

        name_match = re.search(r'NAME\s*=\s*([^\n]+)', content)
        version_match = re.search(r'VERSION\s*=\s*([^\n]+)', content)

        if name_match and version_match:
            module_name = name_match.group(1).strip().lower()
            version = version_match.group(1).strip().lower()
        else:
            raise Exception('Module spec is incorrect.')

        module = Module.objects.filter(name=module_name).first()
        if module:
            if module.custom and not self.custom:
                raise Exception('You can not install original module over custom.')
            elif not module.custom and self.custom:
                raise Exception('You can not install custom module over original.')

            # check version if module already installed
            equals_ok = module.track == 'free' and self.track == 'paid'
            version_result = check_versions(module.version, version, equals_ok=equals_ok)
            if not version_result.get('success'):
                raise Exception(version_result.get('error'))

        return module_name, version

    def _install_server_files(self, server_path):

        if not os.path.exists(settings.XMPP_SERVER_EXTERNAL_MODULES_DIR):
            os.mkdir(settings.XMPP_SERVER_EXTERNAL_MODULES_DIR)

        if os.path.exists(server_path):

            # copy list files
            for filename in os.listdir(server_path):
                path_from = os.path.join(server_path, filename)
                path_to = os.path.join(settings.XMPP_SERVER_EXTERNAL_MODULES_DIR, filename)

                # delete existing file
                if os.path.exists(path_to):
                    os.remove(path_to)

                shutil.copy(path_from, path_to)

    def _after_install(self, module_name, version, server_path):

        # get module verbose name
        try:
            module_app = import_module('.apps', package='modules.%s' % module_name)
        except:
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

        # prepare server files paths
        if os.path.exists(server_path):
            server_files = ','.join(os.listdir(server_path))
        else:
            server_files = ''

        # update module info
        Module.objects.update_or_create(
            name=module_name,
            defaults={
                'version': version,
                'verbose_name': verbose_name,
                'files': server_files,
                'root_page': root_page,
                'global_module': global_module,
                'custom': self.custom,
                'track': self.track,
                'created': self.created,
                'description': self.description,
                'refresh_token': self.refresh_token,
            }
        )

        # create permissions for new modules
        management.call_command('update_permissions')

        # Delete temporary dir
        shutil.rmtree(self.temp_extract_dir)

        make_xmpp_config()
        get_app_template_dirs.cache_clear()

        reload_server()