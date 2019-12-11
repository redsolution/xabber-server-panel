# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-11-27 10:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0003_auto_20191127_0942'),
    ]

    operations = [
        migrations.CreateModel(
            name='LDAPServer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('server', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='LDAPSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('port', models.PositiveSmallIntegerField()),
                ('rootdn', models.CharField(max_length=100)),
                ('password', models.CharField(max_length=50)),
            ],
        ),
        migrations.AddField(
            model_name='ldapserver',
            name='settings',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='server.LDAPSettings'),
        ),
    ]