# Generated by Django 5.1.7 on 2025-04-12 05:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0006_taxi_current_ride_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taxi',
            name='current_lat',
            field=models.FloatField(default=43.239819),
        ),
        migrations.AlterField(
            model_name='taxi',
            name='current_lon',
            field=models.FloatField(default=76.903932),
        ),
    ]
