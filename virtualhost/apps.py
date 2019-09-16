# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig


class VirtualhostConfig(AppConfig):
    name = 'virtualhost'

    def ready(self):
        import virtualhost.signals
