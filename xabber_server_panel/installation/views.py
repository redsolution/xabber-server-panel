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


class InstallationAbstractView(TemplateView):

    form = InstallationForm()

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


class Steps(InstallationAbstractView):

    template_name = 'installation/steps.html'

    def get(self, request, *args, **kwargs):

        if server_installed():
            return HttpResponseRedirect(reverse('root'))

        data = load_predefined_config()
        self.form = InstallationForm(data)

        step = self.form.get_step(default_step=3)

        context = {
            'form': self.form,
            'step': step
        }

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):

        self.form = InstallationForm(request.POST)

        try:
            previous = int(request.POST.get('previous'))
        except:
            previous = None

        try:
            current_step = int(request.POST.get('step'))
        except:
            current_step = 1

        context = {}

        # don't validate form if previous
        if previous:
            return self.render_to_response({
                "form": self.form,
                'step': previous
            })

        else:
            step = self.form.get_step(current_step=current_step)

            if not step:
                try:
                    self.form.full_clean()
                    predefined_config = load_predefined_config()
                    self.form.cleaned_data['base_cronjobs'] = predefined_config.get('base_cronjobs')

                    success, message = install_cmd(request, data=self.form.cleaned_data)
                except Exception as e:
                    success, message = False, e
                    print(e)

                if success:
                    self.after_install()
                    return HttpResponseRedirect(reverse('installation:success'))
                else:
                    step = 4
                    context['installation_error'] = message

        context['step'] = step
        context['form'] = self.form
        return self.render_to_response(context)


class Quick(InstallationAbstractView):

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


class Success(TemplateView):
    template_name = 'installation/success.html'

    def get(self, request, *args, **kwargs):
        return self.render_to_response(
            {
                'host': VirtualHost.objects.first()
            }
        )