# Generated by Django 3.1 on 2020-11-03 14:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('user_management', '0026_auto_20201103_1457'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='genericgroupappliedrole',
            name='group',
        ),
        migrations.AddField(
            model_name='genericgroupappliedrole',
            name='user_id',
            field=models.PositiveIntegerField(db_column='user_id', default=12),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='genericgroupappliedrole',
            name='user_type',
            field=models.ForeignKey(db_column='user_type', default=9, limit_choices_to=models.Q(models.Q(('app_label', 'user_management'), ('model', 'GenericUserProfile')), models.Q(('app_label', 'user_management'), ('model', 'GenericUserGroup')), _connector='OR'), on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'),
            preserve_default=False,
        ),
    ]
