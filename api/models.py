from .utils import token_to_int


class EjabberdAccountPK(object):
    def value_to_string(self, user):
        if user.backend == 'api.backends.DjangoUserBackend':
            return user.django_user.pk
        return token_to_int(user.pk)


class EjabberdAccount(object):
    class Meta(object):
        def __init__(self):
            self.pk = EjabberdAccountPK()

    def __init__(self, api, user=None):
        self.USERNAME_FIELD = 'username'
        self.is_authenticated = True
        self.is_anonymous = False
        self.api = api
        self.django_user = user
        self.pk = api.token
        self._meta = self.Meta()

    def save(self, *args, **kwargs):
        pass

