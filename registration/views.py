import time
from modules_installation.utils.config_generator import make_xmpp_config
from registration.forms import EnableRegistrationForm, AddRegistrationKeyForm
from registration.models import RegistrationSettings
from server.utils import reload_ejabberd_config
from virtualhost.models import VirtualHost
from xmppserverui.mixins import ServerStartedMixin
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from django.urls import reverse


class RegistrationView(ServerStartedMixin, TemplateView):
    page_section = 'registration'
    template_name = 'registration/registration.html'

    def get_vhost(self, request, *args, **kwargs):
        vhost = request.COOKIES['vhost'] if 'vhost' in request.COOKIES and self.context['auth_user'].is_admin \
            else request.session.get('_auth_user_host')
        return VirtualHost.objects.get(name=vhost)

    def get(self, request, *args, **kwargs):
        user = request.user
        vhost = self.get_vhost(request)
        context = {'active_tab': 'registration', 'vhosts': self.context['vhosts']}
        try:
            registration = RegistrationSettings.objects.get(vhost=vhost)
        except RegistrationSettings.DoesNotExist:
            registration = RegistrationSettings(is_enabled=False, is_enabled_by_key=False)
        context['form'] = EnableRegistrationForm(is_enabled=registration.is_enabled,
                                                 is_enabled_by_key=registration.is_enabled_by_key)
        context['by_key'] = registration.is_enabled_by_key
        if registration.is_enabled_by_key:
            keys_list = user.api.get_keys({"host": vhost.name}).get('keys')
            if keys_list:
                for key in keys_list:
                    key['expire'] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(key.get('expire')))
                context['keys'] = keys_list
            else:
                context['keys'] = []

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        vhost = self.get_vhost(request)
        if request.POST.get('key'):
            user = request.user
            user.api.delete_key({"host": vhost.name}, key=request.POST.get('key'))
        else:
            is_enabled = True if request.POST.get("is_enabled") == "on" else False
            is_enabled_by_key = True if request.POST.get("is_enabled_by_key") == "on" else False
            try:
                register = RegistrationSettings.objects.get(vhost=vhost)
                if is_enabled:
                    register.is_enabled = is_enabled
                    register.is_enabled_by_key = is_enabled_by_key
                    register.save()
                else:
                    register.delete()
            except RegistrationSettings.DoesNotExist:
                if is_enabled:
                    RegistrationSettings.objects.create(vhost=vhost, is_enabled=is_enabled,
                                                        is_enabled_by_key=is_enabled_by_key)
            make_xmpp_config()
            reload_ejabberd_config()

        return HttpResponseRedirect(reverse('registration:registration'))


class ChangeKeyView(ServerStartedMixin, TemplateView):
    page_section = 'registration'
    template_name = 'registration/change_key.html'

    def get_vhost(self, request, *args, **kwargs):
        vhost = request.COOKIES['vhost'] if 'vhost' in request.COOKIES and self.context['auth_user'].is_admin \
            else request.session.get('_auth_user_host')
        return VirtualHost.objects.filter(name=vhost).first()

    def get(self, request, *args, **kwargs):
        vhost = self.get_vhost(request)
        context = {'current_key': kwargs.get('key'), 'vhost': vhost.name}
        user = request.user
        keys_list = user.api.get_keys({"host": vhost}).get('keys')
        initial_attrs = next(x for x in keys_list if x["key"] == context['current_key'])
        expire = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(initial_attrs.get('expire')))
        description = initial_attrs.get('description')
        context['form'] = AddRegistrationKeyForm(description=description, expire=expire)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        vhost = self.get_vhost(request)
        form = AddRegistrationKeyForm(request.POST)
        if form.is_valid():
            current_key = kwargs.get('key')
            user = request.user
            user.api.change_key({"host": vhost.name,
                                 "expire": form.cleaned_data['expire'],
                                 "description": form.cleaned_data['description']},
                                current_key)
            return HttpResponseRedirect(reverse('registration:registration'))
        context = {'form': form}
        return self.render_to_response(context)


class AddKeyView(ServerStartedMixin, TemplateView):
    page_section = 'registration'
    template_name = 'registration/add_key.html'

    def get_vhost(self, request, *args, **kwargs):
        vhost = request.COOKIES['vhost'] if 'vhost' in request.COOKIES and self.context['auth_user'].is_admin \
            else request.session.get('_auth_user_host')
        return VirtualHost.objects.filter(name=vhost).first()

    def get(self, request, *args, **kwargs):
        context = {'form': AddRegistrationKeyForm()}
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        vhost = self.get_vhost(request)
        form = AddRegistrationKeyForm(request.POST)
        if form.is_valid():
            user = request.user
            user.api.create_key({"host": vhost.name,
                                 "expire": form.cleaned_data['expire'],
                                 "description": form.cleaned_data['description']})
            return HttpResponseRedirect(reverse('registration:registration'))
        context = {'form': form}
        return self.render_to_response(context)
