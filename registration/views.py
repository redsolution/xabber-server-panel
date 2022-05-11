import time
from modules_installation.utils.config_generator import make_xmpp_config
from registration.forms import EnableRegistrationForm, AddRegistrationKeyForm
from registration.models import RegistrationSettings, RegistrationURL
from server.utils import reload_ejabberd_config
from virtualhost.models import VirtualHost
from xmppserverui.mixins import ServerStartedMixin
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from django.urls import reverse


class Registration(ServerStartedMixin, TemplateView):
    page_section = 'registration'

    def get_vhost(self, request, *args, **kwargs):
        vhost = request.COOKIES['vhost'] if 'vhost' in request.COOKIES and self.context['auth_user'].is_admin \
            else request.session.get('_auth_user_host')
        return VirtualHost.objects.get(name=vhost)


class RegistrationView(Registration):
    template_name = 'registration/registration.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        vhost = self.get_vhost(request)
        context = {'active_tab': 'registration', 'vhosts': self.context['vhosts']}
        try:
            sett_obj = RegistrationSettings.objects.get(vhost=vhost)
        except RegistrationSettings.DoesNotExist:
            sett_obj = RegistrationSettings()
        if sett_obj.status == "LINK":
            try:
                context['cur_url'] = RegistrationURL.objects.get(vhost=vhost).value
            except RegistrationURL.DoesNotExist:
                pass
            keys_list = user.api.get_keys({"host": vhost.name}).get('keys')
            if keys_list:
                for key in keys_list:
                    key['expire'] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(key.get('expire')))
                context['keys'] = keys_list
            else:
                context['keys'] = []
        context['form'] = EnableRegistrationForm(registration=sett_obj.status)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        vhost = self.get_vhost(request)
        key = request.POST.get('key')
        new_status = request.POST.get('registration')
        try:
            sett_obj = RegistrationSettings.objects.get(vhost=vhost)
            cur_status = sett_obj.status
        except RegistrationSettings.DoesNotExist:
            cur_status = "DISABLED"

        if key:
            user = request.user
            user.api.delete_key({"host": vhost.name}, key=key)

        if cur_status == new_status:
            pass
        elif new_status == "DISABLED":
            try:
                RegistrationSettings.objects.get(vhost=vhost).delete()
            except RegistrationSettings.DoesNotExist:
                pass
        else:
            try:
                sett_obj = RegistrationSettings.objects.get(vhost=vhost)
                sett_obj.status = new_status
                sett_obj.save()
            except RegistrationSettings.DoesNotExist:
                RegistrationSettings.objects.create(vhost=vhost, status=new_status)
        make_xmpp_config()
        reload_ejabberd_config()
        return HttpResponseRedirect(reverse('registration:registration'))


class ChangeKeyView(Registration):
    template_name = 'registration/change_key.html'

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


class AddKeyView(Registration):
    template_name = 'registration/add_key.html'

    def get(self, request, *args, **kwargs):
        vhost = self.get_vhost(request)
        context = {'form': AddRegistrationKeyForm(), 'vhost': vhost.name}
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


class SetUrlView(Registration):
    template_name = 'registration/set_url.html'

    def get(self, request, *args, **kwargs):
        vhost = self.get_vhost(request)
        try:
            cur_url = RegistrationURL.objects.get(vhost=vhost).value
        except RegistrationURL.DoesNotExist:
            cur_url = ""
        context = {"cur_url": cur_url, "vhost": vhost.name}
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        vhost = [self.get_vhost(request)]
        reset = request.POST.get('reset')
        all_domains = request.POST.get('all_domains')
        if all_domains:
            vhost = VirtualHost.objects.all()
        if reset:
            for obj in vhost:
                RegistrationURL.objects.filter(vhost=obj).delete()
        else:
            new_url = request.POST.get('url').strip()
            if new_url:
                for obj in vhost:
                    try:
                        cur_url = RegistrationURL.objects.get(vhost=obj)
                        cur_url.value = new_url
                        cur_url.save()
                    except RegistrationURL.DoesNotExist:
                        RegistrationURL.objects.create(vhost=obj, value=new_url)
        return HttpResponseRedirect(reverse('registration:registration'))
