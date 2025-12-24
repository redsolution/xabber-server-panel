from django.urls import path
from xabber_server_panel.base_modules.modules import views


urlpatterns = [
    # modules
    path('', views.Installed.as_view(), name='root'),
    path('catalogue/', views.Catalogue.as_view(), name='catalogue'),
    path('license/', views.License.as_view(), name='license'),
    path('detail/<str:module_name>/<str:track>/', views.Detail.as_view(), name='detail'),
    path('delete/<str:module>/', views.DeleteModule.as_view(), name='delete_module'),
    path('download/<str:module_name>/free/', views.DownloadModuleFree.as_view(), name='download_module_free'),
    path('download/<str:module_name>/paid/', views.DownloadModulePaid.as_view(), name='download_module_paid'),
    path('upload/', views.Upload.as_view(), name='upload'),

    # Xabber Services
    path('xservices/login/', views.LoginXabberServices.as_view(), name='xservices_login'),
    path('xservices/confirm/', views.ConfirmXabberServices.as_view(), name='xservices_confirm'),
    path('xservices/logout/', views.LogoutXabberServices.as_view(), name='xservices_logout')
]
