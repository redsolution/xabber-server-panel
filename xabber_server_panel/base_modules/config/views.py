from django.shortcuts import reverse, loader, render, Http404
from django.views.generic import TemplateView, View
from django.http import HttpResponseRedirect, JsonResponse
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core import management
from django.apps import apps


from ldap3 import Server, Connection, ALL

from xabber_server_panel.base_modules.config.models import VirtualHost, Module
from xabber_server_panel.base_modules.circles.models import Circle
from xabber_server_panel.base_modules.users.models import User
from xabber_server_panel.base_modules.users.utils import check_users
from xabber_server_panel.base_modules.config.utils import update_ejabberd_config, make_xmpp_config, check_hosts,\
    get_dns_records, check_hosts_dns
from xabber_server_panel.utils import get_system_group_suffix, update_app_list, reload_server
from xabber_server_panel.base_modules.users.decorators import permission_read, permission_write, permission_admin
from xabber_server_panel.api.utils import get_api
from xabber_server_panel.api.api import PluginsApi
from xabber_server_panel.utils import get_error_messages, restart_ejabberd, is_ejabberd_started, check_versions
from xabber_server_panel.crontab.models import CronJob
from xabber_server_panel.crontab.forms import CronJobForm
from xabber_server_panel.certificates.utils import update_or_create_certs, check_certificates, validate_certificate
from xabber_server_panel.certificates.models import Certificate


from .models import LDAPSettings, LDAPServer, RootPage, DiscoUrls
from .forms import LDAPSettingsForm, VirtualHostForm
from .module_uploader import ModuleUploader

import threading
import shutil
import requests
import os
import re


class ConfigRoot(LoginRequiredMixin, TemplateView):

    @permission_read
    def get(self, request, *args, **kwargs):

        if request.user.is_admin:
            return HttpResponseRedirect(reverse('config:hosts'))

        return HttpResponseRedirect(reverse('config:ldap'))


class Hosts(LoginRequiredMixin, TemplateView):
    template_name = 'config/hosts.html'

    @permission_admin
    def get(self, request, *args, **kwargs):

        api = get_api(request)

        check_hosts(api)
        check_certificates()

        context = {}
        return self.render_to_response(context)

    @permission_admin
    def post(self, request, *args, **kwargs):

        api = get_api(request)
        check_hosts(api)

        issue_cert_list = request.POST.getlist('issue_cert')
        VirtualHost.objects.filter(id__in=issue_cert_list).update(issue_cert=True)
        VirtualHost.objects.exclude(id__in=issue_cert_list).update(issue_cert=False)

        context = {}
        return self.render_to_response(context)


class DeleteHost(LoginRequiredMixin, TemplateView):

    @permission_admin
    def get(self, request, id, *args, **kwargs):

        try:
            host = VirtualHost.objects.get(id=id)
        except VirtualHost.DoesNotExist:
            raise Http404

        if request.user.host == host.name:
            messages.error(request, "You can't delete self host!")
            return HttpResponseRedirect(
                reverse('config:hosts')
            )

        api = get_api(request)

        users = User.objects.filter(host=host.name)
        for user in users:
            api.unregister_user(
                {
                    'username': user.username,
                    'host': host.name
                }
            )
        users.delete()

        circles = Circle.objects.filter(host=host.name)
        for circle in circles:
            api.delete_circle(
                {
                    'circle': circle.circle,
                    'host': host.name
                }
            )
        circles.delete()

        # check api errors
        error_messages = get_error_messages(request)
        if not error_messages:
            messages.success(request, 'Host "%s" deleted successfully.' % host.name)

        host.delete()
        update_ejabberd_config()
        api.reload_config()
        return HttpResponseRedirect(
            reverse('config:hosts')
        )


class DetailHost(LoginRequiredMixin, TemplateView):
    template_name = 'config/host_detail.html'

    @permission_admin
    def get(self, request, id, *args, **kwargs):

        try:
            host = VirtualHost.objects.get(id=id)
        except VirtualHost.DoesNotExist:
            raise Http404

        context = {
            'host': host
        }
        return self.render_to_response(context)


class CreateHost(LoginRequiredMixin, TemplateView):
    template_name = 'config/host_create.html'

    @permission_admin
    def get(self, request, *args, **kwargs):
        context = {}
        return self.render_to_response(context)

    @permission_admin
    def post(self, request, *args, **kwargs):
        self.api = get_api(request)

        form = VirtualHostForm(request.POST)

        if form.is_valid():
            host = form.save(commit=False)

            # check srv records
            srv_records = get_dns_records(host.name)
            if not 'error' in srv_records:
                host.srv_records = True

            # check cert records
            cert_records = get_dns_records(host.name, type='A')
            if settings.CHALLENGE_RECORD in cert_records.get('_acme-challenge', []):
                host.cert_records = True

            # enable issue certificates flag
            if host.srv_records:
                host.issue_cert = True

            host.save()

            # Create a thread to create certificates
            thread = threading.Thread(target=update_or_create_certs, args=('', self.api))
            thread.start()

            # update config after creating new host
            update_ejabberd_config()
            self.api.reload_config()

            # create groups after update config
            self.create_everybody_group(request, host.name)

            # check api errors
            error_messages = get_error_messages(request)
            if not error_messages:
                messages.success(request, 'Virtual host "%s" created successfully.' % host.name)

                return HttpResponseRedirect(
                    reverse('config:hosts')
                )

        # add common errors
        common_error = form.errors.get('__all__')
        if common_error:
            messages.error(request, common_error)

        return self.render_to_response({'form': form})

    def create_everybody_group(self, request, host):

        try:
            Circle.objects.create(
                circle=host,
                host=host,
                name=settings.XMPP_SERVER_DEFAULT_GROUP_NAME,
                description=settings.XMPP_SERVER_DEFAULT_GROUP_DESCRIPTION,
                prefix=get_system_group_suffix(),
                all_users=True
            )
        except Exception as e:
            messages.error(request, e)
            return

        self.api.create_circle(
            {
                'circle': host,
                'host': host,
                'name': settings.XMPP_SERVER_DEFAULT_GROUP_NAME,
                'description': settings.XMPP_SERVER_DEFAULT_GROUP_DESCRIPTION,
                'all_users': True
            }
        )


class CheckDnsRecords(LoginRequiredMixin, View):

    def get(self, request):
        check_hosts_dns()

        # Create a thread to create certificates
        thread = threading.Thread(target=update_or_create_certs, args=('', get_api(request)))
        thread.start()

        check_certificates()

        return render(request, 'config/parts/host_list.html')


class Admins(LoginRequiredMixin, TemplateView):
    template_name = 'config/admins.html'

    @permission_admin
    def get(self, request, *args, **kwargs):
        api = get_api(request)

        for host in VirtualHost.objects.all():
            check_users(api, host.name)

        admins = User.objects.filter(is_admin=True)

        # exclude authenticated user because he cant change self status
        users = User.objects.exclude(id=request.user.id)
        context = {
            'admins': admins,
            'users': users
        }
        return self.render_to_response(context)

    @permission_admin
    def post(self, request, *args, **kwargs):
        # exclude authenticated user because he cant change self status
        users = User.objects.exclude(id=request.user.id)

        admins = request.POST.get('admins', '')
        if admins:
            admins = admins.split(',')

        api = get_api(request)

        admins_to_add = users.filter(id__in=admins, is_admin=False)
        for user in admins_to_add:
            user.permissions.set([])
            api.set_admin(
                {
                    "username": user.username,
                    "host": user.host
                }
            )

        admins_to_add.update(is_admin=True)

        admins_to_delete = users.exclude(id__in=admins).filter(is_admin=True)
        for user in admins_to_delete:
            api.del_admin(
                {
                    "username": user.username,
                    "host": user.host,
                }
            )

        admins_to_delete.update(is_admin=False)

        # check api errors
        error_messages = get_error_messages(request)
        if not error_messages:
            messages.success(request, 'Admins changed successfully.')

        context = {
            'admins': User.objects.filter(is_admin=True),
            'users': users
        }
        return self.render_to_response(context)


class Ldap(LoginRequiredMixin, TemplateView):
    template_name = 'config/ldap.html'

    @permission_read
    def get(self, request, *args, **kwargs):

        host = request.current_host

        context = {}

        ldap_settings = LDAPSettings.objects.filter(host=host).first()
        context['ldap_settings'] = ldap_settings

        if request.is_ajax():
            html = loader.render_to_string('config/parts/ldap_fields.html', context, request)
            response_data = {
                'html': html
            }
            return JsonResponse(response_data)
        return self.render_to_response(context)

    @permission_write
    def post(self, request, *args, **kwargs):
        self.form = LDAPSettingsForm(request.POST)

        context = {
            'form': self.form
        }

        self.server_list = self.clean_server_list()
        if self.form.is_valid():
            self.update_or_create_ldap()
            update_ejabberd_config()

            if is_ejabberd_started():
                restart_ejabberd()

            messages.success(request, 'Ldap settings changed successfully.')
        else:
            for error in self.form.errors.values():
                messages.error(request, '%s' % error)

        return self.render_to_response(context)

    def clean_server_list(self):
        server_list_data = self.request.POST.get('server_list')

        # Split the input strings by commas, semicolons, and line breaks
        server_list = re.split(r'[;,\n]+', server_list_data.strip())

        # Remove empty strings
        server_list = [server.strip() for server in server_list if server.strip()]

        invalid_server_list = []
        for server_name in server_list:
            server = Server(server_name, get_info=ALL)
            conn = Connection(server)
            try:
                conn.bind()
            except Exception:
                invalid_server_list.append(server_name)

        if invalid_server_list:
            self.form.add_error(
                'server_list', 'Invalid server list: {}.'.format(', '.join(invalid_server_list))
            )

        return server_list

    def update_or_create_ldap(self):
        # prepare data to update excluding special fields
        defaults = {
            key: self.form.cleaned_data.get(key) for key in self.form.fields.keys() if key not in ['host', 'server_list']
        }

        # update settings
        ldap_settings, created = LDAPSettings.objects.update_or_create(
            host=self.request.current_host,
            defaults=defaults
        )

        # create new servers
        for server in self.server_list:
            LDAPServer.objects.get_or_create(
                server=server, settings=ldap_settings
            )

        # delete old servers
        ldap_settings.servers.exclude(server__in=self.server_list).delete()


class Modules(LoginRequiredMixin, TemplateView):
    template_name = 'config/modules.html'

    @permission_admin
    def get(self, request, *args, **kwargs):
        plugins_api = PluginsApi(request)

        available_modules = plugins_api.get_plugins()

        installed_modules = {module.name: module for module in Module.objects.all()}

        modules_data = []
        processed_modules = set()
        grouped_available_modules = {}

        # Handle installed modules
        for module_name, installed_module in installed_modules.items():
            available_module_data = available_modules.get(module_name, {})
            module_info = {
                'name': module_name,
                'display_name': installed_module.verbose_name or module_name,
                'track': installed_module.track,
                'version': installed_module.version,
                'root_page': installed_module.root_page,
                'global_module': installed_module.global_module,
                'custom': installed_module.custom,
                'created_installed': installed_module.created,
                'installed': True,
                'description': installed_module.description,
                'update_links': self.check_module_versions(installed_module, available_module_data),
            }
            modules_data.append(module_info)
            processed_modules.add(module_name)

        # Group available modules by name and version
        for module_name, tracks in available_modules.items():
            for track, module in tracks.items():
                key = (module_name, module.get('release'))

                if key not in grouped_available_modules:
                    grouped_available_modules[key] = {
                        'name': module_name,
                        'display_name': module.get('display_name', module_name),
                        'version': module.get('release'),
                        'created': module.get('created'),
                        'description': module.get('description'),
                        'tracks': [],
                        'installed': False,
                        'update_links': {},
                    }

                grouped_available_modules[key]['tracks'].append(track)

        # Add available modules excluding installed modules
        for module_info in grouped_available_modules.values():
            if module_info['name'] not in processed_modules:
                modules_data.append(module_info)

        # Sort by installed status
        modules_data.sort(key=lambda x: not x['installed'])

        context = {
            'modules_data': modules_data
        }
        return self.render_to_response(context)

    def check_module_versions(self, module: Module, available_module_data: dict):
        """ Check available updates and return links list """
        result = {}

        if isinstance(module, Module) and isinstance(available_module_data, dict):
            new_module_free = available_module_data.get('free')
            new_module_paid = available_module_data.get('paid')
            if not module.custom:
                if module.track == 'free':
                    if new_module_free:
                        if check_versions(module.version, new_module_free.get('release')).get('success'):
                            result['upgrade'] = reverse('config:upload_module',
                                                        kwargs={'module_name': module.name, 'track': 'free'})
                    if new_module_paid:
                        if check_versions(module.version, new_module_paid.get('release'), equals_ok=True).get(
                                'success'):
                            result['buy'] = reverse('config:upload_module',
                                                    kwargs={'module_name': module.name, 'track': 'paid'})
                elif module.track == 'paid':
                    if new_module_paid:
                        if check_versions(module.version, new_module_paid.get('release')).get('success'):
                            result['upgrade'] = reverse('config:upload_module',
                                                        kwargs={'module_name': module.name, 'track': 'paid'})

        return result

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
            except Exception as e:
                messages.error(self.request, e)

        return HttpResponseRedirect(reverse('config:modules'))


class UploadModule(LoginRequiredMixin, View):

    refresh_token = ''
    key = ''

    @permission_admin
    def get(self, request, module_name, track, **kwargs):

        self.plugins_api = PluginsApi(request)

        # get token key refresh or license
        module = Module.objects.filter(name=module_name).exclude(refresh_token='').first()
        if module and module.refresh_token:
            self.key = module.refresh_token

        self._handle_upload(module_name, track)

        return HttpResponseRedirect(reverse('config:modules'))

    @permission_admin
    def post(self, request, module_name, track, **kwargs):

        self.plugins_api = PluginsApi(request)
        self.key = self.request.POST.get('key')
        self._handle_upload(module_name, track)

        return HttpResponseRedirect(reverse('config:modules'))

    def _handle_upload(self, module_name, track):
        available_modules = self.plugins_api.get_plugins()

        module_data = available_modules.get(module_name, {}).get(track, {})
        release_id = module_data.get('release_id')

        if release_id:
            if track == 'paid' and self.key:
                self._get_access_token(release_id)

            self._upload_module(
                track,
                release_id,
                module_data.get('created'),
                module_data.get('description')
            )
        else:
            # If no URL is provided, return an error message or a 400 Bad Request.
            messages.error(self.request, "There is no available modules to update.")

    def _get_access_token(self, release_id):
        data = {
            "key": self.key
        }
        token_response = self.plugins_api.get_access_token(release_id, data=data)

        if not self.plugins_api.errors:
            access_token = token_response.get('access_token')
            self.plugins_api.fetch_token(access_token)

            # set refresh token
            self.refresh_token = token_response.get('refresh_token')

    def _upload_module(self, track, release_id, created, description):
        try:
            response = self.plugins_api.download_release(release_id)
            if response.ok:
                module_uploader = ModuleUploader(
                    uploaded_file=response.raw,
                    track=track,
                    created=created,
                    description=description,
                    refresh_token=self.refresh_token
                )
                module_uploader.handle_upload()
                messages.success(self.request, 'Module installed successfully.')
            elif self.plugins_api.raw_response.status_code == 403:
                raise Exception('Wrong access token.')
            elif self.plugins_api.raw_response.status_code == 401:
                raise Exception('Not authenticated.')
            elif self.plugins_api.raw_response.status_code == 400:
                raise Exception('Malformed data.')
            else:
                raise Exception('Service is not available.')
        except Exception as e:
            messages.error(self.request, e)


class DeleteModule(LoginRequiredMixin, TemplateView):

    @permission_admin
    def get(self, request, module, *args, **kwargs):
        module_path = os.path.join(settings.MODULES_DIR, module)
        app_name = 'modules.%s' % module

        if os.path.isdir(module_path) and apps.is_installed(app_name):
            self.hande_delete(module_path, module, app_name)

            messages.success(request, 'Module "%s" deleted successfully.' % module)
            return HttpResponseRedirect(reverse('config:modules'))
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

        module_objects = Module.objects.filter(name=module_name)
        for module in module_objects:
            if module.files:
                file_list = module.files.split(',')
                for filename in file_list:
                    file_path = os.path.join(settings.XMPP_SERVER_EXTERNAL_MODULES_DIR, filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)

        module_objects.delete()


class RootPageView(LoginRequiredMixin, TemplateView):
    template_name = 'config/root_page.html'

    @permission_read
    def get(self, request, *args, **kwargs):
        return self.render_to_response({})

    @permission_write
    def post(self, request, *args, **kwargs):

        module = request.POST.get('module', 'home')
        root_page = RootPage.objects.first()
        if root_page:
            root_page.module = module
            root_page.save()
        else:
            RootPage.objects.create(module=module)

        messages.success(request, 'Root page changed successfully.')

        return self.render_to_response({})


class ChangeHost(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        host_id = request.POST.get('host')

        try:
            host = VirtualHost.objects.get(id=host_id)
        except VirtualHost.DoesNotExist:
            raise Http404

        request.session['host'] = host_id

        referer = request.META.get('HTTP_REFERER')
        if referer:
            # If there is a referer, redirect to it
            return HttpResponseRedirect(referer)
        else:
            return HttpResponseRedirect(reverse('home'))


class CronJobs(LoginRequiredMixin, TemplateView):

    template_name = 'config/cron_jobs.html'

    @permission_admin
    def get(self, request, *args, **kwargs):
        cron_jobs = CronJob.objects.all()

        context = {
            'cron_jobs': cron_jobs,
        }
        return self.render_to_response(context)


class CronJobCreate(LoginRequiredMixin, TemplateView):

    template_name = 'config/cron_create.html'

    @permission_admin
    def get(self, request, *args, **kwargs):
        form = CronJobForm()

        context = {
            'form': form,
        }
        return self.render_to_response(context)

    @permission_admin
    def post(self, request, *args, **kwargs):
        form = CronJobForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cron created successfully.')
            return HttpResponseRedirect(
                reverse('config:cron_jobs')
            )

        context = {
            'form': form,
        }
        return self.render_to_response(context)


class CronJobDelete(LoginRequiredMixin, View):

    @permission_admin
    def get(self, request, id, *args, **kwargs):
        try:
            cron_job = CronJob.objects.get(id=id)
        except:
            raise Http404

        if cron_job.type == 'built_in_job':
            messages.error(request, 'You cant delete built in command.')
        else:
            cron_job.delete()
            messages.success(request, 'Cron deleted successfully.')

        return HttpResponseRedirect(
            reverse('config:cron_jobs')
        )


class CronJobChange(LoginRequiredMixin, TemplateView):
    template_name = 'config/cron_change.html'

    @permission_admin
    def get(self, request, id, *args, **kwargs):
        try:
            cron_job = CronJob.objects.get(id=id)
        except:
            raise Http404

        form = CronJobForm()

        context = {
            'cron_job': cron_job,
            'form': form
        }
        return self.render_to_response(context)

    @permission_admin
    def post(self, request, id, *args, **kwargs):
        try:
            cron_job = CronJob.objects.get(id=id)
        except:
            raise Http404

        form = CronJobForm(request.POST, instance=cron_job)
        if form.is_valid():
            form.save()

            messages.success(request, 'Cron changed successfully.')
            return HttpResponseRedirect(
                reverse('config:cron_jobs')
            )

        context = {
            'cron_job': cron_job,
            'form': form
        }
        return self.render_to_response(context)


class Certificates(LoginRequiredMixin, TemplateView):

    template_name = 'config/certificates.html'

    @permission_admin
    def get(self, request, *args, **kwargs):
        check_certificates()
        certificates = Certificate.objects.all()
        context = {
            'certificates_info': certificates,
        }
        return self.render_to_response(context)


class UpdateCert(LoginRequiredMixin, TemplateView):

    template_name = 'config/parts/host_list.html'

    @permission_admin
    def get(self, request, domain, *args, **kwargs):
        update_or_create_certs(domain, get_api(request))
        check_certificates()

        context = {}
        return self.render_to_response(context)


class UploadCert(LoginRequiredMixin, TemplateView):
    ALLOWED_EXTENSIONS = ['pem']

    @permission_admin
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')

        if file:
            # Validate file extension
            file_extension = file.name.split('.')[-1].lower()

            if file_extension in self.ALLOWED_EXTENSIONS:
                destination_path = os.path.join(settings.CERT_CONF_DIR, file.name)
                if os.path.exists(destination_path):
                    messages.error(request, "This certificate already exists.")
                else:
                    with open(destination_path, 'wb+') as destination:
                        for chunk in file.chunks():
                            destination.write(chunk)

                    # Check if certificate has public key and is valid
                    if validate_certificate(destination_path):
                        messages.success(request, 'Certificate added successfully.')
                    else:
                        os.remove(destination_path)  # Remove the uploaded file
                        messages.error(request, "Invalid certificate format.")
            else:
                messages.error(request, "Invalid file format.")

        else:
            messages.error(request, "Certificate file is required.")

        return HttpResponseRedirect(
            reverse('config:certificates')
        )


class DeleteCert(LoginRequiredMixin, TemplateView):

    @permission_admin
    def get(self, request, name, *args, **kwargs):
        try:
            Certificate.objects.filter(name=name).delete()
            messages.success(request, 'Certificate deleted successfully.')
        except Exception as e:
            messages.error(request, e)

        return HttpResponseRedirect(
            reverse('config:certificates')
        )
