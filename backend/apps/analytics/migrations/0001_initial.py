from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

import apps.analytics.models.saved_insight


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedInsight",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.CharField(default=apps.analytics.models.saved_insight.generate_saved_insight_public_id, max_length=32, unique=True)),
                ("title", models.CharField(max_length=255)),
                ("summary_text", models.TextField()),
                ("query_definition", models.JSONField()),
                ("chart_payload", models.JSONField()),
                ("last_refreshed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_insights", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "analytics_saved_insight",
                "ordering": ["-last_refreshed_at", "-id"],
                "indexes": [
                    models.Index(fields=["user", "last_refreshed_at"], name="analytics_si_usr_ref_idx"),
                ],
            },
        ),
    ]
