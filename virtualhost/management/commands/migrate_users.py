# -*- coding: utf-8 -*-
from django.core.management import BaseCommand

from api.api import EjabberdAPI
from virtualhost.models import User


ADMIN_USERNAME = ''
ADMIN_PASSWORD = ''
USERS_HOST = ''


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

            print('{} {} {}'.format(nickname, first_name, last_name))

            user.nickname = nickname
            user.first_name = first_name
            user.last_name = last_name
            user.save()
