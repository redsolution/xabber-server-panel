# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-05-22 11:41
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('virtualhost', '0003_auto_20190508_0701'),
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier', models.CharField(max_length=256)),
                ('host', models.CharField(max_length=256)),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('description', models.CharField(blank=True, max_length=256, null=True)),
                ('displayed_groups', models.CharField(blank=True, max_length=256, null=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='group',
            unique_together=set([('identifier', 'host')]),
        ),
    ]
