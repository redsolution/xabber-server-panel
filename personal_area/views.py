from django.views.generic import TemplateView

from django.urls import reverse
from django.http import HttpResponseRedirect, Http404
from .mixins import *
from virtualhost.models import *
from .forms import ChangeUserPasswordForm
from xmppserverui.utils import logout_full


class UserProfileDetailView(PersonalAreaContextMixin, TemplateView):
    page_section = 'personal-area'
    template_name = 'personal_area/index.html'

    def _get_vcard(self, request, curr_user):
        user = request.user
        nickname, first_name, last_name = None, None, None
        vcard = user.api.get_vcard({"username": curr_user.username,
                                    "host": curr_user.host})
        if user.api.success:
            if vcard.get('vcard'):
                nickname = vcard.get('vcard').get('nickname')
        try:
            first_name = vcard['vcard']['n']['given']
        except KeyError:
            pass
        try:
            last_name = vcard['vcard']['n']['family']
        except KeyError:
            pass

        return nickname, first_name, last_name

    def get(self, request, *args, **kwargs):
        user = self.get_user(request)
        if not user:
            logout_full(request)
            return HttpResponseRedirect(reverse('auth:login'))
        nickname, first_name, last_name = self._get_vcard(request, user)
        user.nickname = nickname
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        return self.render_to_response({
            'curr_user': user,
        })


class UserProfileChangePasswordView(PersonalAreaContextMixin, TemplateView):
    page_section = 'personal-area'
    template_name = 'personal_area/change_password.html'

    def get(self, request, *args, **kwargs):
        user = self.get_user(request)
        if not user:
            logout_full(request)
            return HttpResponseRedirect(reverse('auth:login'))
        if not user.allowed_change_password:
            return HttpResponseRedirect(reverse('error:403'))
        form = ChangeUserPasswordForm(request.user)

        return self.render_to_response({
            'curr_user': user,
            'form': form
        })

    def post(self, request, *args, **kwargs):
        user = self.get_user(request)
        if not user:
            logout_full(request)
            return HttpResponseRedirect(reverse('auth:login'))
        if not user.allowed_change_password:
            return HttpResponseRedirect(reverse('error:403'))
        form = ChangeUserPasswordForm(request.user, request.POST, user_to_change=user)
        if form.is_valid():
            return HttpResponseRedirect(reverse('personal-area:profile'))
        return self.render_to_response({"curr_user": user,
                                        "form": form})
