from django.urls import path
from xabber_server_panel.base_modules.modules import views


urlpatterns = [
    # modules
    path('', views.Modules.as_view(), name='root'),
    path('delete/<str:module>/', views.DeleteModule.as_view(), name='delete_module'),
    path('upload/<str:module_name>/<str:track>/', views.UploadModule.as_view(), name='upload_module'),

    # Xabber Services
    path('xservices/login/', views.LoginXabberServices.as_view(), name='xservices_login'),
    path('xservices/confirm/', views.ConfirmXabberServices.as_view(), name='xservices_confirm')
]
