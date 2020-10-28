from django.conf.urls import url, include
from django.conf import settings
from modules_installation import views

app_name = 'modules_installation'

urlpatterns = [
    url(r'^$', views.ManageModulesView.as_view(), name='modules-list'),
    url(r'^add$', views.UploadModuleFileView.as_view(), name='upload-module'),
]

for module in settings.MODULES_SPECS:
    urlpatterns += [url(r'^%s/' % module['name'], include('modules.%s.urls' % module['name'], namespace='%s' % module['name'])),]


