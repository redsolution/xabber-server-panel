from xabber_server_panel.base_modules.users.decorators import permission_admin
from xabber_server_panel.base_modules.modules.utils import request_license_key

from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View


class ServicesHash(LoginRequiredMixin, View):

    @permission_admin
    def get(self, request, *args, **kwargs):

        result = request_license_key(request)
        if result.get('success'):
            services_hash = result.get('services_hash')

            return JsonResponse({
                "services_hash": services_hash
            })
        
        return JsonResponse(
            {"services_hash": None}
        )