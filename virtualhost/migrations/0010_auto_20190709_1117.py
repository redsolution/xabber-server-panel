# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-07-09 11:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('virtualhost', '0009_auto_20190704_1215'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupChat',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256)),
                ('host', models.CharField(max_length=256)),
                ('owner', models.CharField(max_length=256)),
                ('members', models.PositiveSmallIntegerField()),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='groupchat',
            unique_together=set([('name', 'host')]),
        ),
    ]
