from django.conf.urls import url

from server import views
from xmppserverui.decorators import custom_permission_required

app_name = 'xmppserverui'

urlpatterns = [
    url(r'^dashboard/$', custom_permission_required('is_admin')(views.ServerDashboardView.as_view()), name='dashboard'),
    url(r'^stopped/$', views.ServerStoppedStubView.as_view(), name='stopped-stub'),
    url(r'^settings/$',  custom_permission_required('virtualhost.view_virtualhost')(views.ServerVhostsListView.as_view()), name='settings'),
    url(r'^settings/vhosts/$', custom_permission_required('virtualhost.view_virtualhost')(views.ServerVhostsListView.as_view()), name='vhosts-list'),
    url(r'^settings/admins/$', custom_permission_required(('virtualhost.view_virtualhost', 'virtualhost.view_user'))(views.ServerAdminsListView.as_view()), name='admins-list'),
    url(r'^settings/certs/$', custom_permission_required('virtualhost.view_virtualhost')(views.ManageCertsView.as_view()), name='certs-list'),
    url(r'^settings/add/admin/$', custom_permission_required(('virtualhost.view_virtualhost', 'virtualhost.view_user', 'virtualhost.change_user'))(views.ManageAdminsSelectView.as_view()), name='manage-admins'),
    url(r'^settings/add/cert/$', custom_permission_required('virtualhost.view_virtualhost')(views.UploadCertFileView.as_view()), name='upload-cert'),
    url(r'^settings/add/vhost/$',  custom_permission_required(('virtualhost.view_virtualhost', 'virtualhost.add_virtualhost'))(views.AddVirtualHostView.as_view()), name='add-vhost'),
    url(r'^settings/manage/ldap/$', custom_permission_required('virtualhost.view_virtualhost')(views.ManageLDAPView.as_view()), name='manage-ldap'),
    url(r'^settings/delete/cert/$', custom_permission_required('virtualhost.view_virtualhost')(views.DeleteCertFileView.as_view()), name='delete-cert'),
    url(r'^settings/delete/vhost/(?P<vhost_id>[0-9]+)/$', custom_permission_required(('virtualhost.view_virtualhost', 'virtualhost.delete_virtualhost'))(views.DeleteVirtualHostView.as_view()), name='delete-vhost'),
    url(r'^settings/detail/vhost/(?P<vhost_id>[0-9]+)/$', custom_permission_required('virtualhost.view_virtualhost')(views.VirtualHostDetauView.as_view()), name='detail-vhost'),
]
