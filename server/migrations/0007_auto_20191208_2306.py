# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-12-08 23:06
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0006_auto_20191208_2251'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ldapauthuid',
            name='ldap_uidattr',
            field=models.CharField(default=b'uid', max_length=100),
        ),
        migrations.AlterField(
            model_name='ldapauthuid',
            name='ldap_uidattr_format',
            field=models.CharField(default=b'%u', max_length=100),
        ),
    ]