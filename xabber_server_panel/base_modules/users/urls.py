from django.urls import path
from xabber_server_panel.base_modules.users.views import CreateUser, UserDetail, UserList, UserVcard, \
    UserCircles, UserPermissions, UserDelete, UserBlock, UserUnBlock


urlpatterns = [
    path('', UserList.as_view(), name='list'),
    path('create/', CreateUser.as_view(), name='create'),
    path('detail/<int:id>/', UserDetail.as_view(), name='detail'),
    path('block/<int:id>/', UserBlock.as_view(), name='block'),
    path('unblock/<int:id>/', UserUnBlock.as_view(), name='unblock'),
    path('delete/<int:id>/', UserDelete.as_view(), name='delete'),
    path('vcard/<int:id>/', UserVcard.as_view(), name='vcard'),
    path('manage_circles/<int:id>/', UserCircles.as_view(), name='circles'),
    path('permissions/<int:id>/', UserPermissions.as_view(), name='permissions'),
]