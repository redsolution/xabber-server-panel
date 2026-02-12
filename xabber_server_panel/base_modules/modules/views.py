from django.shortcuts import reverse, Http404, loader
from django.views.generic import TemplateView, View
from django.http import HttpResponseRedirect, JsonResponse
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core import management
from django.apps import apps
from django.utils.dateparse import parse_datetime

from jid_validation.utils import validate_jid

from xabber_server_panel.base_modules.config.models import Module, DiscoUrls
from xabber_server_panel.base_modules.config.utils import make_xmpp_config
from xabber_server_panel.utils import update_app_list, reload_server
from xabber_server_panel.base_modules.users.decorators import permission_admin
from xabber_server_panel.api.api import PluginsApi, XabberServicesApi
from xabber_server_panel.base_modules.modules.utils import request_license_key

from .module_installer import ModuleInstaller
from .models import XServicesToken
from .utils import get_available_modules, get_installed_modules, get_plugins_prices, PluginsPriceCollector, get_installed_tracks

from abc import ABC, abstractmethod
from urllib.parse import urljoin

import shutil
import os

XSERVICES_PLUGINS_SUBSCRIBE_URL = urljoin(settings.XABBER_SERVICES_UI_URL, '/#/plugins/subscribe/')


class Installed(LoginRequiredMixin, TemplateView):
    template_name = 'modules/installed.html'

    @permission_admin
    def get(self, request, *args, **kwargs):
        plugins_api = PluginsApi(request)

        available_modules = plugins_api.get_plugins()
        if not plugins_api.errors:
            installed_modules = get_installed_modules(available_modules)
        else:
            installed_modules = []
        
        context = {
            'installed_modules': installed_modules,
            'xservices_plugins_subscribe_url': XSERVICES_PLUGINS_SUBSCRIBE_URL
        }
        return self.render_to_response(context)


class Catalogue(LoginRequiredMixin, TemplateView):
    template_name = 'modules/catalogue.html'

    @permission_admin
    def get(self, request, *args, **kwargs):
        plugins_api = PluginsApi(request)
        xservices_api = XabberServicesApi(request)

        available_modules = plugins_api.get_plugins()
        if not plugins_api.errors:
            available_modules = get_available_modules(available_modules)
            installed_tracks = get_installed_tracks()
        else:
            available_modules= []
            installed_tracks = {}

        purchased_modules = []
        result = request_license_key(request)
        if result.get('success'):
            license_key = result.get('key')
            if license_key:
                purchased_modules = plugins_api.get_purchased_plugins(license_key)

        plugin_price_collector = PluginsPriceCollector(xservices_api)
        xservices_plugins = plugin_price_collector.get_prices()
        
        context = {
            'available_modules': available_modules,
            "installed_tracks": installed_tracks,
            'xservices_plugins': xservices_plugins,
            'purchased_modules': purchased_modules,
            'xservices_plugins_subscribe_url': XSERVICES_PLUGINS_SUBSCRIBE_URL
        }

        if request.is_ajax():
            html = loader.render_to_string('modules/parts/modules_data_catalogue.html', context, request)
            response_data = {
                'html': html
            }
            return JsonResponse(response_data)
        return self.render_to_response(context)
    

class Upload(LoginRequiredMixin, TemplateView):
    template_name = 'modules/upload.html'

    @permission_admin
    def get(self, request, *args, **kwargs):
        context = {}
        return self.render_to_response(context)

    @permission_admin
    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')

        if uploaded_file:
            try:
                module_installer = ModuleInstaller(
                    uploaded_file=uploaded_file,
                    custom=True
                )
                module_installer.handle_install()
                messages.success(self.request, 'Module installed successfully.')
                return HttpResponseRedirect(reverse('modules:root'))
            except Exception as e:
                messages.error(self.request, e)

        return HttpResponseRedirect(reverse('modules:upload'))
    

class License(LoginRequiredMixin, TemplateView):
    template_name = 'modules/license.html'

    @permission_admin
    def get(self, request, *args, **kwargs):
        context = {}
        return self.render_to_response(context)
    

class Detail(LoginRequiredMixin, TemplateView):
    template_name = 'modules/detail.html'

    @permission_admin
    def get(self, request, module_name, track, *args, **kwargs):
        
        purchased_modules = self._get_purchased_modules()

        module = self._get_module_data(module_name, track)

        installed_tracks = get_installed_tracks()

        # Get modules prices list
        xservices_api = XabberServicesApi(request)
        plugin_price_collector = PluginsPriceCollector(xservices_api)
        xservices_plugins = plugin_price_collector.get_prices()
        
        context = {
            "installed_tracks": installed_tracks,
            'xservices_plugins': xservices_plugins,
            'purchased_modules': purchased_modules,
            'xservices_plugins_subscribe_url': XSERVICES_PLUGINS_SUBSCRIBE_URL,
            'module': module
        }

        return self.render_to_response(context)
    
    def _get_purchased_modules(self):
        # Request purchased modules
        plugins_api = PluginsApi(self.request)
        purchased_modules = []
        result = request_license_key(self.request)
        if result.get('success'):
            license_key = result.get('key')
            
            purchased_modules = plugins_api.get_purchased_plugins(license_key)

        return purchased_modules
    
    def _get_module_data(self, module_name, track):
        plugins_api = PluginsApi(self.request)

        # get module data from available modules
        modules_data = plugins_api.get_plugins(data={'name': module_name})
        if not plugins_api.errors:
            available_modules = get_available_modules(modules_data)            
        else:
            available_modules = []

        modules_filtered = list(filter(lambda x: x.get('name') == module_name and x.get('track') == track, available_modules))
        if not modules_filtered:
            raise Http404
        
        module = modules_filtered[0]
        return module
    

class DownloadModuleBase(LoginRequiredMixin, View, ABC):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugins_api = None
        self.refresh_token = ''
    
    def _download_module(self, release_id, created, description):
        if self.plugins_api:
            try:
                self.plugins_api.download_release(release_id)
                if self.plugins_api.raw_response.ok:
                    module_installer = ModuleInstaller(
                        uploaded_file=self.plugins_api.raw_response.raw,
                        track=self.track,
                        created=created,
                        description=description,
                        refresh_token=self.refresh_token
                    )
                    module_installer.handle_install()
                    messages.success(self.request, 'Module installed successfully.')
                elif self.plugins_api.raw_response.status_code == 403:
                    raise Exception('You have no access to this plugin.')
                elif self.plugins_api.raw_response.status_code == 401:
                    raise Exception('Not authenticated.')
                elif self.plugins_api.raw_response.status_code == 400:
                    raise Exception('Malformed data.')
                else:
                    raise Exception('Service is not available.')
            except Exception as e:
                messages.error(self.request, str(e))
        else:
            messages.error(self.request, 'Installation error.')

    @abstractmethod
    def _handle_download(self, *args, **kwargs):
        pass

    @property
    @abstractmethod
    def track(self):
        pass


class DownloadModuleFree(DownloadModuleBase):

    @permission_admin
    def get(self, request, module_name, **kwargs):

        self.plugins_api = PluginsApi(request)

        module = Module.objects.filter(name=module_name).exclude(refresh_token='').first()
        if module and module.refresh_token:
            self.refresh_token = module.refresh_token

        self._handle_download(module_name)

        return HttpResponseRedirect(reverse('modules:root'))
    
    def _handle_download(self, module_name):
        available_modules = self.plugins_api.get_plugins()

        module_data = available_modules.get(module_name, {}).get(self.track, {})
        release_id = module_data.get('release_id')

        if release_id:

            self._download_module(
                release_id,
                module_data.get('created'),
                module_data.get('description')
            )
        else:
            # If no URL is provided, return an error message or a 400 Bad Request.
            messages.error(self.request, "There is no available modules to update.")

    @property
    def track(self):
        return 'free'
    

class DownloadModulePaid(DownloadModuleBase):
    license_key = ''

    @permission_admin
    def get(self, request, module_name, **kwargs):

        self.plugins_api = PluginsApi(request)

        # load license key
        result = request_license_key(request)

        if result.get('success'):
            self.license_key = result.get('key') 
        else:
            messages.error(request, result.get('error', 'Request license key error.'))

        if self.license_key:
            self._handle_download(module_name)

        return HttpResponseRedirect(reverse('modules:root'))
    
    @property
    def track(self):
        return 'paid'

    def _handle_download(self, module_name):
        available_modules = self.plugins_api.get_plugins()

        module_data = available_modules.get(module_name, {}).get(self.track, {})
        release_id = module_data.get('release_id')

        if release_id:
            refresh_token = self._get_access_token(release_id)
            # check get token success
            if not refresh_token:
                return

            self._download_module(
                release_id,
                module_data.get('created'),
                module_data.get('description')
            )
        else:
            # If no URL is provided, return an error message or a 400 Bad Request.
            messages.error(self.request, "There is no available modules to update.")

    def _get_access_token(self, release_id):
        if self.license_key:
            # request access token by license_key
            data = {
                "key": self.license_key
            }
            token_response = self.plugins_api.get_access_token(release_id, data=data)
        else:
            data = {
                'key': self.refresh_token
            }
            token_response = self.plugins_api.refresh_token(release_id, data=data)

        if self.plugins_api.errors:
            if token_response.status_code == 403:
                messages.error(self.request, "You have no permissions to this plugin.")
            elif token_response.status_code == 404:
                messages.error(self.request, "Plugin does not exists.")
            else:
                messages.error(self.request, "Service error.")
        else:
            access_token = token_response.get('access_token')
            self.plugins_api.fetch_token(access_token)

            # set refresh token
            self.refresh_token = token_response.get('refresh_token')
            return self.refresh_token


class DeleteModule(LoginRequiredMixin, TemplateView):

    @permission_admin
    def get(self, request, module, *args, **kwargs):
        module_path = os.path.join(settings.MODULES_DIR, module)
        app_name = 'modules.%s' % module

        if os.path.isdir(module_path) and apps.is_installed(app_name):
            self.hande_delete(module_path, module, app_name)

            messages.success(request, 'Module "%s" deleted successfully.' % module)
            return HttpResponseRedirect(reverse('modules:root'))
        else:
            raise Http404

    def hande_delete(self, module_path, module, app_name):

        # migrate db if module has migrations
        if os.path.exists(os.path.join(module_path, 'migrations', '__init__.py')):
            management.call_command('migrate', module, 'zero', interactive=True)

        management.call_command('collectstatic', '--noinput', interactive=False)

        shutil.rmtree(module_path)

        # delete module data
        self.delete_module_objects(module)

        # delete module disco urls
        DiscoUrls.objects.filter(module_name=module).delete()

        settings.INSTALLED_APPS.remove(app_name)

        # update app list
        update_app_list(settings.INSTALLED_APPS)

        management.call_command('update_permissions')
        make_xmpp_config()

        reload_server()

    def delete_module_objects(self, module_name):

        """ Deletion from db logic """

        plugins_api = PluginsApi(self.request)

        module_objects = Module.objects.filter(name=module_name)
        for module in module_objects:
            if module.files:
                file_list = module.files.split(',')
                for filename in file_list:
                    file_path = os.path.join(settings.XMPP_SERVER_EXTERNAL_MODULES_DIR, filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)

            # delete module refresh token from plugins api
            if module.refresh_token:
                plugins_api.fetch_token(module.refresh_token)
                plugins_api.delete_refresh_token()

        module_objects.delete()


# Create your views here.
class LoginXabberServices(LoginRequiredMixin, View):

    @permission_admin
    def post(self, request, *args, **kwargs):
        xservices_api = XabberServicesApi(request)

        jid = request.POST.get('jid')
        result = validate_jid(jid)
        if not result.get('success'):
            return JsonResponse(
                {
                    "message": str(result.get('error_message')),
                },
                status=400
            )
        
        jid = result.get('full_jid')

        request.session['xservises_jid'] = jid
        request.session.modified = True

        xservices_api.code_request(jid)

        if xservices_api.errors:
            return JsonResponse(
                {
                    "message": 'Request code service error.',
                },
                status=500
            )

        return JsonResponse(
            {
                "message": "Code requested successfully.",
            }
        )
    

class ConfirmXabberServices(LoginRequiredMixin, View):

    @permission_admin
    def post(self, request, *args, **kwargs):
        xservices_api = XabberServicesApi(request)
        jid = request.session.get('xservises_jid')
        code = request.POST.get('code')

        if not jid:
            return JsonResponse(
                {
                    "message": "JID is required",
                },
                status=400
            )
            
        if not code:
            return JsonResponse(
                {
                    "message": "Code is required",
                },
                status=400
            )

        result = validate_jid(jid)
        if not result.get('success'):
            return JsonResponse(
                {
                    "message": str(result.get('error_message')),
                },
                status=400
            )

        jid = result.get('full_jid')
        response = xservices_api.license_token(jid, code)

        if xservices_api.errors or not xservices_api.raw_response.ok:
            return JsonResponse(
                {
                    "message": 'Confirm code error.'
                },
                status=500
            )
        
        token = response.get('token')
        expires = response.get('expires')
        expires_dt = parse_datetime(expires)

        XServicesToken.objects.all().delete()
        XServicesToken.objects.create(token=token, expires=expires_dt, jid=jid)

        try:
            del request.session['xservises_jid']
        except:
            pass

        request.session.modified = True

        purchased_modules = self._get_purchased_modules()

        return JsonResponse(
            {
                "message": "Code confirmed successfully.",
                "purchased_modules": purchased_modules
            }
        )
    
    def _get_purchased_modules(self):
        # Request purchased modules
        plugins_api = PluginsApi(self.request)
        purchased_modules = []
        result = request_license_key(self.request)
        if result.get('success'):
            license_key = result.get('key')
            
            purchased_modules = plugins_api.get_purchased_plugins(license_key)

        return purchased_modules
    

class LogoutXabberServices(LoginRequiredMixin, View):

    @permission_admin
    def get(self, request, *args, **kwargs):
        XServicesToken.objects.all().delete()

        referer = request.META.get('HTTP_REFERER')
        if referer:
            # If there is a referer, redirect to it
            return HttpResponseRedirect(referer)
        
        return HttpResponseRedirect(reverse('modules:root'))