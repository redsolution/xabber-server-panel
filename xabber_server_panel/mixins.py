from django.shortcuts import render
from django.views.generic.base import View
from .utils import is_ejabberd_started


class ServerStartedMixin(View):

    def dispatch(self, request, *args, **kwargs):
        # render dummy if ejabberd is not started
        if not is_ejabberd_started():
            return render(request, 'server_not_started.html', status=503)
        return super().dispatch(request, *args, **kwargs)
