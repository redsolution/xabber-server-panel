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
from django.conf.urls.static import static
from .views import *


urlpatterns = [
    url(r'^auth/', include('auth.urls', namespace='auth')),
    url(r'^admin/server/', include('server.urls', namespace='server')),
    url(r'^admin/server/modules/', include('modules_installation.urls', namespace='modules')),
    url(r'^admin/virtualhost/', include('virtualhost.urls', namespace='virtualhost')),
    url(r'^admin/installation/', include('xmppserverinstaller.urls', namespace='installer')),
    url(r'^admin/error/', include('error.urls', namespace='error')),
    url(r'^admin/registration/', include('registration.urls', namespace='registration')),
    url(r'^admin/$', DefaultView.as_view()),
    url(r'^admin', DefaultView.as_view(), name="admin_page"),
    url(r'^webhooks/', include('webhooks.urls', namespace='webhooks')),
    url(r'^$', RootView.as_view(), name='root-page'),
]
for module in list(filter(lambda k: 'modules.' in k, settings.INSTALLED_APPS)):
    urlpatterns += [url(r'^%s/' % module, include('%s.urls' % module, namespace='%s' % module)),]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
