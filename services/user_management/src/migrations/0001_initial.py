# Generated by Django 3.1.8 on 2024-10-28 03:48

import django.contrib.auth.validators
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import ecommerce_common.models.mixins
import softdelete.models
import user_management.models.auth


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnauthResetAccountRequest',
            fields=[
                ('hashed_token', models.BinaryField(blank=True, max_length=32, primary_key=True, serialize=False)),
                ('time_created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'unauth_reset_account_request',
                'managed': False,
            },
            bases=(models.Model, ecommerce_common.models.mixins.MinimumInfoMixin),
        ),
        migrations.CreateModel(
            name='GenericUserGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_deleted', models.DateTimeField(blank=True, default=None, editable=False, null=True)),
                ('name', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'generic_user_group',
                'abstract': False,
            },
            bases=(models.Model, ecommerce_common.models.mixins.MinimumInfoMixin),
        ),
        migrations.CreateModel(
            name='GenericUserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_deleted', models.DateTimeField(blank=True, default=None, editable=False, null=True)),
                ('first_name', models.CharField(max_length=32)),
                ('last_name', models.CharField(max_length=32)),
                ('time_created', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'generic_user_profile',
                'abstract': False,
            },
            bases=(models.Model, ecommerce_common.models.mixins.MinimumInfoMixin),
        ),
        migrations.CreateModel(
            name='QuotaMaterial',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app_code', models.PositiveSmallIntegerField(choices=[(1, 'user management'), (2, 'product management'), (3, 'media'), (4, 'purchase/sale order'), (5, 'front store'), (7, 'payment'), (6, 'inventory')])),
                ('mat_code', models.PositiveSmallIntegerField()),
            ],
            options={
                'db_table': 'quota_material',
            },
        ),
        migrations.CreateModel(
            name='UsermgtChangeSet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('done_by', models.CharField(max_length=16)),
                ('time_created', models.DateTimeField(default=django.utils.timezone.now)),
                ('object_id', models.CharField(db_column='object_id', max_length=100)),
                ('content_type', models.ForeignKey(db_column='content_type', on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'db_table': 'usermgt_soft_delete_changeset',
            },
            bases=(models.Model, softdelete.models._SoftDeleteIdSerializerMixin),
        ),
        migrations.CreateModel(
            name='LoginAccount',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 64 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=32, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('password_last_updated', models.DateTimeField(verbose_name='password last updated')),
                ('profile', models.OneToOneField(db_column='profile', on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='account', serialize=False, to='user_management.genericuserprofile')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'db_table': 'login_account',
                'abstract': False,
                'swappable': 'AUTH_USER_MODEL',
            },
            bases=(models.Model, ecommerce_common.models.mixins.MinimumInfoMixin),
            managers=[
                ('objects', user_management.models.auth.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='UserQuotaRelation',
            fields=[
                ('time_deleted', models.DateTimeField(blank=True, default=None, editable=False, null=True)),
                ('user_id', models.PositiveIntegerField(db_column='user_id')),
                ('expiry', models.DateTimeField(blank=True, null=True)),
                ('maxnum', models.PositiveSmallIntegerField(default=1)),
                ('id', models.CharField(max_length=18, primary_key=True, serialize=False)),
                ('material', models.ForeignKey(db_column='material', on_delete=django.db.models.deletion.CASCADE, related_name='usr_relations', to='user_management.quotamaterial')),
                ('user_type', models.ForeignKey(db_column='user_type', limit_choices_to=models.Q(models.Q(('app_label', 'user_management'), ('model', 'GenericUserProfile')), models.Q(('app_label', 'user_management'), ('model', 'GenericUserGroup')), _connector='OR'), on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'db_table': 'user_quota_relation',
            },
        ),
        migrations.CreateModel(
            name='UsermgtSoftDeleteRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_created', models.DateTimeField(default=django.utils.timezone.now)),
                ('object_id', models.CharField(db_column='object_id', max_length=100)),
                ('changeset', models.ForeignKey(db_column='changeset', on_delete=django.db.models.deletion.CASCADE, related_name='soft_delete_records', to='user_management.usermgtchangeset')),
                ('content_type', models.ForeignKey(db_column='content_type', on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'db_table': 'usermgt_soft_delete_record',
            },
            bases=(models.Model, softdelete.models._SoftDeleteIdSerializerMixin),
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='name')),
                ('permissions', models.ManyToManyField(to='auth.Permission', verbose_name='permissions')),
            ],
            options={
                'verbose_name': 'role',
                'verbose_name_plural': 'roles',
                'db_table': 'usermgt_role',
            },
            bases=(models.Model, ecommerce_common.models.mixins.MinimumInfoMixin),
            managers=[
                ('objects', user_management.models.auth.RoleManager()),
            ],
        ),
        migrations.CreateModel(
            name='PhoneNumber',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.PositiveIntegerField(db_column='user_id')),
                ('country_code', models.CharField(max_length=3, validators=[django.core.validators.RegexValidator(message="non-digit character detected, or length of digits doesn't meet requirement. It must contain only digit e.g. '91', '886' , from 1 digit up to 3 digits", regex='^\\d{1,3}$')])),
                ('line_number', models.CharField(max_length=15, validators=[django.core.validators.RegexValidator(message="non-digit character detected, or length of digits doesn't meet requirement. It must contain only digits e.g. '9990099', from 7 digits up to 15 digits", regex='^\\+?1?\\d{7,15}$')])),
                ('user_type', models.ForeignKey(db_column='user_type', limit_choices_to=models.Q(models.Q(('app_label', 'user_management'), ('model', 'GenericUserProfile')), models.Q(('app_label', 'user_management'), ('model', 'GenericUserGroup')), _connector='OR'), on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'db_table': 'phone_number',
            },
        ),
        migrations.CreateModel(
            name='GeoLocation',
            fields=[
                ('user_id', models.PositiveIntegerField(db_column='user_id')),
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('country', models.CharField(choices=[('AU', 'Australia'), ('AT', 'Austria'), ('CZ', 'Czechia'), ('DE', 'Deutsch'), ('HK', 'Hong Kong'), ('IN', 'India'), ('ID', 'Indonesia'), ('IL', 'Israel'), ('MY', 'Malaysia'), ('NZ', 'New Zealand'), ('PT', 'Portugal'), ('SG', 'Singapore'), ('TH', 'Thailand'), ('TW', 'Taiwan'), ('US', 'Unit State')], default='TW', max_length=2)),
                ('province', models.CharField(max_length=50)),
                ('locality', models.CharField(max_length=50)),
                ('street', models.CharField(max_length=50)),
                ('detail', models.CharField(max_length=100)),
                ('floor', models.SmallIntegerField(blank=True, default=1, null=True)),
                ('description', models.CharField(blank=True, max_length=100)),
                ('user_type', models.ForeignKey(db_column='user_type', limit_choices_to=models.Q(models.Q(('app_label', 'user_management'), ('model', 'GenericUserProfile')), models.Q(('app_label', 'user_management'), ('model', 'GenericUserGroup')), _connector='OR'), on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'db_table': 'geo_location',
            },
        ),
        migrations.CreateModel(
            name='GenericUserGroupRelation',
            fields=[
                ('time_deleted', models.DateTimeField(blank=True, default=None, editable=False, null=True)),
                ('id', models.CharField(max_length=16, primary_key=True, serialize=False)),
                ('approved_by', models.ForeignKey(blank=True, db_column='approved_by', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approval_group', to='user_management.genericuserprofile')),
                ('group', models.ForeignKey(db_column='group', on_delete=django.db.models.deletion.CASCADE, related_name='profiles', to='user_management.genericusergroup')),
                ('profile', models.ForeignKey(db_column='profile', on_delete=django.db.models.deletion.CASCADE, related_name='groups', to='user_management.genericuserprofile')),
            ],
            options={
                'db_table': 'generic_user_group_relation',
            },
        ),
        migrations.CreateModel(
            name='GenericUserGroupClosure',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_deleted', models.DateTimeField(blank=True, default=None, editable=False, null=True)),
                ('depth', models.PositiveIntegerField(db_column='depth', default=0)),
                ('ancestor', models.ForeignKey(db_column='ancestor', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='descendants', to='user_management.genericusergroup')),
                ('descendant', models.ForeignKey(db_column='descendant', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ancestors', to='user_management.genericusergroup')),
            ],
            options={
                'db_table': 'generic_user_group_closure',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GenericUserAppliedRole',
            fields=[
                ('time_deleted', models.DateTimeField(blank=True, default=None, editable=False, null=True)),
                ('user_id', models.PositiveIntegerField(db_column='user_id')),
                ('expiry', models.DateTimeField(blank=True, null=True)),
                ('id', models.CharField(max_length=18, primary_key=True, serialize=False)),
                ('approved_by', models.ForeignKey(blank=True, db_column='approved_by', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approval_role', to='user_management.genericuserprofile')),
                ('role', models.ForeignKey(db_column='role', on_delete=django.db.models.deletion.CASCADE, related_name='users_applied', to='user_management.role')),
                ('user_type', models.ForeignKey(db_column='user_type', limit_choices_to=models.Q(models.Q(('app_label', 'user_management'), ('model', 'GenericUserProfile')), models.Q(('app_label', 'user_management'), ('model', 'GenericUserGroup')), _connector='OR'), on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'db_table': 'generic_user_applied_role',
            },
        ),
        migrations.CreateModel(
            name='EmailAddress',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_deleted', models.DateTimeField(blank=True, default=None, editable=False, null=True)),
                ('user_id', models.PositiveIntegerField(db_column='user_id')),
                ('addr', models.EmailField(default='notprovide@localhost', max_length=160)),
                ('user_type', models.ForeignKey(db_column='user_type', limit_choices_to=models.Q(models.Q(('app_label', 'user_management'), ('model', 'GenericUserProfile')), models.Q(('app_label', 'user_management'), ('model', 'GenericUserGroup')), _connector='OR'), on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'db_table': 'email_address',
            },
        ),
        migrations.AddConstraint(
            model_name='genericusergroupclosure',
            constraint=models.UniqueConstraint(fields=('ancestor', 'descendant'), name='unique_path'),
        ),
    ]
