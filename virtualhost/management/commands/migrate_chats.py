# -*- coding: utf-8 -*-
from django.core.management import BaseCommand

from api.api import EjabberdAPI
from virtualhost.models import GroupChat


ADMIN_USERNAME = 'admin@xmppdev01.xabber.com'
ADMIN_PASSWORD = '123'
USERS_HOST = 'xmppdev01.xabber.com'


class Command(BaseCommand):
    def handle(self, *args, **options):
        api = EjabberdAPI()
        api.login({"username": ADMIN_USERNAME,
                   "password": ADMIN_PASSWORD})

        chats = api.xabber_registered_chats({"host": USERS_HOST})
        for chat in chats:
            GroupChat.objects.create(name=chat["name"], host=USERS_HOST,
                                     owner=chat["owner"],  members=chat["number"])
