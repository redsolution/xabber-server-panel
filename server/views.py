import time
from django.views.generic import TemplateView

from django.urls import reverse
from django.http import HttpResponseRedirect, Http404

from django.conf import settings
from xmppserverui.mixins import PageContextMixin
from virtualhost.models import VirtualHost, User, Group, GroupMember
from virtualhost.utils import get_system_group_suffix
from .models import AuthBackend
from .forms import SelectAdminForm, AddVirtualHostForm, DeleteVirtualHostForm, LDAPSettingsForm, RegistrationKeysForm
from .utils import start_ejabberd, restart_ejabberd, stop_ejabberd, is_ejabberd_running, update_ejabberd_config

SETTINGS_TAB_VHOSTS = 'vhosts'
SETTINGS_TAB_ADMINS = 'admins'
SETTINGS_TAB_AUTH_BACKENDS = 'auth_backends'
SETTINGS_TAB_REGISTRATION_KEYS = 'registration-keys'


class ServerHomePage(PageContextMixin, TemplateView):
    page_section = 'home'
    template_name = 'server/home.html'

    def get(self, request, *args, **kwargs):
        return self.render_to_response(request, *args, **kwargs)


class ServerDashboardView(PageContextMixin, TemplateView):
    page_section = 'dashboard'
    template_name = 'server/dashboard.html'

    def get_hosts_stat(self, request):
        user = request.user
        data = []
        if self.context['auth_user'].is_admin:
            for host in VirtualHost.objects.all():
                user_count = user.api.xabber_registered_users_count(
                    {"host": host.name}).get('count')
                online_user_count = user.api.stats_host(
                    {"host": host.name}).get('count')
                host_data = {"name": host.name,
                             "registeredusers": user_count,
                             "onlineusers": online_user_count}
                data.append(host_data)
        else:
            try:
                host = VirtualHost.objects.get(name=self.context['auth_user'].host)
                user_count = user.api.xabber_registered_users_count(
                    {"host": host.name}).get('count')
                online_user_count = user.api.stats_host(
                    {"host": host.name}).get('count')
                host_data = {"name": host.name,
                             "registeredusers": user_count,
                             "onlineusers": online_user_count}
                data.append(host_data)
            except VirtualHost.DoesNotExist:
                raise Http404
        data.append({"name": "",
                     "registeredusers": sum([o["registeredusers"]
                                             for o in data if o['registeredusers']]),
                     "onlineusers": sum([o["onlineusers"]
                                         for o in data if o['onlineusers']])})
        return data

    def get(self, request, *args, **kwargs):
        vhosts_data = self.get_hosts_stat(request)

        is_ejabberd_started = is_ejabberd_running()['success']
        context = {"is_ejabberd_started": is_ejabberd_started,
                   "vhosts_data": vhosts_data}
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        user = self.context['auth_user']
        if user.is_admin:
            action = request.POST.get('action')
            if action == 'start_server':
                start_ejabberd()
            elif action == 'restart_server':
                restart_ejabberd()
            elif action == 'stop_server':
                stop_ejabberd()

            is_ejabberd_started = is_ejabberd_running()['success']
            vhosts_data = self.get_hosts_stat(request)
            context = {"is_ejabberd_started": is_ejabberd_started,
                       "vhosts_data": vhosts_data}
            return self.render_to_response(context)
        else:
            return HttpResponseRedirect(reverse('server:home'))


class ServerStoppedStubView(PageContextMixin, TemplateView):
    page_section = 'server'
    template_name = 'server/stopped_stub.html'


class ServerAdminsListView(PageContextMixin, TemplateView):
    page_section = 'server'
    template_name = 'server/admins_list.html'

    def get(self, request, *args,**kwargs):
        admins = User.objects.filter(is_admin=True)

        context = {
            'admins': admins,
            'active_tab': SETTINGS_TAB_ADMINS
        }
        return self.render_to_response(context)


class ManageAdminsSelectView(PageContextMixin, TemplateView):
    page_section = 'server'
    template_name = 'server/admins_manage.html'

    def get_admin_list(self):
        return [admin.full_jid for admin in User.objects.filter(is_admin=True)]

    def get_page_context(self, request, *args, **kwargs):
        user = request.user
        users = User.objects.all()
        admins = users.filter(is_admin=True)
        return {
            'users': users,
            'admins_count': admins.count(),
            'active_tab': SETTINGS_TAB_ADMINS
        }

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_page_context(request, *args, **kwargs))

    def post(self, request, *args, **kwargs):
        context = self.get_page_context(request, *args, **kwargs)

        user = request.user
        post_data = request.POST.copy()
        post_data.pop('admin_list')

        form_admin_list = request.POST.get('admin_list').split(' ')
        stored_admin_list = self.get_admin_list()

        users_to_add = list(set(form_admin_list) - set(stored_admin_list))
        users_to_del = list(set(stored_admin_list) - set(form_admin_list))

        errors = False

        error_message = None
        for admin in users_to_add:
            if len(admin) is 0:
                continue
            name, host = admin.split('@')
            user.api.xabber_set_admin(
                {
                    "username": name,
                    "host": host
                }
            )
            post_data['user'] = admin
            form = SelectAdminForm(post_data, action='add')
            if not form.is_valid():
                errors = True
                break

        for admin in users_to_del:
            if len(admin) is 0:
                continue
            name, host = admin.split('@')
            user.api.xabber_del_admin(
                {
                    "username": name,
                    "host": host,
                }
            )
            post_data['user'] = admin
            form = SelectAdminForm(post_data, action='delete')
            if not form.is_valid():
                errors = True
                error_message = form.errors.as_data()['__all__'][0].message
                break

        if errors:
            if error_message:
                context["select_admins_error"] = error_message
            else:
                context["select_admins_error"] = \
                    "An unexpected error has occurred. Please, try again later."
            return self.render_to_response(context)
        update_ejabberd_config()
        return HttpResponseRedirect(reverse('server:admins-list'))


class ServerVhostsListView(PageContextMixin, TemplateView):
    page_section = 'server'
    template_name = 'server/vhosts_list.html'

    def get(self, request, *args,**kwargs):
        vhosts = VirtualHost.objects.all()

        context = {
            'virtual_hosts': vhosts,
            'active_tab': SETTINGS_TAB_VHOSTS
        }
        return self.render_to_response(context)


class AddVirtualHostView(PageContextMixin, TemplateView):
    page_section = 'server'
    template_name = 'server/add_vhost.html'

    def create_everybody_group(self, request, hostname):
        create_group_data = {
            'group': hostname,
            'host': hostname,
            'name': settings.EJABBERD_EVERYBODY_DEFAULT_GROUP_NAME,
            'description': settings.EJABBERD_EVERYBODY_DEFAULT_GROUP_DESCRIPTION,
            'display': []
        }
        request.user.api.srg_create_api(data=create_group_data)
        add_all_users_data = {
            'user': '@all@',
            'host': hostname,
            'circle': hostname,
            'grouphost': hostname
        }
        request.user.api.srg_user_add_api(data=add_all_users_data)

        group = Group(
            group=hostname,
            host=hostname,
            name=settings.EJABBERD_EVERYBODY_DEFAULT_GROUP_NAME,
            description=settings.EJABBERD_EVERYBODY_DEFAULT_GROUP_DESCRIPTION,
            prefix=get_system_group_suffix()
        )
        group.save()
        member = GroupMember(
            group=group,
            username='@all@',
            host=hostname
        )
        member.save()

    def get_page_context(self, request, *args, **kwargs):
        user = request.user
        hosts = VirtualHost.objects.all()
        form = AddVirtualHostForm(user)
        return {
            'form': form,
            'vhosts_count': hosts.count
        }

    def get(self, request, *args, **kwargs):
        user = request.user
        hosts = VirtualHost.objects.all()
        form = AddVirtualHostForm()
        context = {
            'form': form,
            'vhosts_count': hosts.count
        }
        return self.render_to_response(context=context)

    def post(self, request, *args, **kwargs):
        user = request.user
        form = AddVirtualHostForm(request.POST)
        if form.is_valid():
            update_ejabberd_config()
            self.create_everybody_group(request, form.clean_name())
            return HttpResponseRedirect(reverse('server:settings'))
        hosts = VirtualHost.objects.all()
        return self.render_to_response({
            "form": form,
            'vhosts_count': hosts.count
        })


class DeleteVirtualHostView(PageContextMixin, TemplateView):
    page_section = 'server'
    template_name = 'server/delete_vhost.html'

    def get(self, request, *args, **kwargs):
        try:
            vhost_to_del = VirtualHost.objects.get(id=kwargs["vhost_id"])
        except VirtualHost.DoesNotExist:
            raise Http404
        user = request.user
        form = DeleteVirtualHostForm()
        return self.render_to_response({"vhost_to_del": vhost_to_del,
                                        "form": form})

    def post(self, request, *args, **kwargs):
        try:
            vhost_to_del = VirtualHost.objects.get(id=kwargs["vhost_id"])
        except VirtualHost.DoesNotExist:
            raise Http404
        user = request.user
        post_data = request.POST.copy()
        post_data.update({"name": vhost_to_del.name})
        form = DeleteVirtualHostForm(post_data)
        if form.is_valid():
            users_to_del = User.objects.filter(host=vhost_to_del)
            for item in users_to_del:
                data = {
                    'username': item.username,
                    'host': item.host
                }
                user.api.unregister_user(data=data)
            users_to_del.delete()

            groups_to_del = Group.objects.filter(host=vhost_to_del)
            for item in groups_to_del:
                data = {
                    'circle': item.group,
                    'host': item.host
                }
                user.api.delete_group(data=data)
            groups_to_del.delete()
            update_ejabberd_config()
            return HttpResponseRedirect(reverse('server:settings'))
        return self.render_to_response({"vhost_to_del": vhost_to_del,
                                        "form": form})


class VirtualHostDetauView(PageContextMixin, TemplateView):
    page_section = 'server'
    template_name = 'server/detail_vhost.html'

    def get(self, request, *args, **kwargs):
        try:
            vhost = VirtualHost.objects.get(id=kwargs["vhost_id"])
        except VirtualHost.DoesNotExist:
            raise Http404
        return self.render_to_response({
            'host': vhost,
        })


class ManageLDAPView(PageContextMixin, TemplateView):
    page_section = 'server'
    template_name = 'server/ldap_manage.html'

    def get_page_context(self, vhost=None):
        auth_backends = AuthBackend.objects.all()
        return {
            'auth_backends': auth_backends,
            'active_tab': SETTINGS_TAB_AUTH_BACKENDS
        }

    def get(self, request, *args, **kwargs):
        context = self.get_page_context()
        vhost = request.GET.get('vhost')
        vhost = VirtualHost.objects.filter(name=vhost).first()
        if vhost:
            context['form'] = LDAPSettingsForm(
                vhosts=self.context['vhosts'], vhost=vhost)
        else:
            context['form'] = LDAPSettingsForm(vhosts=self.context['vhosts'])
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = LDAPSettingsForm(request.POST, vhosts=self.context['vhosts'])
        if form.is_valid():
            update_ejabberd_config()
            return HttpResponseRedirect(reverse('server:manage-ldap'))

        context = self.get_page_context()
        context['form'] = form
        return self.render_to_response(context)


class ServerKeysView(PageContextMixin, TemplateView):
    page_section = 'server'
    template_name = 'server/registration_keys.html'

    def get_page_context(self, vhost=None):
        return {
            'active_tab': SETTINGS_TAB_REGISTRATION_KEYS
        }

    def get_vhost(self, request, *args, **kwargs):
        return request.COOKIES['vhost'] if 'vhost' in request.COOKIES and self.context['auth_user'].is_admin \
            else request.session.get('_auth_user_host')

    def get(self, request, *args, **kwargs):
        user = request.user
        vhost = self.get_vhost(request)
        context = self.get_page_context()
        keys_list = user.api.get_keys({"host": vhost}).get('keys')
        for key in keys_list:
            key['expire'] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(key.get('expire')))
        context['keys'] = keys_list
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        user = request.user
        vhost = self.get_vhost(request)
        user.api.delete_key({"host": vhost}, key=request.POST.get('key'))
        return HttpResponseRedirect(reverse('server:registration-keys'))


class ServerChangeKeysView(PageContextMixin, TemplateView):
    page_section = 'server'
    template_name = 'server/change_key.html'

    def get_vhost(self, request, *args, **kwargs):
        return request.COOKIES['vhost'] if 'vhost' in request.COOKIES and self.context['auth_user'].is_admin \
            else request.session.get('_auth_user_host')

    def get(self, request, *args, **kwargs):
        context = {'current_key': kwargs.get('key')}
        user = request.user
        vhost = self.get_vhost(request)
        vhost = VirtualHost.objects.filter(name=vhost).first()
        keys_list = user.api.get_keys({"host": vhost}).get('keys')
        initial_attrs = next(x for x in keys_list if x["key"] == context['current_key'])
        expire = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(initial_attrs.get('expire')))
        description = initial_attrs.get('description')
        context['form'] = RegistrationKeysForm(
            vhosts=self.context['vhosts'], vhost=vhost, description=description, expire=expire)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = RegistrationKeysForm(request.POST, vhosts=self.context['vhosts'])
        if form.is_valid():
            current_key = kwargs.get('key')
            user = request.user
            user.api.change_key({"host": form.cleaned_data['host'],
                                 "expire": int(form.cleaned_data['expire'].timestamp()),
                                 "description": form.cleaned_data['description']},
                                current_key)
            return HttpResponseRedirect(reverse('server:registration-keys'))
        context = {'form': form}
        return self.render_to_response(context)


class ServerAddKeysView(PageContextMixin, TemplateView):
    page_section = 'server'
    template_name = 'server/add_key.html'

    def get(self, request, *args, **kwargs):
        context = {}
        vhost = request.GET.get('vhost')
        vhost = VirtualHost.objects.filter(name=vhost).first()
        if vhost:
            context['form'] = RegistrationKeysForm(
                vhosts=self.context['vhosts'], vhost=vhost)
        else:
            context['form'] = RegistrationKeysForm(vhosts=self.context['vhosts'])
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = RegistrationKeysForm(request.POST, vhosts=self.context['vhosts'])
        if form.is_valid():
            user = request.user
            user.api.create_key({"host": form.cleaned_data['host'],
                                 "expire": int(form.cleaned_data['expire'].timestamp()),
                                 "description": form.cleaned_data['description']})
            return HttpResponseRedirect(reverse('server:registration-keys'))
        context = {'form': form}
        return self.render_to_response(context)
