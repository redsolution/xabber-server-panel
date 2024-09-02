from django.urls import path
from xabber_server_panel.base_modules.config import views


urlpatterns = [
    path('', views.ConfigRoot.as_view(), name='root'),

    # hosts
    path('hosts/', views.Hosts.as_view(), name='hosts'),
    path('host/create/', views.CreateHost.as_view(), name='host_create'),
    path('host/delete/<int:id>/', views.DeleteHost.as_view(), name='host_delete'),
    path('host/detail/<int:id>/', views.DetailHost.as_view(), name='host_detail'),
    path('host/change/', views.ChangeHost.as_view(), name='host_change'),
    path('check_records/', views.CheckDnsRecords.as_view(), name='check_records'),

    # admins
    path('admins/', views.Admins.as_view(), name='admins'),

    # ldap
    path('ldap/', views.Ldap.as_view(), name='ldap'),

    # modules
    path('modules/', views.Modules.as_view(), name='modules'),
    path('modules/delete/<str:module>/', views.DeleteModule.as_view(), name='delete_module'),

    # root
    path('root_page/', views.RootPageView.as_view(), name='root_page'),

    # cron
    path('cron_jobs/', views.CronJobs.as_view(), name='cron_jobs'),
    path('cron_create/', views.CronJobCreate.as_view(), name='cron_create'),
    path('cron_delete/<int:id>/', views.CronJobDelete.as_view(), name='cron_delete'),
    path('cron_change/<int:id>/', views.CronJobChange.as_view(), name='cron_change'),

    # certificates
    path('certificates/', views.Certificates.as_view(), name='certificates'),
    path('update_cert/<str:domain>/', views.UpdateCert.as_view(), name='update_cert'),
    path('upload_cert/', views.UploadCert.as_view(), name='upload_cert'),
    path('delete_cert/<str:name>/', views.DeleteCert.as_view(), name='delete_cert'),
]
