from .api import EjabberdAPI
from .models import EjabberdAccount
from .utils import int_to_token

from virtualhost.models import User


class EjabberdAPIBackend(object):
    def authenticate(self, request, api=None, **kwargs):
        if api is None:
            return None
        return EjabberdAccount(api) if api.authorized else None

    def get_user(self, hash_token):
        try:
            token = int_to_token(hash_token)
        except Exception as e:
            return None
        api = EjabberdAPI()
        api.fetch_token(token)
        try:
            return EjabberdAccount(api)
        except KeyError:
            return None


class DjangoUserBackend(object):
    def authenticate(self, request, username, password, **kwargs):
        username, host = username.split('@')
        try:
            user = User.objects.get(username=username, host=host)
        except User.DoesNotExist:
            return None
        if user.is_admin and user.check_password(password):
            api = EjabberdAPI()
            return EjabberdAccount(api, user=user)
        return None

    def get_user(self, user_id):
        try:
            user = User.objects.get(id=user_id)
            api = EjabberdAPI()
            return EjabberdAccount(api, user=user)
        except User.DoesNotExist:
            return None
