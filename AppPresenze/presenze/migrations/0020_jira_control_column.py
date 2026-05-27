from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("presenze", "0019_alter_trasferta_validation_level"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'ALTER TABLE IF EXISTS "JiraGlobals" '
                'ADD COLUMN IF NOT EXISTS "JiraControl" boolean NOT NULL DEFAULT true;'
            ),
            reverse_sql=(
                'ALTER TABLE IF EXISTS "JiraGlobals" '
                'DROP COLUMN IF EXISTS "JiraControl";'
            ),
        ),
    ]
