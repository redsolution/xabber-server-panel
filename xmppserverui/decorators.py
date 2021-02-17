from django.core.exceptions import PermissionDenied
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.conf import settings
from django.shortcuts import resolve_url
from functools import wraps
from urllib.parse import urlparse
from virtualhost.models import User


def custom_user_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            username = request.session.get('_auth_user_username')
            host = request.session.get('_auth_user_host')
            try:
                user = User.objects.get(username=username, host=host)
                if test_func(request, user):
                    return view_func(request, *args, **kwargs)
                path = request.build_absolute_uri()
                resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)

                login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
                current_scheme, current_netloc = urlparse(path)[:2]
                if ((not login_scheme or login_scheme == current_scheme) and
                        (not login_netloc or login_netloc == current_netloc)):
                    path = request.get_full_path()
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(
                    path, resolved_login_url, redirect_field_name)
            except User.DoesNotExist:
                return None
        return _wrapped_view
    return decorator


def custom_permission_required(perm, login_url=None, raise_exception=False, check_any=False):

    def check_perms(request, user):
        if perm == 'is_admin' and user.is_admin:
            return True
        elif perm == 'is_admin' and not user.is_admin:
            return False
        if isinstance(perm, str):
            perms = (perm,)
        else:
            if check_any:
                for permission in perm:
                    if user.has_perms((permission,)):
                        return True
            else:
                perms = perm
        if user.has_perms(perms):
            return True
        # In case the 403 handler should be called raise the exception
        if raise_exception:
            raise PermissionDenied
        # As the last resort, show the login form
        return False
    return custom_user_passes_test(check_perms, login_url=login_url)