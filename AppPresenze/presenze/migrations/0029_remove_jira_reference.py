from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0028_jiraglobals_alter_utilitiesbar_icon_jiracredentials"),
    ]

    operations = [
        migrations.DeleteModel(
            name="JiraReference",
        ),
    ]
