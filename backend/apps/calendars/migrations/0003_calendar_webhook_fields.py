from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("calendars", "0002_calendar_timezone"),
    ]

    operations = [
        migrations.AddField(
            model_name="calendar",
            name="webhook_channel_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="calendar",
            name="webhook_channel_token",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="calendar",
            name="webhook_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="calendar",
            name="webhook_resource_id",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
