from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.contrib import auth
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin


def _user_has_perm(user, perm, obj):
    """
    A backend can raise `PermissionDenied` to short-circuit permission checking.
    """
    for backend in auth.get_backends():
        if not hasattr(backend, 'has_perm'):
            continue
        try:
            if backend.has_perm(user, perm, obj):
                return True
        except PermissionDenied:
            return False
    return False


class VirtualHost(models.Model):
    name = models.CharField(max_length=256)

    def __str__(self):
        return self.name


class User(AbstractBaseUser, PermissionsMixin):
    SQL = 'sql'
    LDAP = 'ldap'
    AUTH_BACKENDS = [
        (SQL, 'internal'),
        (LDAP, 'LDAP')
    ]
    username = models.CharField(max_length=256, unique=True)
    USERNAME_FIELD = 'username'
    password = models.CharField(max_length=128, null=True)
    auth_backend = models.CharField(max_length=128, choices=AUTH_BACKENDS, default=SQL)
    is_admin = models.BooleanField(default=False)
    host = models.CharField(max_length=256)
    nickname = models.CharField(max_length=100, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    photo = models.ImageField(
        verbose_name='Photo',
        upload_to='upload',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', 'jpeg'])],
        null=True
    )
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('username', 'host')

    @property
    def full_jid(self):
        return u'{}@{}'.format(self.username, self.host)

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            formatted_name = u'{} {}'.format(self.first_name, self.last_name).strip()
            if len(formatted_name) > 0:
                return formatted_name
            else:
                return self.full_jid
        else:
            return self.full_jid

    def get_full_name(self):
        full_name = u'{}@{}'.format(self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        return self.first_name

    @property
    def vhost(self):
        try:
            return VirtualHost.objects.get(name=self.host)
        except VirtualHost.DoesNotExist:
            return None

    @property
    def allowed_delete(self):
        return False if self.auth_backend == 'ldap' else True

    @property
    def allowed_change_vcard(self):
        return True

    @property
    def allowed_change_password(self):
        return False if self.auth_backend == 'ldap' else True

    def __str__(self):
        return self.full_jid

    def has_perm(self, perm, obj=None):
        """
        Return True if the user has the specified permission. Query all
        available auth backends, but return immediately if any backend returns
        True. Thus, a user who has permission from a single auth backend is
        assumed to have permission in general. If an object is provided, check
        permissions for that object.
        """
        # # Active superusers have all permissions.
        if self.is_active and self.is_superuser or self.is_active and self.is_admin:
            return True

        # Otherwise we need to check the backends.
        return _user_has_perm(self, perm, obj)


class Group(models.Model):
    group = models.CharField(max_length=256)
    host = models.CharField(max_length=256)
    name = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=256, null=True, blank=True)
    displayed_groups = models.CharField(max_length=256, null=True, blank=True)
    created = models.DateTimeField(default=timezone.now)
    prefix = models.CharField(max_length=10, null=True)

    class Meta:
        unique_together = ('group', 'host')

    @property
    def full_jid(self):
        return u'{}@{}'.format(self.group, self.host)

    @property
    def is_system(self):
        return self.prefix is not None

    def __str__(self):
        return self.full_jid


class GroupMember(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    username = models.CharField(max_length=256)
    host = models.CharField(max_length=256)

    class Meta:
        unique_together = ('group', 'username', 'host')

    @property
    def full_jid(self):
        if self.username != '@all@':
            return '{}@{}'.format(self.username, self.host)
        else:
            return 'all@{}'.format(self.host)

    def __str__(self):
        return self.full_jid


class GroupChat(models.Model):
    name = models.CharField(max_length=256)
    host = models.CharField(max_length=256)
    owner = models.CharField(max_length=256)
    members = models.PositiveSmallIntegerField()
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('name', 'host')

    @property
    def full_jid(self):
        return '{}@{}'.format(self.name, self.host)

    def __str__(self):
        return self.full_jid


class UserPassword(models.Model):
    # model is only for granting rights to change the user's password
    class Meta:
        managed = False
