# -*- coding: utf-8 -*-
from django.core.management import BaseCommand

from api.api import EjabberdAPI
from virtualhost.models import User


ADMIN_USERNAME = 'admin@xmppdev01.xabber.com'
# ADMIN_USERNAME = 'admin@c0032.soni.redsolution.ru'
ADMIN_PASSWORD = '123'
USERS_HOST = 'xmppdev01.xabber.com'
# USERS_HOST = 'c0032-virt01.soni.redsolution.ru'


class Command(BaseCommand):
    def handle(self, *args, **options):
        api = EjabberdAPI()
        api.login({"username": ADMIN_USERNAME,
                   "password": ADMIN_PASSWORD})

        users = api.xabber_registered_users({"host": USERS_HOST})
        for username in users:
            user, created = User.objects.get_or_create(username=username,
                                                       host=USERS_HOST)
            nickname, first_name, last_name = None, None, None
            api.get_vcard({"user": username, "host": USERS_HOST, "name": "nickname"})
            if api.success:
                nickname = api.response["content"]

            api.get_vcard2(
                {"user": username, "host": USERS_HOST, "name": "n", "subname": "given"})
            if api.success:
                first_name = api.response["content"]

            api.get_vcard2(
                {"user": username, "host": USERS_HOST, "name": "n", "subname": "family"})
            if api.success:
                last_name = api.response["content"]

            print nickname, first_name, last_name

            user.nickname = nickname
            user.first_name = first_name
            user.last_name = last_name
            user.save()
