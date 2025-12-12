from django.db import models


class XServicesToken(models.Model):

    token = models.TextField(unique=True)
    expires = models.DateTimeField()
    jid = models.EmailField(unique=True)