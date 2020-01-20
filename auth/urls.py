from django.conf.urls import url

from auth import views

app_name = 'xmppserverui'

urlpatterns = [
    url(r'^login/$', views.LoginView.as_view(), name='login'),
    url(r'^request_password/$', views.RequestUserPasswordView.as_view(),
        name='request-user-password'),
    url(r'^logout/$', views.LogoutView.as_view(), name='logout'),
]
