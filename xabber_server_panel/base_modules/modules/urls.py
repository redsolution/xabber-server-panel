from django.urls import path
from xabber_server_panel.base_modules.modules import views


urlpatterns = [
    # modules
    path('', views.Installed.as_view(), name='root'),
    path('catalogue/', views.Catalogue.as_view(), name='catalogue'),
    path('delete/<str:module>/', views.DeleteModule.as_view(), name='delete_module'),
    path('upload/<str:module_name>/<str:track>/', views.DownloadModule.as_view(), name='download_module'),
    path('upload/', views.Upload.as_view(), name='upload'),

    # Xabber Services
    path('xservices/login/', views.LoginXabberServices.as_view(), name='xservices_login'),
    path('xservices/confirm/', views.ConfirmXabberServices.as_view(), name='xservices_confirm'),
    path('xservices/logout/', views.LogoutXabberServices.as_view(), name='xservices_logout')
]
