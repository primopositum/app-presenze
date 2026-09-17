from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0026_jira_reference"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="jirareference",
            constraint=models.UniqueConstraint(Lower("name"), name="jira_reference_name_ci_unique"),
        ),
    ]
