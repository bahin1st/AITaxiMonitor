# Generated by Django 5.1.7 on 2025-04-07 07:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0004_alter_taxi_route'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='anomaly',
            name='severity',
        ),
    ]
