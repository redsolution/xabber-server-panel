from django.urls import path
from xabber_server_panel.base_modules.circles.views import CircleList, CircleCreate, CircleDetail, CircleMembers, CircleShared, CirclesDelete, DeleteMember


urlpatterns = [
    path('', CircleList.as_view(), name='list'),
    path('create/', CircleCreate.as_view(), name='create'),
    path('detail/<int:id>/', CircleDetail.as_view(), name='detail'),
    path('delete/<int:id>/', CirclesDelete.as_view(), name='delete'),
    path('members/<int:id>/', CircleMembers.as_view(), name='members'),
    path('members/delete/<int:circle_id>/<int:member_id>/', DeleteMember.as_view(), name='delete_member'),
    path('shared/<int:id>/', CircleShared.as_view(), name='shared'),
]
