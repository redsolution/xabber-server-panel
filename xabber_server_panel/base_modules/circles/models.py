from django.db import models
from django.utils import timezone

from xabber_server_panel.base_modules.users.models import User


class Circle(models.Model):

    class Meta:
        ordering = ['circle']

    circle = models.CharField(
        max_length=256,
    )
    host = models.CharField(
        max_length=256,
    )
    name = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )
    description = models.CharField(
        max_length=256,
        blank=True,
        default=''
    )
    subscribes = models.TextField(
        null=True,
        blank=True
    )
    created = models.DateTimeField(
        default=timezone.now,
        blank=True
    )
    prefix = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )
    members = models.ManyToManyField(
        User,
        blank=True,
        related_name='circles'
    )
    all_users = models.BooleanField(
        default=False
    )

    class Meta:
        unique_together = ('circle', 'host')

    @property
    def full_jid(self):
        return u'{}@{}'.format(self.circle, self.host)

    @property
    def is_system(self):
        return self.prefix is not None

    @property
    def get_subscribes(self):
        if self.subscribes:
            return self.subscribes.split(',')
        else:
            return []

    @property
    def get_members_list(self):
        members = []
        for member in self.members.all():
            members += [member.full_jid]
        return members

    def __str__(self):
        return self.full_jid

    @property
    def get_members_count(self):
        if self.all_users:
            return User.objects.filter(status='ACTIVE', host=self.host).count()
        else:
            return self.members.count()