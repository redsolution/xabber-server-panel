import shutil
import os
import re
import tarfile
from collections import OrderedDict
from importlib import import_module
from django.views.generic import TemplateView, View
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.conf import settings
from django.apps import apps
from django.core import management
from django.shortcuts import redirect
from modules_installation.templatetags.modules_tags import get_modules
from virtualhost.templatetags.virtualhost_tags import update_module_permissions_names
from virtualhost.views import update_module_permissions
from xmppserverui.mixins import PageContextMixin
from virtualhost.models import VirtualHost
from .forms import UploadModuleFileForm
from .mixins import ModuleAccessMixin
from .utils.config_generator import make_xmpp_config
from django.template.utils import get_app_template_dirs

SETTINGS_TAB_MODULES = 'modules'


class BaseModuleView(ModuleAccessMixin, View):
    pass


class ManageModulesView(PageContextMixin, TemplateView):
    page_section = 'modules'
    template_name = 'modules/modules_list.html'

    def get(self, request, *args, **kwargs):
        modules = get_modules()

        vhosts = VirtualHost.objects.all()
        context = {
            'modules': modules,
            'virtual_hosts': vhosts,
            'active_tab': SETTINGS_TAB_MODULES
        }

        return self.render_to_response(context)


class UploadModuleFileView(PageContextMixin, TemplateView):
    page_section = 'modules_upload'
    template_name = 'modules/upload_module.html'

    def get(self, request, *args, **kwargs):
        form = UploadModuleFileForm()
        context = {
            'form': form,
        }
        return self.render_to_response(context=context)

    def post(self, request, *args, **kwargs):
        form = UploadModuleFileForm(request.POST, request.FILES)
        if form.is_valid():
            error = self.handle_uploaded_file(request.FILES['file'])
            if error:
                return self.render_to_response({"form": form, 'error': error})
            else:
                return HttpResponseRedirect(reverse('server:modules-list'))
        return self.render_to_response({"form": form})

    def handle_uploaded_file(self, f):
        try:
            tar = tarfile.open(fileobj=f.file, mode='r:gz')
            subdir_and_files = []
            for member in tar.getmembers():
                if member.path.startswith('panel/'):
                    member.path = member.path[len('panel/'):]
                    subdir_and_files.append(member)
            tar.extractall(settings.MODULES_DIR, members=subdir_and_files)
            tar.close()
        except tarfile.ReadError:
            return 'Module files cannot be extracted from this file'

        if os.path.exists(settings.MODULES_DIR):
            for folder in os.listdir(settings.MODULES_DIR):
                folder_path = os.path.join(settings.MODULES_DIR, folder)
                if os.path.isdir(folder_path):
                    new_app_name = "modules." + folder
                    if not apps.is_installed(new_app_name):
                        try:
                            apps.app_configs = OrderedDict()
                            settings.INSTALLED_APPS += (new_app_name,)
                            apps.apps_ready = apps.models_ready = apps.loading = apps.ready = False
                            apps.clear_cache()
                            apps.populate(settings.INSTALLED_APPS)
                            if os.path.exists(os.path.join(folder_path, 'migrations', '__init__.py')):
                                management.call_command('migrate', folder, interactive=False)
                            management.call_command('collectstatic', '--noinput', interactive=False)
                            update_module_permissions()
                            update_module_permissions_names()
                            make_xmpp_config()
                            get_app_template_dirs.cache_clear()
                            try:
                                if os.environ.get("XABBER_PANEL_PF"):
                                    import signal
                                    pid = open(os.environ.get("XABBER_PANEL_PF")).read()
                                    os.kill(int(pid), signal.SIGHUP)
                                else:
                                    os.utime(os.path.join(settings.BASE_DIR, 'xmppserverui/wsgi.py'), times=None)
                            except:
                                pass
                        except Exception as err:
                            rollback_install(new_app_name, folder_path)
                            return 'Something went wrong during the installation of this module: {}'.format(err)
            return ''


def module_view_detail(request, module, path):
    try:
        urlconf = import_module("modules." + module + '.urls')
        patterns = getattr(urlconf, 'urlpatterns')
        path_patterns = list(filter(lambda x: re.match(str(x.pattern), path), patterns))
        if len(path_patterns):
            return path_patterns[0].callback(request)
        else:
            return redirect('server:dashboard')
    except ImportError or AttributeError:
        return redirect('server:dashboard')


def rollback_install(new_app_name, folder_path):
    try:
        settings.INSTALLED_APPS.remove(new_app_name)
        shutil.rmtree(folder_path)
    except Exception:
        pass
