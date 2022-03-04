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
            vcard = api.get_vcard({"username": username, "host": USERS_HOST})
            if api.success:
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

            print('{} {} {}'.format(nickname, first_name, last_name))

            user.nickname = nickname
            user.first_name = first_name
            user.last_name = last_name
            user.save()
