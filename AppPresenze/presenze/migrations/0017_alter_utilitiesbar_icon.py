from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0016_utilitiesbar"),
    ]

    operations = [
        migrations.AlterField(
            model_name="utilitiesbar",
            name="icon",
            field=models.CharField(
                choices=[
                    ("faConfluence", "Confluence"),
                    ("faJira", "Jira"),
                    ("faCircle", "Circle"),
                    ("faAmazon", "Amazon"),
                    ("faAws", "AWS"),
                    ("faDiscord", "Discord"),
                    ("faGithub", "GitHub"),
                    ("faGitlab", "GitLab"),
                    ("faLinkedin", "LinkedIn"),
                    ("faMicrosoft", "Microsoft"),
                    ("faNotion", "Notion"),
                    ("faUbuntu", "Ubuntu"),
                ],
                help_text="Nome icona Font Awesome consentita",
                max_length=100,
            ),
        ),
    ]
