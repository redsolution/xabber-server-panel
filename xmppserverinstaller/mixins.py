from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from .utils import is_installation_mode, check_predefined_config
from xmppserverui.mixins import BaseMixin


class InstallationModeMixin(BaseMixin):
    permission_methods = ['check_mode']

    def check_mode(self, request, *args, **kwargs):
        if not is_installation_mode():
            return HttpResponseRedirect('/')


class QuickInstallModeMixin(InstallationModeMixin):
    permission_methods = InstallationModeMixin.permission_methods + ['is_quick_mode']

    def is_quick_mode(self, request, *args, **kwargs):
        if not check_predefined_config():
            return HttpResponseRedirect(reverse('installer:stepper'))


class StepperInstallModeMixin(InstallationModeMixin):
    permission_methods = InstallationModeMixin.permission_methods + ['is_stepper_mode']

    def is_stepper_mode(self, request, *args, **kwargs):
        if check_predefined_config():
            return HttpResponseRedirect(reverse('installer:quick'))
