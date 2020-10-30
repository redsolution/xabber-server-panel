from django.conf.urls import url, include
from django.conf import settings
from modules_installation import views

app_name = 'modules_installation'

urlpatterns = []

for module in settings.MODULES_SPECS:
    urlpatterns += [url(r'^%s/' % module['name'], include('modules.%s.urls' % module['name'], namespace='%s' % module['name'])),]

urlpatterns+= [
    url(r'^(?P<module>[^/]*)/?(?P<path>.*)$', views.module_view_detail, name='modules-path'),
]