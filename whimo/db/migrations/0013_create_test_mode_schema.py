from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0012_cover_whole_commodity_groups"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE SCHEMA IF NOT EXISTS test_mode;",
            reverse_sql="DROP SCHEMA IF EXISTS test_mode CASCADE;",
        ),
        migrations.RunSQL(
            # The "test_mode" alias shares its migration bookkeeping table with
            # "default" through search_path (test_mode,public) unless it has its
            # own: without this, Django finds public.django_migrations already
            # fully applied and skips every migration for "test_mode", leaving the
            # schema empty and silently falling through to public on every query.
            sql="CREATE TABLE IF NOT EXISTS test_mode.django_migrations "
            "(LIKE public.django_migrations INCLUDING ALL);",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
