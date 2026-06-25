"""Доработка по согласованию с заказчицей (ТЗ §5, схема меняется через миграции):

1. Новая колонка ``plant.plants.has_author_description`` — флаг «авторское описание»
   (блокирует будущую массовую перезапись карточки шаблоном).
2. Перенос словаря цветов ``dict_colors`` из схемы ``plant`` в ``plant_info``
   (к остальным справочникам). FK из link-таблиц следуют за таблицей по OID.

Таблицы managed=False, поэтому всё руками через RunSQL. SQL идемпотентный.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_dictcarelevel_dictdesigner_dictdesignuse_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE plant.plants "
                "ADD COLUMN IF NOT EXISTS has_author_description boolean NOT NULL DEFAULT false;",
            reverse_sql="ALTER TABLE plant.plants DROP COLUMN IF EXISTS has_author_description;",
        ),
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'plant' AND table_name = 'dict_colors'
                ) THEN
                    ALTER TABLE plant.dict_colors SET SCHEMA plant_info;
                END IF;
            END $$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'plant_info' AND table_name = 'dict_colors'
                ) THEN
                    ALTER TABLE plant_info.dict_colors SET SCHEMA plant;
                END IF;
            END $$;
            """,
        ),
    ]
