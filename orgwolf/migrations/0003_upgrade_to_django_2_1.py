# Generated by Django 2.0.9 on 2018-11-27 03:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orgwolf', '0002_upgrade_to_django_1_11'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orgwolfuser',
            name='last_name',
            field=models.CharField(blank=True, max_length=150, verbose_name='last name'),
        ),
    ]
