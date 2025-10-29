from django.shortcuts import reverse, Http404
from django.views.generic import TemplateView, View
from django.http import HttpResponseRedirect, JsonResponse
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core import management
from django.apps import apps
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from jid_validation.utils import validate_jid

from xabber_server_panel.base_modules.config.models import Module, DiscoUrls
from xabber_server_panel.base_modules.config.utils import make_xmpp_config
from xabber_server_panel.utils import update_app_list, reload_server
from xabber_server_panel.base_modules.users.decorators import permission_admin
from xabber_server_panel.api.api import PluginsApi, XabberServicesApi
from xabber_server_panel.utils import get_error_messages

from .module_uploader import ModuleUploader
from .models import XServicesToken
from .utils import get_modules_data, get_available_modules, get_installed_modules, get_plugins_prices

import shutil
import os


class Modules(LoginRequiredMixin, TemplateView):
    template_name = 'modules/modules.html'

    @permission_admin
    def get(self, request, *args, **kwargs):
        plugins_api = PluginsApi(request)

        available_modules = plugins_api.get_plugins()
        if not plugins_api.errors:
            modules_data = get_installed_modules(available_modules)
        else:
            modules_data = []
        
        context = {
            'modules_data': modules_data,
            'xservies_token': XServicesToken.objects.filter(expires__gt=timezone.now()).first()
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
            modules_data = get_available_modules(available_modules)
        else:
            modules_data = []

        plugin_prices = get_plugins_prices(xservices_api)
        
        context = {
            'modules_data': modules_data,
            'plugin_prices': plugin_prices,
            'xservies_token': XServicesToken.objects.filter(expires__gt=timezone.now()).first()
        }
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
                module_uploader = ModuleUploader(
                    uploaded_file=uploaded_file,
                    custom=True
                )
                module_uploader.handle_upload()
                messages.success(self.request, 'Module installed successfully.')
                return HttpResponseRedirect(reverse('modules:root'))
            except Exception as e:
                messages.error(self.request, e)

        return HttpResponseRedirect(reverse('modules:upload'))


class UploadModule(LoginRequiredMixin, View):

    refresh_token = ''
    license_key = ''

    @permission_admin
    def get(self, request, module_name, track, **kwargs):

        self.plugins_api = PluginsApi(request)

        module = Module.objects.filter(name=module_name).exclude(refresh_token='').first()
        if module and module.refresh_token:
            self.refresh_token = module.refresh_token

        self._handle_upload(module_name, track)

        return HttpResponseRedirect(reverse('modules:root'))

    @permission_admin
    def post(self, request, module_name, track, **kwargs):

        self.plugins_api = PluginsApi(request)

        # load license key
        self.request_key_from_api()

        if self.license_key:
            self._handle_upload(module_name, track)

        error_messages = get_error_messages(request)

        return JsonResponse({'errors': error_messages})

    def request_key_from_api(self):
        "Load license key from xabber services API "

        xservices_api = XabberServicesApi(self.request)
        token = XServicesToken.objects.filter(expires__gt=timezone.now()).first()
        
        if not token:
            messages.error(self.request, "Xabber Services Account is not authenticated.") 
            return
        
        response = xservices_api.license_key(data={"token": token.token})
        if xservices_api.errors:
            messages.error(self.request, "Request license key error.") 
            return
        
        key = response.get('license_key')

        # Check if the key is not empty after stripping
        if not key:
            messages.error(self.request, "Request license key error.") 
            return

        self.license_key = key

    def _handle_upload(self, module_name, track):
        available_modules = self.plugins_api.get_plugins()

        module_data = available_modules.get(module_name, {}).get(track, {})
        release_id = module_data.get('release_id')

        if release_id:
            if track == 'paid':
                refresh_token = self._get_access_token(release_id, module_name)
                # check get token success
                if not refresh_token:
                    return

            self._upload_module(
                track,
                release_id,
                module_data.get('created'),
                module_data.get('description')
            )
        else:
            # If no URL is provided, return an error message or a 400 Bad Request.
            messages.error(self.request, "There is no available modules to update.")

    def _get_access_token(self, release_id, module_name):
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

    def _upload_module(self, track, release_id, created, description):
        try:
            self.plugins_api.download_release(release_id)
            if self.plugins_api.raw_response.ok:
                module_uploader = ModuleUploader(
                    uploaded_file=self.plugins_api.raw_response.raw,
                    track=track,
                    created=created,
                    description=description,
                    refresh_token=self.refresh_token
                )
                module_uploader.handle_upload()
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
        XServicesToken.objects.create(token=token, expires=expires_dt)

        try:
            del request.session['xservises_jid']
        except:
            pass

        request.session.modified = True

        return JsonResponse(
            {
                "message": "Code confirmed successfully.",
            }
        )