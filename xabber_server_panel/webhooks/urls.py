# -*- coding: utf-8 -*-
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from xabber_server_panel.webhooks.views import Hook


urlpatterns = [
    path('<path:hook_path>', csrf_exempt(Hook.as_view()), name='hook'),
]
