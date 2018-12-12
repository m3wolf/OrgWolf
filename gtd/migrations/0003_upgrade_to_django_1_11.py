# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-23 21:04
from __future__ import unicode_literals

from django.db import migrations
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ('gtd', '0002_upgrade_to_django_1_9'),
    ]

    operations = [
        migrations.AlterField(
            model_name='node',
            name='parent',
            field=mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='gtd.Node'),
        ),
    ]