# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.apps import AppConfig

import xmppserverui.utils


class XMPPServerUIConfig(AppConfig):
    name = 'xmppserverui'

    # def ready(self):
    #     xmppserverui.utils.start_ejabberd()
