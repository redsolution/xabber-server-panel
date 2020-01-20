from django.conf.urls import url

from virtualhost import views

app_name = 'xmppserverui'

urlpatterns = [
    url(r'^users/$', views.UserListView.as_view(), name='users'),
    url(r'^users/create/$', views.UserCreateView.as_view(), name='user-create'),
    url(r'^users/(?P<user_id>[0-9]+)/created/$', views.UserCreatedView.as_view(), name='user-created'),
    url(r'^users/(?P<user_id>[0-9]+)/details/$', views.UserDetailsView.as_view(), name='user-details'),
    url(r'^users/(?P<user_id>[0-9]+)/instructions/$', views.UserInstructionView.as_view(), name='user-instruction'),
    url(r'^users/(?P<user_id>[0-9]+)/vcard/$', views.UserVcardView.as_view(), name='user-vcard'),
    url(r'^users/(?P<user_id>[0-9]+)/security/$', views.UserSecurityView.as_view(), name='user-security'),
    url(r'^users/(?P<user_id>[0-9]+)/groups/$', views.UserGroupsView.as_view(), name='user-groups'),
    url(r'^users/(?P<user_id>[0-9]+)/delete/$', views.DeleteUserView.as_view(), name='user-delete'),
    url(r'^groups/$', views.GroupListView.as_view(), name='groups'),
    url(r'^groups/create/$', views.GroupCreateView.as_view(), name='group-create'),
    url(r'^groups/created/$', views.GroupCreatedView.as_view(), name='group-created'),
    url(r'^groups/(?P<group_id>[0-9]+)/details/$', views.GroupDetailsView.as_view(), name='group-details'),
    url(r'^groups/(?P<group_id>[0-9]+)/members/$', views.GroupMembersView.as_view(), name='group-members'),
    url(r'^groups/(?P<group_id>[0-9]+)/members/manage/$', views.GroupMembersSelectView.as_view(), name='group-members-select'),
    url(r'^groups/(?P<group_id>[0-9]+)/sharedcontacts/$', views.GroupSubscribersView.as_view(), name='group-subscriptions'),
    url(r'^groups/(?P<group_id>[0-9]+)/delete/$', views.DeleteGroupView.as_view(), name='group-delete'),
    url(r'^chats/$', views.ChatListView.as_view(), name='chats'),
]
