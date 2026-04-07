from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.analytics.models.saved_insight import SavedInsight

User = get_user_model()


class SavedInsightModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="saved-insight@example.com",
            password="test-pass-123",
        )
        self.other_user = User.objects.create_user(
            username="ignored-2",
            email="saved-insight-other@example.com",
            password="test-pass-123",
        )

    def test_persists_narrow_saved_insight_contract(self):
        insight = SavedInsight.objects.create(
            user=self.user,
            title="Meeting hours this week",
            summary_text="You have 6.0 hours of meetings this week so far.",
            query_definition={"query_type": "meeting_hours_by_weekday_this_week"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Meeting hours this week",
                "subtitle": "Based on synced events grouped by weekday.",
                "data": [
                    {"label": "Mon", "value": 4},
                    {"label": "Tue", "value": 2},
                ],
            },
        )

        self.assertEqual(insight.user, self.user)
        self.assertEqual(
            insight.query_definition, {"query_type": "meeting_hours_by_weekday_this_week"}
        )
        self.assertEqual(insight.chart_payload["type"], "chart")
        self.assertIsNotNone(insight.last_refreshed_at)
        self.assertEqual(len(insight.public_id), 32)

    def test_rejects_invalid_query_definition_shapes(self):
        invalid_definitions = [
            None,
            {},
            {"query_type": ""},
            {"query_type": "arbitrary_sql"},
            {"query_type": "meeting_hours_by_weekday_this_week", "sql": "select * from event"},
        ]

        for query_definition in invalid_definitions:
            with self.subTest(query_definition=query_definition):
                insight = SavedInsight(
                    user=self.user,
                    title="Broken insight",
                    summary_text="This should not save.",
                    query_definition=query_definition,
                    chart_payload={
                        "type": "chart",
                        "chart_type": "bar",
                        "title": "Broken insight",
                        "data": [{"label": "Mon", "value": 0}],
                    },
                )

                with self.assertRaises(ValidationError):
                    insight.full_clean()

    def test_orders_saved_insights_by_last_refreshed_at_with_user_ownership(self):
        older = SavedInsight.objects.create(
            user=self.user,
            title="Older insight",
            summary_text="Older summary",
            query_definition={"query_type": "meeting_hours_by_weekday_this_week"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Older insight",
                "data": [{"label": "Mon", "value": 1}],
            },
            last_refreshed_at=timezone.now() - timedelta(days=1),
        )
        newer = SavedInsight.objects.create(
            user=self.user,
            title="Newer insight",
            summary_text="Newer summary",
            query_definition={"query_type": "busiest_day_last_14_days"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Newer insight",
                "data": [{"label": "Apr 1", "value": 3}],
            },
            last_refreshed_at=timezone.now(),
        )
        SavedInsight.objects.create(
            user=self.other_user,
            title="Other user insight",
            summary_text="Should not appear",
            query_definition={"query_type": "meeting_hours_by_weekday_this_week"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Other user insight",
                "data": [{"label": "Mon", "value": 5}],
            },
            last_refreshed_at=timezone.now() + timedelta(minutes=5),
        )

        insights = list(SavedInsight.objects.filter(user=self.user))

        self.assertEqual([insight.id for insight in insights], [newer.id, older.id])
