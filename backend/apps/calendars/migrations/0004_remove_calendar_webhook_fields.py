from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("calendars", "0003_calendar_webhook_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="calendar",
            name="webhook_channel_id",
        ),
        migrations.RemoveField(
            model_name="calendar",
            name="webhook_channel_token",
        ),
        migrations.RemoveField(
            model_name="calendar",
            name="webhook_expires_at",
        ),
        migrations.RemoveField(
            model_name="calendar",
            name="webhook_resource_id",
        ),
    ]
