# -*- coding: utf-8 -*-
from django.conf.urls import url

from xmppserverinstaller import views

app_name = 'xmppserverui'

urlpatterns = [
    url(r'^$', views.InstallerStepperView.as_view(), name='stepper'),
    url(r'^quick/$', views.InstallerQuickView.as_view(), name='quick'),
    url(r'^success/$', views.SuccessInstallationView.as_view(), name='success-page'),
]
