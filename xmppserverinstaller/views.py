# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import socket

from django.views.generic import TemplateView
from django.urls import reverse
from django.http import HttpResponseRedirect

from django.conf import settings

from xmppserverinstaller.mixins import *
from xmppserverinstaller.utils import install_cmd
from .forms import *
from .utils import load_predefined_config


from virtualhost.utils import get_system_group_suffix

from virtualhost.models import *


def create_db_group_links(data):
    group = Group(
        group=data['xmpp_host'],
        host=data['xmpp_host'],
        name=settings.EJABBERD_EVERYBODY_DEFAULT_GROUP_NAME,
        description=settings.EJABBERD_EVERYBODY_DEFAULT_GROUP_DESCRIPTION,
        prefix=get_system_group_suffix()
    )
    group.save()
    member = GroupMember(
        group=group,
        username='@all@',
        host=data['xmpp_host']
    )
    member.save()


class InstallerStepperView(StepperInstallModeMixin, TemplateView):
    template_name = 'xmppserverinstaller/ui/stepper.html'

    def get(self, request, *args, **kwargs):
        step = InstallerForm.STEP_1
        form = InstallerForm(step=step)

        return self.render_to_response({
            "form": form,
            "step": step,
        })

    def post(self, request, *args, **kwargs):
        prev_action = False
        if 'next_to_step2' in request.POST:
            curr_step = InstallerForm.STEP_1
            next_step = InstallerForm.STEP_2

        elif 'next_to_step3' in request.POST:
            curr_step = InstallerForm.STEP_2
            next_step = InstallerForm.STEP_3

        elif 'next_to_step4' in request.POST:
            curr_step = InstallerForm.STEP_3
            next_step = InstallerForm.STEP_4

        elif 'prev_to_step1' in request.POST:
            curr_step = InstallerForm.STEP_2
            next_step = InstallerForm.STEP_1
            prev_action = True

        elif 'prev_to_step2' in request.POST:
            curr_step = InstallerForm.STEP_3
            next_step = InstallerForm.STEP_2
            prev_action = True

        elif 'prev_to_step3' in request.POST:
            curr_step = InstallerForm.STEP_4
            next_step = InstallerForm.STEP_3
            prev_action = True

        else:
            curr_step = InstallerForm.STEP_3
            next_step = InstallerForm.STEP_4

        form = InstallerForm(request.POST, step=curr_step)
        if 'submit' in request.POST and form.is_valid():
            try:
                success, message = install_cmd(request, data=form.cleaned_data)
            except Exception as e:
                success, message = False, e

            if not success:
                return self.render_to_response({
                    "form": form,
                    "step": next_step if form.is_valid() or prev_action else curr_step,
                    "installation_error": message
                })
            create_db_group_links(form.cleaned_data)
            return HttpResponseRedirect(reverse('installer:success-page'))

        return self.render_to_response({
            "form": form,
            "step": next_step if form.is_valid() or prev_action else curr_step
        })


class InstallerQuickView(QuickInstallModeMixin, TemplateView):
    template_name = 'xmppserverinstaller/ui/quick_mode.html'

    def get(self, request, *args, **kwargs):
        step = QuickInstallerModeForm.STEP_1
        stored_data = load_predefined_config()
        form = QuickInstallerModeForm(step=step, stored_data=stored_data)

        return self.render_to_response({
            "form": form,
            "step": step,
            "xmpp_host_value": stored_data["virtual_host"]
        })

    def post(self, request, *args, **kwargs):
        prev_action = False
        print(request.POST)
        if 'next_to_step2' in request.POST:
            curr_step = QuickInstallerModeForm.STEP_1
            next_step = QuickInstallerModeForm.STEP_2
        elif 'prev_to_step1' in request.POST:
            curr_step = QuickInstallerModeForm.STEP_2
            next_step = QuickInstallerModeForm.STEP_1
            prev_action = True
        else:
            curr_step = QuickInstallerModeForm.STEP_1
            next_step = QuickInstallerModeForm.STEP_2

        stored_data = load_predefined_config()
        form = QuickInstallerModeForm(request.POST, step=curr_step, stored_data=stored_data)
        if 'submit' in request.POST and form.is_valid():
            try:
                success, message = install_cmd(request, data=form.cleaned_data)
            except Exception as e:
                success, message = False, e

            if not success:
                return self.render_to_response({
                    "form": form,
                    "step": next_step if form.is_valid() or prev_action else curr_step,
                    "xmpp_host_value": stored_data["virtual_host"],
                    "installation_error": message
                })
            create_db_group_links(form.cleaned_data)
            return HttpResponseRedirect(reverse('server:dashboard'))

        return self.render_to_response({
            "form": form,
            "step": next_step if form.is_valid() or prev_action else curr_step,
            "xmpp_host_value": stored_data["virtual_host"]
        })


class SuccessInstallationView(TemplateView):
    template_name = 'xmppserverinstaller/ui/success.html'

    def get(self, request, *args, **kwargs):
        return self.render_to_response({
            'host': VirtualHost.objects.all()[0]
        })