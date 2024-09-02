from django.urls import path, include


urlpatterns = [
    path('dashboard/', include(('xabber_server_panel.base_modules.dashboard.urls', 'dashboard'), namespace='dashboard')),
    path('users/', include(('xabber_server_panel.base_modules.users.urls', 'users'), namespace='users')),
    path('circles/', include(('xabber_server_panel.base_modules.circles.urls', 'circles'), namespace='circles')),
    path('groups/', include(('xabber_server_panel.base_modules.groups.urls', 'groups'), namespace='groups')),
    path('registration/', include(('xabber_server_panel.base_modules.registration.urls', 'registration'), namespace='registration')),
    path('config/', include(('xabber_server_panel.base_modules.config.urls', 'config'), namespace='config')),
    path('log/', include(('xabber_server_panel.base_modules.log.urls', 'log'), namespace='log')),
]
