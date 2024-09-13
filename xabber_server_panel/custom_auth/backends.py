from xabber_server_panel.base_modules.users.models import User


class CustomAuthBackend:

    """
        Customized to allow authorization for administrators and users with any permissions.
         Also backend writes api token in user.token field if ejabberd server is started.
    """

    def authenticate(self, request, username, password, check_password=True, **kwargs):

        try:
            username, host = username.split('@')
            user = User.objects.get(
                username=username,
                host=host
            )
        except:
            return None

        # check permissions
        if (user.is_admin or user.has_any_permissions) and user.is_active:
            if check_password:
                if user.check_password(password):
                    return user
            else:
                return user
        return None

    def get_user(self, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
        return user