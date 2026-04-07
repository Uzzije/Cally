from django.db import migrations, models


def migrate_auto_to_confirm(apps, schema_editor):
    UserPreferences = apps.get_model("preferences", "UserPreferences")
    UserPreferences.objects.filter(execution_mode="auto").update(execution_mode="confirm")


class Migration(migrations.Migration):
    dependencies = [
        ("preferences", "0002_temporaryblockedtime"),
    ]

    operations = [
        migrations.RunPython(migrate_auto_to_confirm, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="userpreferences",
            name="execution_mode",
            field=models.CharField(
                choices=[
                    ("draft_only", "Draft only"),
                    ("confirm", "Confirm before executing"),
                ],
                default="draft_only",
                max_length=32,
            ),
        ),
    ]
