from django.conf.urls import url, include
from django.conf import settings
from modules_installation import views

app_name = 'modules_installation'

urlpatterns = [
    url(r'^add$', views.UploadModuleFileView.as_view(), name='upload-module'),
]

for module in settings.MODULES_NAMES:
    urlpatterns += [url(r'^%s/' % module['name'], include('modules.%s.urls' % module['name'], namespace='%s' % module['name'])),]


