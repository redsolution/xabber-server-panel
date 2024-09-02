from django.urls import path, include
from .views import GroupList, GroupCreate, GroupDelete


urlpatterns = [
    path('', GroupList.as_view(), name='list'),
    path('create/', GroupCreate.as_view(), name='create'),
    path('delete/<str:localpart>/', GroupDelete.as_view(), name='delete'),
]
