-- Pre-create the PostgreSQL schemas used by the client's existing database so
-- that schema-qualified Django models (db_table = '"schema"."table"') can be
-- migrated locally without manual steps. Runs once on an empty data volume.
--
-- Final schema routing (e.g. Django service tables in django_internal) is wired
-- when the real `plant.plants` dump arrives; until then Django defaults to public.

CREATE SCHEMA IF NOT EXISTS plant_info;
CREATE SCHEMA IF NOT EXISTS plant;
CREATE SCHEMA IF NOT EXISTS user_info;
CREATE SCHEMA IF NOT EXISTS django_internal;
