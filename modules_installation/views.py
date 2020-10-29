import os
import tarfile
from collections import OrderedDict
from django.views.generic import TemplateView, View
from django.urls import reverse
from django.http import HttpResponseRedirect, Http404
from django.conf import settings
from django.apps import apps
from django.core import management

from modules_installation.templatetags.modules_tags import get_modules
from xmppserverui.mixins import PageContextMixin
from virtualhost.models import VirtualHost
from .forms import UploadModuleFileForm
from .mixins import ModuleAccessMixin

SETTINGS_TAB_MODULES = 'modules'


class BasePluginView(ModuleAccessMixin, View):
    pass


class ManageModulesView(PageContextMixin, TemplateView):
    page_section = 'modules'
    template_name = 'modules/modules_list.html'

    def get(self, request, *args, **kwargs):
        modules = get_modules()
        print(modules)

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
            print(request.FILES['file'])
            error = self.handle_uploaded_file(request.FILES['file'])
            if error:
                return self.render_to_response({"form": form, 'error': error})
            else:
                return HttpResponseRedirect(reverse('modules:modules-list'))
        return self.render_to_response({"form": form})

    def handle_uploaded_file(self, f):
        if os.path.exists(settings.MODULES_DIR):
            try:
                tar = tarfile.open(fileobj=f.file, mode='r:gz')
                tar.extractall(settings.MODULES_DIR)
                tar.close()
            except tarfile.ReadError:
                return 'Module files cannot be extracted from this file'

            for folder in os.listdir(settings.MODULES_DIR):
                folder_path = os.path.join(settings.MODULES_DIR, folder)
                if os.path.isdir(folder_path) and os.path.isfile(os.path.join(folder_path,  '__init__.py')):
                    new_app_name = "modules." + folder
                    if not apps.is_installed(new_app_name):
                        try:
                            apps.app_configs = OrderedDict()
                            settings.INSTALLED_APPS += (new_app_name,)
                            apps.apps_ready = apps.models_ready = apps.loading = apps.ready = False
                            apps.clear_cache()
                            apps.populate(settings.INSTALLED_APPS)

                            management.call_command('migrate', folder, interactive=False)
                        except:
                            pass


