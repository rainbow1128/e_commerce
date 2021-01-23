# Generated by Django 3.1 on 2020-08-21 07:32

from django.db import migrations, models
import django.db.models.deletion
from common.models.migrations import AlterTablePrivilege


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('user_management', '0018_genericusergroup_roles'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuotaUsageType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'quota_usage_type',
            },
        ),
        migrations.RemoveField(
            model_name='genericusergroup',
            name='max_bookings',
        ),
        migrations.RemoveField(
            model_name='genericusergroup',
            name='max_entry_waitlist',
        ),
        migrations.RemoveField(
            model_name='genericusergroup',
            name='max_num_addr',
        ),
        migrations.RemoveField(
            model_name='genericusergroup',
            name='max_num_email',
        ),
        migrations.RemoveField(
            model_name='genericusergroup',
            name='max_num_phone',
        ),
        migrations.RemoveField(
            model_name='genericusergroup',
            name='meta_path',
        ),
        migrations.RemoveField(
            model_name='genericuserprofile',
            name='max_bookings',
        ),
        migrations.RemoveField(
            model_name='genericuserprofile',
            name='max_entry_waitlist',
        ),
        migrations.RemoveField(
            model_name='genericuserprofile',
            name='max_num_addr',
        ),
        migrations.RemoveField(
            model_name='genericuserprofile',
            name='max_num_email',
        ),
        migrations.RemoveField(
            model_name='genericuserprofile',
            name='max_num_phone',
        ),
        migrations.CreateModel(
            name='UserQuotaRelation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.PositiveIntegerField(db_column='user_id')),
                ('maxnum', models.PositiveSmallIntegerField(default=1)),
                ('usage_type', models.ForeignKey(db_column='usage_type', on_delete=django.db.models.deletion.CASCADE, related_name='auth', to='user_management.quotausagetype')),
                ('user_type', models.ForeignKey(db_column='user_type', limit_choices_to=models.Q(models.Q(('app_label', 'user_management'), ('model', 'GenericUserProfile')), models.Q(('app_label', 'user_management'), ('model', 'GenericUserGroup')), _connector='OR'), on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'db_table': 'user_quota_relation',
            },
        ),
    ]

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_privilege_update_init'):
            for op in cls.operations:
                if isinstance(op, AlterTablePrivilege.ACCEPTED_OPERATIONS):
                    op._priv_lvl = AlterTablePrivilege.PRIVILEGE_MAP['READ_WRITE']
            privilege_update_obj = AlterTablePrivilege( autogen_ops=cls.operations,  db_setup_tag='usermgt_service')
            cls._privilege_update_init = True
        return super().__new__(cls)

