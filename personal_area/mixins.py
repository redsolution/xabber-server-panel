from django.http import HttpResponseRedirect
from django.urls import reverse

from virtualhost.models import User
from xmppserverui.mixins import AuthMixin


class PersonalAreaContextMixin(AuthMixin):
    permission_methods = AuthMixin.permission_methods + ['is_valid_token']
    extra_init_methods = ['init_page_context', 'fill_page_context']

    def is_valid_token(self, request, *args, **kwargs):
        request.user.api.registered_vhosts(data={})
        if request.user.api.status_code == 401:
            return HttpResponseRedirect(reverse('auth:logout'))

    def get_user(self, request):
        username = request.session.get('_auth_user_username')
        host = request.session.get('_auth_user_host')
        try:
            user = User.objects.get(username=username, host=host)
        except User.DoesNotExist:
            user = None
        return user

    def init_page_context(self, request, *args, **kwargs):
        user = self.get_user(request)
        page_data = {
            'section': getattr(self, 'page_section', '')
        }
        page_data.update(kwargs)
        self.context = {
            'page': page_data,
            'auth_user': user
        }

    def fill_page_context(self, request, *args, **kwargs):
        pass

    def get_context_data(self, **kwargs):
        return self.context

    def render_to_response(self, context, **response_kwargs):
        self.context.update(context)
        return super(PersonalAreaContextMixin, self).render_to_response(self.context, **response_kwargs)