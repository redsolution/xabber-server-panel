from django.conf.urls import url

from modules_installation import views

app_name = 'modules_installation'

urlpatterns = [
    url(r'^$', views.ManageModulesView.as_view(), name='modules-list'),
    url(r'^add$', views.UploadModuleFileView.as_view(), name='upload-module'),
]
