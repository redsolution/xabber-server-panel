from django.conf.urls import url
from virtualhost import views
from xmppserverui.decorators import custom_permission_required

app_name = 'xmppserverui'

urlpatterns = [
    url(r'^users/$', custom_permission_required('virtualhost.view_user')(views.UserListView.as_view()), name='users'),
    url(r'^users/create/$', custom_permission_required(('virtualhost.view_user', 'virtualhost.add_user'))(views.UserCreateView.as_view()), name='user-create'),
    url(r'^users/(?P<user_id>[0-9]+)/created/$', custom_permission_required('virtualhost.view_user')(views.UserCreatedView.as_view()), name='user-created'),
    url(r'^users/(?P<user_id>[0-9]+)/details/$', custom_permission_required('virtualhost.view_user')(views.UserDetailsView.as_view()), name='user-details'),
    url(r'^users/(?P<user_id>[0-9]+)/instructions/$', custom_permission_required('virtualhost.view_user')(views.UserInstructionView.as_view()), name='user-instruction'),
    url(r'^users/(?P<user_id>[0-9]+)/vcard/$', custom_permission_required(('virtualhost.view_user', 'virtualhost.change_user'))(views.UserVcardView.as_view()), name='user-vcard'),
    url(r'^users/(?P<user_id>[0-9]+)/security/$', custom_permission_required(('virtualhost.view_user', 'virtualhost.change_user'))(views.UserSecurityView.as_view()), name='user-security'),
    url(r'^users/(?P<user_id>[0-9]+)/groups/$', custom_permission_required(('virtualhost.view_user', 'virtualhost.change_user', 'virtualhost.view_group', 'virtualhost.change_group'))(views.UserGroupsView.as_view()), name='user-groups'),
    url(r'^users/(?P<user_id>[0-9]+)/permissions/$', custom_permission_required('is_admin')(views.UserPermissionsView.as_view()), name='user-permissions'),
    url(r'^users/(?P<user_id>[0-9]+)/delete/$', custom_permission_required(('virtualhost.view_user', 'virtualhost.delete_user'))(views.DeleteUserView.as_view()), name='user-delete'),
    url(r'^groups/$', custom_permission_required('virtualhost.view_group')(views.GroupListView.as_view()), name='groups'),
    url(r'^groups/create/$', custom_permission_required(('virtualhost.view_group', 'virtualhost.add_group'))(views.GroupCreateView.as_view()), name='group-create'),
    url(r'^groups/created/$', custom_permission_required('virtualhost.view_group')(views.GroupCreatedView.as_view()), name='group-created'),
    url(r'^groups/(?P<group_id>[0-9]+)/details/$', custom_permission_required(('virtualhost.view_group', 'virtualhost.change_group'))(views.GroupDetailsView.as_view()), name='group-details'),
    url(r'^groups/(?P<group_id>[0-9]+)/members/$', custom_permission_required(('virtualhost.view_user', 'virtualhost.add_user', 'virtualhost.change_user', 'virtualhost.view_group', 'virtualhost.change_group'))(views.GroupMembersView.as_view()), name='group-members'),
    url(r'^groups/(?P<group_id>[0-9]+)/members/manage/$', custom_permission_required(('virtualhost.view_user', 'virtualhost.change_user', 'virtualhost.view_group', 'virtualhost.change_group'))(views.GroupMembersSelectView.as_view()), name='group-members-select'),
    url(r'^groups/(?P<group_id>[0-9]+)/sharedcontacts/$', custom_permission_required(('virtualhost.view_group', 'virtualhost.change_group'))(views.GroupSubscribersView.as_view()), name='group-subscriptions'),
    url(r'^groups/(?P<group_id>[0-9]+)/delete/$', custom_permission_required(('virtualhost.view_group', 'virtualhost.delete_group'))(views.DeleteGroupView.as_view()), name='group-delete'),
    url(r'^chats/$', custom_permission_required('virtualhost.view_groupchat')(views.ChatListView.as_view()), name='chats'),
]
