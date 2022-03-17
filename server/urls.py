from django.conf.urls import url

from modules_installation.views import ManageModulesView, UploadModuleFileView
from server import views
from xmppserverui.decorators import custom_permission_required

app_name = 'xmppserverui'

urlpatterns = [
    url(r'^$', views.ServerHomePage.as_view(), name='home'),
    url(r'^dashboard/$', custom_permission_required('server.view_dashboard')(views.ServerDashboardView.as_view()), name='dashboard'),
    url(r'^stopped/$', views.ServerStoppedStubView.as_view(), name='stopped-stub'),
    url(r'^modules/$', custom_permission_required('is_admin')(ManageModulesView.as_view()), name='modules-list'),
    url(r'^add/modules/$', custom_permission_required('is_admin')(UploadModuleFileView.as_view()), name='upload-module'),
    url(r'^settings/$',  custom_permission_required('is_admin')(views.ServerVhostsListView.as_view()), name='settings'),
    url(r'^settings/vhosts/$', custom_permission_required('is_admin')(views.ServerVhostsListView.as_view()), name='vhosts-list'),
    url(r'^settings/admins/$', custom_permission_required('is_admin')(views.ServerAdminsListView.as_view()), name='admins-list'),
    url(r'^settings/keys/$', custom_permission_required('is_admin')(views.ServerKeysView.as_view()), name='registration-keys'),
    url(r'^settings/keys/(?P<key>[-\w]+)/$', custom_permission_required('is_admin')(views.ServerChangeKeysView.as_view()), name='change-key'),
    url(r'^settings/add/key/$', custom_permission_required('is_admin')(views.ServerAddKeysView.as_view()), name='add-key'),
    url(r'^settings/add/admin/$', custom_permission_required('is_admin')(views.ManageAdminsSelectView.as_view()), name='manage-admins'),
    url(r'^settings/add/vhost/$',  custom_permission_required('is_admin')(views.AddVirtualHostView.as_view()), name='add-vhost'),
    url(r'^settings/manage/ldap/$', custom_permission_required('is_admin')(views.ManageLDAPView.as_view()), name='manage-ldap'),
    url(r'^settings/delete/vhost/(?P<vhost_id>[0-9]+)/$', custom_permission_required('is_admin')(views.DeleteVirtualHostView.as_view()), name='delete-vhost'),
    url(r'^settings/detail/vhost/(?P<vhost_id>[0-9]+)/$', custom_permission_required('is_admin')(views.VirtualHostDetauView.as_view()), name='detail-vhost'),
]
