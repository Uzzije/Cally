from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import apps.preferences.models.temporary_blocked_time


class Migration(migrations.Migration):
    dependencies = [
        ("preferences", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TemporaryBlockedTime",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "public_id",
                    models.CharField(
                        default=apps.preferences.models.temporary_blocked_time.generate_temporary_blocked_time_public_id,
                        max_length=32,
                        unique=True,
                    ),
                ),
                ("label", models.CharField(max_length=255)),
                ("start_time", models.DateTimeField()),
                ("end_time", models.DateTimeField()),
                ("timezone", models.CharField(max_length=64)),
                (
                    "source",
                    models.CharField(
                        choices=[("email_draft", "Email draft")],
                        default="email_draft",
                        max_length=32,
                    ),
                ),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="temporary_blocked_times",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "preferences_temporary_blocked_time",
                "ordering": ["start_time", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="temporaryblockedtime",
            index=models.Index(
                fields=["user", "expires_at"],
                name="pref_temp_block_user_exp_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="temporaryblockedtime",
            index=models.Index(
                fields=["user", "start_time"],
                name="pref_temp_block_user_start_idx",
            ),
        ),
    ]
