import importlib
from django.http import HttpResponseRedirect
from django.views.generic import View, TemplateView
from django.urls import reverse
from server.models import RootPageSettings
from .utils import get_default_url
from server.utils import *


class DefaultView(View):
    def get(self, request):
        username = request.session.get('_auth_user_username')
        host = request.session.get('_auth_user_host')
        if username and host:
            user = User.objects.filter(username=username, host=host)
            if user.exists():
                user = user[0]
                return HttpResponseRedirect(get_default_url(request.user, django_user=user))
        return HttpResponseRedirect(get_default_url(request.user))


class RootView(TemplateView):
    template_name = 'server/root_stub.html'

    def get(self, request, *args, **kwargs):
        current_root = RootPageSettings.objects.first()
        if str(current_root) != "home_page":
            module_name = "modules.{}".format(current_root)
            try:
                module_views = importlib.import_module(module_name).views.RootView.as_view()
                return module_views(request)
            except(AttributeError, ModuleNotFoundError):
                pass
        return HttpResponseRedirect(reverse('server:home'))
