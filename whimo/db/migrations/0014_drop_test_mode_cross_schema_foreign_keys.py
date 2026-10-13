from django.db import migrations


def drop_cross_schema_foreign_keys(apps, schema_editor):
    # test_mode.balances/transactions/... reference public.commodities/users/
    # harvest_seasons across schemas. That FK is enforced at the application layer
    # (every id used there is read from an existing public row first); keeping the
    # physical constraint only means Postgres refuses to TRUNCATE public.commodities
    # in a plain (non-CASCADE) flush, because test_mode's copies also reference it -
    # breaking test teardown for every other test in the suite, not just test_mode's.
    if schema_editor.connection.alias != "test_mode":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT conrelid::regclass::text, conname
            FROM pg_constraint
            WHERE contype = 'f'
              AND connamespace = 'test_mode'::regnamespace
              AND connamespace <> (SELECT relnamespace FROM pg_class WHERE oid = confrelid)
            """
        )
        for table_name, constraint_name in cursor.fetchall():
            cursor.execute(f'ALTER TABLE {table_name} DROP CONSTRAINT "{constraint_name}"')


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0013_create_test_mode_schema"),
    ]

    operations = [
        migrations.RunPython(
            drop_cross_schema_foreign_keys,
            migrations.RunPython.noop,
            hints={"always_migrate": True},
        ),
    ]
