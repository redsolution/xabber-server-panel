from django.contrib.auth.models import Permission

from .api import EjabberdAPI
from .models import EjabberdAccount
from .utils import int_to_token
from django.contrib.auth import get_user_model
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

    def _get_user_permissions(self, user_obj):
        return user_obj.user_permissions.all()

    def _get_group_permissions(self, user_obj):
        user_groups_field = get_user_model()._meta.get_field('groups')
        user_groups_query = 'group__%s' % user_groups_field.related_query_name()
        return Permission.objects.filter(**{user_groups_query: user_obj})

    def _get_permissions(self, user_obj, obj, from_name):
        """
        Return the permissions of `user_obj` from `from_name`. `from_name` can
        be either "group" or "user" to return permissions from
        `_get_group_permissions` or `_get_user_permissions` respectively.
        """
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()

        perm_cache_name = '_%s_perm_cache' % from_name
        if not hasattr(user_obj, perm_cache_name):
            if user_obj.is_superuser:
                perms = Permission.objects.all()
            else:
                perms = getattr(self, '_get_%s_permissions' % from_name)(user_obj)
            perms = perms.values_list('content_type__app_label', 'codename').order_by()
            setattr(user_obj, perm_cache_name, {"%s.%s" % (ct, name) for ct, name in perms})
        return getattr(user_obj, perm_cache_name)

    def get_user_permissions(self, user_obj, obj=None):
        """
        Return a set of permission strings the user `user_obj` has from their
        `user_permissions`.
        """
        return self._get_permissions(user_obj, obj, 'user')

    def get_group_permissions(self, user_obj, obj=None):
        """
        Return a set of permission strings the user `user_obj` has from the
        groups they belong.
        """
        return self._get_permissions(user_obj, obj, 'group')

    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()
        if not hasattr(user_obj, '_perm_cache'):
            user_obj._perm_cache = {
                *self.get_user_permissions(user_obj),
                *self.get_group_permissions(user_obj),
            }
        return user_obj._perm_cache

    def has_perm(self, user_obj, perm, obj=None):
        return user_obj.is_active and perm in self.get_all_permissions(user_obj, obj)

    def has_module_perms(self, user_obj, app_label):
        """
        Return True if user_obj has any permissions in the given app_label.
        """
        return user_obj.is_active and any(
            perm[:perm.index('.')] == app_label
            for perm in self.get_all_permissions(user_obj)
        )
