from django.contrib.auth import login
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView, View
from django.contrib import messages

from xmppserverui.utils import get_default_url, logout_full
from xmppserverui.mixins import NoAuthMixin, AuthMixin, PageContextMixin
from server.utils import is_ejabberd_running
from .forms import LoginForm, LoginFormViaDjango
from virtualhost.models import User, VirtualHost
from virtualhost.signals import get_user_ip


def custom_login(request, form):
    login(request, form.user)
    username, host = form.cleaned_data['username'].split('@')
    request.session['_auth_user_username'] = username
    request.session['_auth_user_host'] = host


class LoginView(NoAuthMixin, TemplateView):
    template_name = 'auth/login.html'

    def get(self, request, *args, **kwargs):
        is_server_started = is_ejabberd_running()['success']
        user_ip = get_user_ip(request)
        if is_server_started:
            form = LoginForm()
        else:
            form = LoginFormViaDjango()
        return self.render_to_response({"form": form, 'user_ip': user_ip})

    def post(self, request, *args, **kwargs):
        is_server_started = is_ejabberd_running()['success']
        user_ip = get_user_ip(request)
        if is_server_started:
            form = LoginForm(request.POST)
        else:
            form = LoginFormViaDjango(request.POST)
        if form.is_valid():
            custom_login(request, form)
            username, host = form.cleaned_data['username'].split('@')
            user = User.objects.filter(username=username, host=host)
            if user.exists():
                user = user[0]
                if user.is_admin or user.get_all_permissions():
                    if not user.password:
                        user.set_password(request.POST['password'])
                        user.save()
                    return HttpResponseRedirect(reverse('server:home'))
            return HttpResponseRedirect(reverse('xabber-web'))
        return self.render_to_response({"form": form, 'user_ip': user_ip})


class LogoutView(AuthMixin, View):
    def get(self, request, *args, **kwargs):
        logout_full(request)
        return HttpResponseRedirect(get_default_url(request.user))


class RequestUserPasswordView(PageContextMixin, View):
    def post(self, request, *args, **kwargs):
        current_path = request.POST.get('current_path')
        form = LoginForm(request.POST)
        if form.is_valid():
            custom_login(request, form)
        else:
            error = 'The password you have entered is invalid.'
            messages.add_message(request, messages.ERROR, error,
                                 extra_tags='request_user_pass_form_errors')

            # for error_list in form.errors.values():
            #     messages.add_message(request, messages.ERROR, error_list[0],
            #                          extra_tags='request_user_pass_form_errors')
        return HttpResponseRedirect(current_path)
