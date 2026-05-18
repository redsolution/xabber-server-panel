from django.core import management
from django.conf import settings
from django.apps import apps
from django.template.utils import get_app_template_dirs
from django.db.migrations.recorder import MigrationRecorder

from importlib import import_module

from xabber_server_panel.utils import update_app_list, reload_server
from xabber_server_panel.base_modules.config.models import Module
from xabber_server_panel.utils import check_versions
from xabber_server_panel.base_modules.config.utils import make_xmpp_config

import tarfile
import shutil
import os
import re
import tempfile
from datetime import date


class ModuleInstaller:

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
        self.rollback_dir = None
        self.module_name = None
        self.app_name = None
        self.target_path = None
        self.module_existed = False
        self.app_was_installed = False
        self.previous_module_data = None
        self.previous_migration = None
        self.migrations_attempted = False
        self.module_backup_path = None
        self.server_file_backups = {}
        self.server_dir_existed = False

    def handle_install(self):
        try:
            if not self.uploaded_file:
                raise Exception('Uploaded file is None.')

            # Create temporary dir for unpack
            os.makedirs(self.temp_extract_dir, exist_ok=True)

            # Unpack archieve in temporary dir
            with tarfile.open(fileobj=self.uploaded_file, mode='r:gz') as tar:
                self._safe_extract(tar, self.temp_extract_dir)

            module_name, version = self._check_version()

            # Get nested dir inside 'panel'
            panel_path = os.path.join(self.temp_extract_dir, 'panel')
            server_path = os.path.join(self.temp_extract_dir, 'server')
            module_path = os.path.join(panel_path, module_name)

            if os.path.isdir(module_path):
                self._prepare_rollback(module_name, server_path)

                # Copy module in modules dir
                self._install_module(panel_path, module_name)

                # Copy server files if it exists
                self._install_server_files(server_path)

                # after installation actions
                self._after_install(module_name, version, server_path)
            else:
                raise Exception('Module folder is missed.')
        except Exception as e:
            self._rollback_install(e)
            raise
        finally:
            # Delete temporary dir
            shutil.rmtree(self.temp_extract_dir, ignore_errors=True)
            self._delete_rollback_backup()

    def _safe_extract(self, tar, path):
        target_dir = os.path.realpath(path)

        for member in tar.getmembers():
            member_path = os.path.realpath(os.path.join(path, member.name))
            if os.path.commonpath([target_dir, member_path]) != target_dir:
                raise Exception('Archive contains unsafe paths.')

            if member.issym() or member.islnk():
                link_path = os.path.realpath(
                    os.path.join(os.path.dirname(member_path), member.linkname)
                )
                if os.path.commonpath([target_dir, link_path]) != target_dir:
                    raise Exception('Archive contains unsafe links.')

        tar.extractall(path)

    def _prepare_rollback(self, module_name, server_path):
        self.module_name = module_name
        self.app_name = 'modules.%s' % module_name
        self.target_path = os.path.join(settings.MODULES_DIR, module_name)
        self.module_existed = os.path.exists(self.target_path)
        self.app_was_installed = apps.is_installed(self.app_name)
        self.previous_module_data = Module.objects.filter(name=module_name).values().first()
        self.previous_migration = self._get_last_applied_migration(module_name)
        self.server_dir_existed = os.path.exists(settings.XMPP_SERVER_EXTERNAL_MODULES_DIR)
        self.rollback_dir = tempfile.mkdtemp(prefix='module_install_rollback_', dir=settings.BASE_DIR)

        if self.module_existed:
            self.module_backup_path = os.path.join(self.rollback_dir, 'panel', module_name)
            shutil.copytree(self.target_path, self.module_backup_path)

        if os.path.exists(server_path):
            backup_dir = os.path.join(self.rollback_dir, 'server')
            os.makedirs(backup_dir, exist_ok=True)

            for filename in os.listdir(server_path):
                path_to = os.path.join(settings.XMPP_SERVER_EXTERNAL_MODULES_DIR, filename)
                backup_path = os.path.join(backup_dir, filename)

                if os.path.exists(path_to):
                    shutil.copy2(path_to, backup_path)
                    self.server_file_backups[filename] = backup_path
                else:
                    self.server_file_backups[filename] = None

    def _get_last_applied_migration(self, module_name):
        migration = MigrationRecorder.Migration.objects.filter(
            app=module_name
        ).order_by('id').last()
        if migration:
            return migration.name
        return 'zero'

    def _rollback_install(self, original_error):
        if not self.module_name:
            return

        rollback_steps = [
            self._rollback_migrations,
            self._rollback_module_files,
            self._rollback_server_files,
            self._rollback_module_object,
            self._rollback_installed_apps,
            self._refresh_after_rollback,
        ]
        rollback_errors = []

        for step in rollback_steps:
            try:
                step()
            except Exception as rollback_error:
                rollback_errors.append(str(rollback_error))

        if rollback_errors:
            raise Exception(
                'Module installation failed: %s Rollback failed: %s' % (
                    original_error,
                    '; '.join(rollback_errors)
                )
            )

    def _rollback_migrations(self):
        if not self.migrations_attempted:
            return

        management.call_command(
            'migrate',
            self.module_name,
            self.previous_migration,
            interactive=False
        )

    def _rollback_module_files(self):
        if self.module_existed and self.module_backup_path:
            shutil.rmtree(self.target_path, ignore_errors=True)
            shutil.copytree(self.module_backup_path, self.target_path)
        else:
            shutil.rmtree(self.target_path, ignore_errors=True)

    def _rollback_server_files(self):
        for filename, backup_path in self.server_file_backups.items():
            path_to = os.path.join(settings.XMPP_SERVER_EXTERNAL_MODULES_DIR, filename)

            if backup_path:
                os.makedirs(os.path.dirname(path_to), exist_ok=True)
                shutil.copy2(backup_path, path_to)
            elif os.path.exists(path_to):
                os.remove(path_to)

        if not self.server_dir_existed and os.path.isdir(settings.XMPP_SERVER_EXTERNAL_MODULES_DIR):
            try:
                os.rmdir(settings.XMPP_SERVER_EXTERNAL_MODULES_DIR)
            except OSError:
                pass

    def _rollback_module_object(self):
        Module.objects.filter(name=self.module_name).delete()

        if not self.previous_module_data:
            return

        Module.objects.create(**self.previous_module_data)

    def _rollback_installed_apps(self):
        if self.app_was_installed:
            if self.app_name not in settings.INSTALLED_APPS:
                settings.INSTALLED_APPS += [self.app_name]
        elif self.app_name in settings.INSTALLED_APPS:
            settings.INSTALLED_APPS.remove(self.app_name)

        update_app_list(settings.INSTALLED_APPS)

    def _refresh_after_rollback(self):
        management.call_command('update_permissions')
        make_xmpp_config()
        get_app_template_dirs.cache_clear()

    def _delete_rollback_backup(self):
        if self.rollback_dir:
            shutil.rmtree(self.rollback_dir, ignore_errors=True)

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
            self.migrations_attempted = True
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
