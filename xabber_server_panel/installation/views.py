from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from django.contrib.auth import login

from xabber_server_panel.utils import server_installed
from xabber_server_panel.base_modules.config.models import VirtualHost
from xabber_server_panel.base_modules.config.utils import check_hosts_dns
from xabber_server_panel.custom_auth.forms import ApiAuthenticationForm

from .forms import InstallationForm
from .utils import install_cmd, create_circles, load_predefined_config


class Steps(TemplateView):

    template_name = 'installation/steps.html'

    def get(self, request, *args, **kwargs):

        if server_installed():
            return HttpResponseRedirect(reverse('root'))

        context = {
            'form': InstallationForm(),
            'step': '1'
        }

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):

        self.form = InstallationForm(request.POST)
        self.previous = request.POST.get('previous')
        self.step = request.POST.get('step', '1')
        response = self._validate_data()

        return response

    def _validate_data(self):

        """ Validates form depending of current step and return response """

        context = {}

        # don't validate form if previous
        if self.previous:
            return self.render_to_response({
                "form": self.form,
                'step': self.previous
            })

        # validate by step
        elif self.step == '1':
            context['step'] = '2' if self.form.validate_1_step() else '1'

        elif self.step == '2':
            context['step'] = '3' if self.form.validate_1_step() and self.form.validate_2_step() else '2'

        elif self.step == '3':
            # full clean if form filled
            if self.form.validate_1_step() and self.form.validate_2_step() and self.form.validate_3_step():


                try:
                    self.form.full_clean()
                    success, message = install_cmd(self.request, data=self.form.cleaned_data)
                except Exception as e:
                    success, message = False, e
                    print(e)

                if not success:
                    return self.render_to_response({
                        "form": self.form,
                        "installation_error": message,
                        'step': '4'
                    })

                self.after_install()
                return HttpResponseRedirect(reverse('installation:success'))

            # additional errors check
            else:
                if self.form.step_1_errors():
                    context['step'] = '1'
                elif self.form.step_2_errors():
                    context['step'] = '2'
                elif self.form.step_3_errors():
                    context['step'] = '3'

        context['form'] = self.form
        return self.render_to_response(context)

    def after_install(self):
        create_circles(self.form.cleaned_data)
        self._login_admin()
        check_hosts_dns()

    def _login_admin(self):
        data = {
            'username': f"{self.form.cleaned_data.get('username')}@{self.form.cleaned_data.get('host')}",
            'password': self.form.cleaned_data.get('password')
        }

        auth_form = ApiAuthenticationForm(data, request=self.request)

        if auth_form.is_valid():
            login(self.request, auth_form.user)


class Quick(TemplateView):

    template_name = 'installation/quick.html'

    def get(self, request, *args, **kwargs):

        if server_installed():
            return HttpResponseRedirect(reverse('root'))

        data = load_predefined_config()

        context = {
            'form': InstallationForm(),
            'data': data
        }

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):

        previous = request.POST.get('previous')

        data = load_predefined_config()
        data['username'] = request.POST.get('username')
        data['password'] = request.POST.get('password')

        self.form = InstallationForm(data)

        context = {
            "form": self.form
        }

        # don't validate form if previous
        if previous:
            return self.render_to_response(context)

        if self.form.is_valid():
            try:
                success, message = install_cmd(request, data=self.form.cleaned_data)
            except Exception as e:
                success, message = False, e
                print(e)

            if not success:
                return self.render_to_response({
                    "form": self.form,
                    "installation_error": message
                })

            self.after_install()
            return HttpResponseRedirect(reverse('installation:success'))

        return self.render_to_response(context)

    def after_install(self):
        create_circles(self.form.cleaned_data)
        self._login_admin()
        check_hosts_dns()

    def _login_admin(self):
        data = {
            'username': f"{self.form.cleaned_data.get('username')}@{self.form.cleaned_data.get('host')}",
            'password': self.form.cleaned_data.get('password')
        }

        auth_form = ApiAuthenticationForm(data, request=self.request)

        if auth_form.is_valid():
            login(self.request, auth_form.user)


class Success(TemplateView):
    template_name = 'installation/success.html'

    def get(self, request, *args, **kwargs):
        return self.render_to_response(
            {
                'host': VirtualHost.objects.first()
            }
        )