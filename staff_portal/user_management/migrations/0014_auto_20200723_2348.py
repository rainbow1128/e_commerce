# Generated by Django 3.1 on 2020-07-23 15:48

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_management', '0013_auto_20200722_2355'),
    ]

    operations = [
        migrations.AlterField(
            model_name='phonenumber',
            name='country_code',
            field=models.CharField(max_length=3, validators=[django.core.validators.RegexValidator(message='', regex='^\\+?1?\\d{9,15}$')]),
        ),
        migrations.AlterField(
            model_name='phonenumber',
            name='line_number',
            field=models.CharField(max_length=15, validators=[django.core.validators.RegexValidator(message='', regex='^?\\d{1,3}$')]),
        ),
    ]
