"""xmppserverui URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .views import *


urlpatterns = [
    url(r'^auth/', include('auth.urls', namespace='auth')),
    url(r'^admin/server/', include('server.urls', namespace='server')),
    url(r'^admin/virtualhost/', include('virtualhost.urls', namespace='virtualhost')),
    url(r'^admin/installation/', include('xmppserverinstaller.urls', namespace='installer')),
    url(r'^admin/$', DefaultView.as_view()),
    url(r'^admin', DefaultView.as_view()),
    url(r'^profile/', include('personal_area.urls', namespace='personal-area')),
    url(r'^$', XabberWebView.as_view(), name='xabber-web'),
    url(r'^firebase-messaging-sw.js', XabberWebFirebaseMessSWView.as_view()),

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)