from django.urls import path, include

from xabber_server_panel.views import HomePage, Search, Root, Suggestions, UpdatePanel
from xabber_server_panel.base_modules.config.utils import get_modules


urlpatterns = [
    path('', Root.as_view(), name='root'),
    path('panel/', HomePage.as_view(), name='home'),
    path('panel/update/', UpdatePanel.as_view(), name='update_panel'),
    path('panel/search/', Search.as_view(), name='search'),
    path('panel/suggestions/', Suggestions.as_view(), name='suggestions'),
    path('panel/', include('xabber_server_panel.base_modules.urls')),
    path('auth/', include(('xabber_server_panel.custom_auth.urls', 'custom_auth'), namespace='custom_auth')),
    path('webhooks/', include(('xabber_server_panel.webhooks.urls', 'webhooks'), namespace='webhooks')),
    path('installation/', include(('xabber_server_panel.installation.urls', 'installation'), namespace='installation')),
]

for module in get_modules():
    urlpatterns += [path('modules/%s/' % module, include(('modules.%s.urls' % module, module), namespace=module))]