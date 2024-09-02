from django.db import models
from django.utils import timezone
from django.apps import apps
from django.contrib.auth.hashers import make_password
from django.contrib.auth import _get_backends, load_backend
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator

from xabber_server_panel.base_modules.config.utils import get_modules
from xabber_server_panel.base_modules.config.models import VirtualHost


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, password, **extra_fields):
        """
        Create and save a user with the given username and password.
        """
        if not username:
            raise ValueError('The given username must be set')
        # Lookup the real model class from the global app registry so this
        # manager method can be used in migrations. This is fine because
        # managers are by definition working on the real model.
        GlobalUserModel = apps.get_model(self.model._meta.app_label, self.model._meta.object_name)
        username = GlobalUserModel.normalize_username(username)
        user = self.model(username=username, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, password, **extra_fields)

    def with_perm(self, perm, is_active=True, include_superusers=True, backend=None, obj=None):
        if backend is None:
            backends = _get_backends(return_tuples=True)
            if len(backends) == 1:
                backend, _ = backends[0]
            else:
                raise ValueError(
                    'You have multiple authentication backends configured and '
                    'therefore must provide the `backend` argument.'
                )
        elif not isinstance(backend, str):
            raise TypeError(
                'backend must be a dotted import path string (got %r).'
                % backend
            )
        else:
            backend = load_backend(backend)
        if hasattr(backend, 'with_perm'):
            return backend.with_perm(
                perm,
                is_active=is_active,
                include_superusers=include_superusers,
                obj=obj,
            )
        return self.none()


class User(AbstractBaseUser, PermissionsMixin):

    AUTH_BACKENDS = [
        ('sql', 'sql'),
        ('ldap', 'LDAP')
    ]

    STATUSES = [
        ('ACTIVE', 'ACTIVE'),
        ('BANNED', 'BANNED'),
        ('EXPIRED', 'EXPIRED'),
        ('BLOCKED', 'BLOCKED'),
    ]
    USERNAME_FIELD = 'username'
    username_validator = UnicodeUsernameValidator()
    objects = UserManager()

    username = models.CharField(
        max_length=256,
        validators=[
            username_validator
        ],
        error_messages={
            'unique': "A user with that username already exists.",
        },
    )
    password = models.CharField(max_length=128, null=True)
    auth_backend = models.CharField(
        max_length=128,
        choices=AUTH_BACKENDS,
        default='sql',
        blank=True
    )
    is_admin = models.BooleanField(default=False)
    host = models.CharField(
        max_length=256,
    )
    nickname = models.CharField(max_length=100, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    created = models.DateTimeField(
        default=timezone.now,
        blank=True
    )
    expires = models.DateTimeField(
        null=True,
        blank=True
    )
    status = models.CharField(
        choices=STATUSES,
        default='ACTIVE',
        max_length=255,
        blank=True
    )
    permissions = models.ManyToManyField(
        'CustomPermission',
        blank=True
    )
    reason = models.TextField(
        verbose_name='reason for blocking',
        blank=True,
        null=True
    )

    class Meta:
        unique_together = ['username', 'host']

    @property
    def is_active(self):
        return self.status == 'ACTIVE'

    @property
    def auth_backend_is_ldap(self):
        return self.auth_backend == 'ldap'

    @property
    def full_jid(self):
        return u'{}@{}'.format(self.username, self.host)

    @property
    def get_initials(self):
        if self.first_name and self.last_name:
            return u"{}{}".format(self.first_name[0], self.last_name[0])
        else:
            return self.username[0:2]

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return '%s %s' % (self.first_name, self.last_name)
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return ''

    @property
    def is_expired(self):
        return self.expires and self.expires < timezone.now()

    @property
    def has_any_permissions(self):
        return self.permissions.exists()

    def get_allowed_hosts(self):
        hosts = VirtualHost.objects.all()
        if not self.is_admin:
            hosts = hosts.filter(name=self.host)
        return hosts.values_list('name', flat=True)


def get_apps_choices():
    apps = [
        ('dashboard', 'Dashboard'),
        ('users', 'Users'),
        ('circles', 'Circles'),
        ('groups', 'Groups'),
        ('registration', 'Registration'),
        ('config', 'Settings'),
        ('log', 'Log'),
        *[(module, module) for module in get_modules()]
    ]
    return apps


class CustomPermission(models.Model):

    PERMISSIONS = [
        ('read', 'read'),
        ('write', 'write')
    ]

    permission = models.CharField(
        choices=PERMISSIONS,
        max_length=10
    )

    app = models.CharField(
        choices=get_apps_choices(),
        max_length=100
    )

    def __str__(self):
        return '%s - %s' % (self.app, self.get_permission_display())