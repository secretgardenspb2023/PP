"""Bind the User model to the client's ``user_info.users`` table (ТЗ Этап 3.1/3.2).

State: User becomes ``managed = False`` (table is owned by the client); add the
read-only ``DictRole`` model for ``user_info.dict_roles``.

Database: ``user_info.users`` lacks the columns Django auth needs, so we add
``is_active`` / ``is_staff`` / ``is_superuser`` / ``last_login`` and seed the admin
flags from ``role_id`` (1=Администратор → super+staff, 2=Модератор → staff). The
ALTER is guarded by ``to_regclass`` so it is a no-op on a database without the
client schema (e.g. the ephemeral pytest test DB). The obsolete Django-managed
``accounts_user`` table (+ its M2M tables) is dropped.
"""
from django.db import migrations, models

ADD_AUTH_COLUMNS = r"""
DO $$
BEGIN
  IF to_regclass('user_info.users') IS NOT NULL THEN
    ALTER TABLE "user_info"."users"
      ADD COLUMN IF NOT EXISTS is_active    boolean     NOT NULL DEFAULT true,
      ADD COLUMN IF NOT EXISTS is_staff     boolean     NOT NULL DEFAULT false,
      ADD COLUMN IF NOT EXISTS is_superuser boolean     NOT NULL DEFAULT false,
      ADD COLUMN IF NOT EXISTS last_login   timestamptz NULL;
    UPDATE "user_info"."users" SET is_staff = true, is_superuser = true WHERE role_id = 1;
    UPDATE "user_info"."users" SET is_staff = true                      WHERE role_id = 2;
  END IF;
END $$;
-- Obsolete Django-managed user tables (the model now maps to user_info.users).
DROP TABLE IF EXISTS accounts_user_groups CASCADE;
DROP TABLE IF EXISTS accounts_user_user_permissions CASCADE;
DROP TABLE IF EXISTS accounts_user CASCADE;
"""

DROP_AUTH_COLUMNS = r"""
DO $$
BEGIN
  IF to_regclass('user_info.users') IS NOT NULL THEN
    ALTER TABLE "user_info"."users"
      DROP COLUMN IF EXISTS is_active,
      DROP COLUMN IF EXISTS is_staff,
      DROP COLUMN IF EXISTS is_superuser,
      DROP COLUMN IF EXISTS last_login;
  END IF;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_social_id_user_social_provider_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DictRole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role_name', models.CharField(max_length=50)),
            ],
            options={
                'verbose_name': 'роль',
                'verbose_name_plural': 'роли',
                'db_table': 'user_info"."dict_roles',
                'managed': False,
            },
        ),
        migrations.AlterModelOptions(
            name='user',
            options={'managed': False, 'verbose_name': 'пользователь', 'verbose_name_plural': 'пользователи'},
        ),
        # State-only (model is unmanaged → no DB rename); keeps migration state in
        # sync so ``makemigrations --check`` stays clean. Must come AFTER the
        # managed=False switch above.
        migrations.AlterModelTable(name='user', table='user_info"."users'),
        migrations.RunSQL(sql=ADD_AUTH_COLUMNS, reverse_sql=DROP_AUTH_COLUMNS),
    ]
