from django.conf.urls import url

from personal_area import views

app_name = 'xmppserverui'

urlpatterns = [
    url(r'^change/password/$', views.UserProfileChangePasswordView.as_view(), name='change-password'),
    url(r'^', views.UserProfileDetailView.as_view(), name='profile'),
]
