from django.contrib.auth.views import LogoutView
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from django.urls import reverse
from django.contrib.auth import login

from xabber_server_panel.utils import is_ejabberd_started

from .forms import CustomAuthenticationForm, ApiAuthenticationForm


class CustomLoginView(TemplateView):
    template_name = 'auth/login.html'

    def get(self, request, *args, **kwargs):
        form = CustomAuthenticationForm()
        context = {
            'form': form
        }
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        next = request.POST.get('next')

        if is_ejabberd_started():
            form = ApiAuthenticationForm(request.POST, request=request)
        else:
            form = CustomAuthenticationForm(request.POST, request=request)

        if form.is_valid():
            login(request, form.user)
            if next:
                return HttpResponseRedirect(next)
            else:
                return HttpResponseRedirect(reverse('home'))

        context = {
            'form': form
        }

        return self.render_to_response(context)


class CustomLogoutView(LogoutView):
    next_page = 'custom_auth:login'