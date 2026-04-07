from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("calendars", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="calendar",
            name="timezone",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
