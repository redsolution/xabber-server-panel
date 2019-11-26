from django.conf.urls import url

from server import views


urlpatterns = [
    url(r'^dashboard/$', views.ServerDashboardView.as_view(), name='dashboard'),
    url(r'^stopped/$', views.ServerStoppedStubView.as_view(), name='stopped-stub'),
    url(r'^settings/$', views.ServerVhostsListView.as_view(), name='settings'),
    url(r'^settings/vhosts/$', views.ServerVhostsListView.as_view(), name='vhosts-list'),
    url(r'^settings/admins/$', views.ServerAdminsListView.as_view(), name='admins-list'),
    url(r'^settings/authbackends/$', views.ServerAuthBackendsListView.as_view(), name='auth-backends-list'),
    url(r'^settings/add/admin/$', views.ManageAdminsSelectView.as_view(), name='manage-admins'),
    url(r'^settings/add/vhost/$', views.AddVirtualHostView.as_view(), name='add-vhost'),
    url(r'^settings/manage/authbackends/$', views.ManageAuthBackendsView.as_view(), name='manage-auth-backends'),
    url(r'^settings/delete/vhost/(?P<vhost_id>[0-9]+)/$', views.DeleteVirtualHostView.as_view(), name='delete-vhost'),
    url(r'^settings/detail/vhost/(?P<vhost_id>[0-9]+)/$', views.VirtualHostDetauView.as_view(), name='detail-vhost'),
]
