# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-05-29 10:46
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('virtualhost', '0005_auto_20190522_1204'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='photo',
            field=models.ImageField(null=True, upload_to=b'upload', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=[b'jpg', b'png', b'jpeg'])], verbose_name=b'Photo'),
        ),
    ]
