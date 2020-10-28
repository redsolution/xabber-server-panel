from django.http import HttpResponseRedirect
from django.urls import reverse

from xmppserverui.mixins import PageContextMixin


class ModuleAccessMixin(PageContextMixin):
    permission_methods = ['is_has_permission']

    def is_has_permission(self, request, *args, **kwargs):
        # TODO: create permission model
        has_permission = True
        if not has_permission:
            return HttpResponseRedirect(reverse('admin_page'))