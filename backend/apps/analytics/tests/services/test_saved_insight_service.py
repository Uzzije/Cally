import json
from datetime import timedelta
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.analytics.models.saved_insight import SavedInsight
from apps.analytics.services.analytics_query_service import AnalyticsQueryResult
from apps.analytics.services.saved_insight_service import (
    SavedInsightNotFoundError,
    SavedInsightService,
    SavedInsightValidationError,
)
from apps.chat.models.chat_session import ChatSession
from apps.chat.models.message import Message, MessageRole

User = get_user_model()


@dataclass
class StubAnalyticsQueryService:
    result: AnalyticsQueryResult
    last_call: tuple[object, str] | None = None

    def run(self, *, user, query_type: str) -> AnalyticsQueryResult:
        self.last_call = (user, query_type)
        return self.result


class SavedInsightServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="saved-insight-service@example.com",
            password="test-pass-123",
        )
        self.other_user = User.objects.create_user(
            username="ignored-2",
            email="saved-insight-service-other@example.com",
            password="test-pass-123",
        )
        self.session = ChatSession.objects.create(user=self.user, title="Analytics")
        self.other_session = ChatSession.objects.create(
            user=self.other_user, title="Other analytics"
        )
        self.assistant_message = Message.objects.create(
            session=self.session,
            role=MessageRole.ASSISTANT,
            content_blocks=[
                {"type": "text", "text": "You have 6.0 hours of meetings this week so far."},
                {
                    "type": "chart",
                    "chart_type": "bar",
                    "title": "Meeting hours this week",
                    "subtitle": "Based on synced events grouped by weekday.",
                    "data": [
                        {"label": "Mon", "value": 4},
                        {"label": "Tue", "value": 2},
                    ],
                    "save_enabled": True,
                },
            ],
            tool_calls=[
                {
                    "tool_name": "query_analytics",
                    "tool_args": {"query_type": "meeting_hours_by_weekday_this_week"},
                    "result": json.dumps(
                        {
                            "summary_text": "You have 6.0 hours of meetings this week so far.",
                            "chart_block": {
                                "type": "chart",
                                "chart_type": "bar",
                                "title": "Meeting hours this week",
                                "subtitle": "Based on synced events grouped by weekday.",
                                "data": [
                                    {"label": "Mon", "value": 4},
                                    {"label": "Tue", "value": 2},
                                ],
                                "save_enabled": True,
                            },
                        }
                    ),
                }
            ],
        )
        self.service = SavedInsightService()

    def test_save_from_message_persists_supported_chart_artifact(self):
        result = self.service.save_from_message(
            user=self.user,
            assistant_message_id=self.assistant_message.id,
            block_index=1,
        )
        insight = result.insight

        self.assertEqual(insight.user, self.user)
        self.assertEqual(insight.title, "Meeting hours this week")
        self.assertEqual(insight.summary_text, "You have 6.0 hours of meetings this week so far.")
        self.assertEqual(
            insight.query_definition,
            {"query_type": "meeting_hours_by_weekday_this_week"},
        )
        self.assertNotIn("save_enabled", insight.chart_payload)
        self.assertEqual(SavedInsight.objects.filter(user=self.user).count(), 1)
        self.assertFalse(result.replaced_existing)

    def test_save_from_message_replaces_existing_saved_insight_for_user(self):
        existing = SavedInsight.objects.create(
            user=self.user,
            title="Old insight",
            summary_text="Old summary",
            query_definition={"query_type": "busiest_day_last_14_days"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Old insight",
                "data": [{"label": "Apr 1", "value": 3}],
            },
        )

        result = self.service.save_from_message(
            user=self.user,
            assistant_message_id=self.assistant_message.id,
            block_index=1,
        )
        insight = result.insight

        self.assertEqual(insight.pk, existing.pk)
        self.assertEqual(insight.title, "Meeting hours this week")
        self.assertEqual(SavedInsight.objects.filter(user=self.user).count(), 1)
        self.assertTrue(result.replaced_existing)
        self.assertEqual(
            SavedInsight.objects.get(user=self.user).query_definition,
            {"query_type": "meeting_hours_by_weekday_this_week"},
        )

    def test_save_from_message_rejects_non_saveable_or_unsupported_blocks(self):
        non_saveable_message = Message.objects.create(
            session=self.session,
            role=MessageRole.ASSISTANT,
            content_blocks=[
                {
                    "type": "chart",
                    "chart_type": "bar",
                    "title": "Unsupported chart",
                    "data": [{"label": "Mon", "value": 1}],
                }
            ],
            tool_calls=[],
        )

        with self.assertRaises(SavedInsightValidationError):
            self.service.save_from_message(
                user=self.user,
                assistant_message_id=non_saveable_message.id,
                block_index=0,
            )

    def test_refresh_recomputes_saved_insight_from_approved_query_definition(self):
        insight = SavedInsight.objects.create(
            user=self.user,
            title="Meeting hours this week",
            summary_text="Old summary",
            query_definition={"query_type": "meeting_hours_by_weekday_this_week"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Meeting hours this week",
                "data": [{"label": "Mon", "value": 1}],
            },
            last_refreshed_at=timezone.now() - timedelta(days=1),
        )
        query_service = StubAnalyticsQueryService(
            result=AnalyticsQueryResult(
                summary_text="Updated summary",
                chart_block={
                    "type": "chart",
                    "chart_type": "bar",
                    "title": "Meeting hours this week",
                    "subtitle": "Freshly recomputed.",
                    "data": [{"label": "Mon", "value": 5}],
                    "save_enabled": True,
                },
            )
        )
        service = SavedInsightService(analytics_query_service=query_service)

        refreshed = service.refresh(user=self.user, public_id=insight.public_id)

        self.assertEqual(query_service.last_call, (self.user, "meeting_hours_by_weekday_this_week"))
        self.assertEqual(refreshed.summary_text, "Updated summary")
        self.assertEqual(refreshed.chart_payload["data"][0]["value"], 5)
        self.assertNotIn("save_enabled", refreshed.chart_payload)
        self.assertGreater(refreshed.last_refreshed_at, insight.last_refreshed_at)

    def test_delete_only_removes_targeted_user_owned_saved_insight(self):
        own_insight = SavedInsight.objects.create(
            user=self.user,
            title="Own insight",
            summary_text="Delete me",
            query_definition={"query_type": "meeting_hours_by_weekday_this_week"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Own insight",
                "data": [{"label": "Mon", "value": 1}],
            },
        )
        other_insight = SavedInsight.objects.create(
            user=self.other_user,
            title="Other insight",
            summary_text="Keep me",
            query_definition={"query_type": "meeting_hours_by_weekday_this_week"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Other insight",
                "data": [{"label": "Mon", "value": 1}],
            },
        )

        deleted = self.service.delete(user=self.user, public_id=own_insight.public_id)

        self.assertTrue(deleted)
        self.assertFalse(SavedInsight.objects.filter(pk=own_insight.pk).exists())
        self.assertTrue(SavedInsight.objects.filter(pk=other_insight.pk).exists())

    def test_delete_returns_false_for_missing_or_foreign_saved_insight(self):
        foreign_insight = SavedInsight.objects.create(
            user=self.other_user,
            title="Foreign insight",
            summary_text="Not yours",
            query_definition={"query_type": "meeting_hours_by_weekday_this_week"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Foreign insight",
                "data": [{"label": "Mon", "value": 1}],
            },
        )

        self.assertFalse(self.service.delete(user=self.user, public_id="missing-id"))
        self.assertFalse(self.service.delete(user=self.user, public_id=foreign_insight.public_id))
        self.assertTrue(SavedInsight.objects.filter(pk=foreign_insight.pk).exists())

    def test_save_from_message_rejects_other_users_assistant_message(self):
        foreign_message = Message.objects.create(
            session=self.other_session,
            role=MessageRole.ASSISTANT,
            content_blocks=self.assistant_message.content_blocks,
            tool_calls=self.assistant_message.tool_calls,
        )

        with self.assertRaises(SavedInsightNotFoundError):
            self.service.save_from_message(
                user=self.user,
                assistant_message_id=foreign_message.id,
                block_index=1,
            )
