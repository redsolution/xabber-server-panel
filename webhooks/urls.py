# -*- coding: utf-8 -*-
from django.conf.urls import url
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from webhooks import views

app_name = 'xmppserverui'

urlpatterns = [
    path('<path:hook_path>', csrf_exempt(views.Hook.as_view()), name='hook'),
]
