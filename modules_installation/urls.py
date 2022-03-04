from django.conf.urls import url, include
from django.conf import settings
from modules_installation import views

app_name = 'modules_installation'

urlpatterns = []

# for module in list(filter(lambda k: 'modules.' in k, settings.INSTALLED_APPS)):
#     urlpatterns += [url(r'^%s/' % module, include('%s.urls' % module, namespace='%s' % module)),]

urlpatterns+= [
    url(r'^(?P<module>[^/]*)/?(?P<path>.*)$', views.module_view_detail, name='modules-path'),
]