from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("preferences", "0003_remove_auto_execution_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="userpreferences",
            name="display_timezone",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
