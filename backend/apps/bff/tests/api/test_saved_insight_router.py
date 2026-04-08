import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.analytics.models.saved_insight import SavedInsight
from apps.analytics.services.saved_insight_service import SavedInsightValidationError
from apps.chat.models.chat_session import ChatSession
from apps.chat.models.message import Message, MessageRole

User = get_user_model()


class SavedInsightRouterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="saved-insight-api@example.com",
            password="test-pass-123",
        )
        self.other_user = User.objects.create_user(
            username="ignored-2",
            email="saved-insight-api-other@example.com",
            password="test-pass-123",
        )
        self.session = ChatSession.objects.create(user=self.user, title="Analytics")
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

    def test_list_saved_insights_requires_authentication(self):
        response = self.client.get("/api/v1/analytics/saved-insights", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 401)

    def test_list_saved_insights_returns_only_authenticated_users_cards(self):
        self.client.force_login(self.user)
        own_insight = SavedInsight.objects.create(
            user=self.user,
            title="Own insight",
            summary_text="Own summary",
            query_definition={"query_type": "meeting_hours_by_weekday_this_week"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Own insight",
                "data": [{"label": "Mon", "value": 1}],
            },
        )
        SavedInsight.objects.create(
            user=self.other_user,
            title="Other insight",
            summary_text="Other summary",
            query_definition={"query_type": "meeting_hours_by_weekday_this_week"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Other insight",
                "data": [{"label": "Mon", "value": 1}],
            },
        )

        response = self.client.get("/api/v1/analytics/saved-insights", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["id"], own_insight.public_id)
        self.assertEqual(payload["items"][0]["title"], "Own insight")
        self.assertEqual(payload["policy"]["max_saved_insights"], 1)
        self.assertEqual(payload["policy"]["current_count"], 1)
        self.assertTrue(payload["policy"]["replaces_on_save"])
        self.assertIn("upgrade", payload["policy"]["upgrade_message"].lower())

    def test_create_saved_insight_persists_chart_from_chat_message(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/analytics/saved-insights",
            data={
                "assistant_message_id": self.assistant_message.id,
                "block_index": 1,
            },
            content_type="application/json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["title"], "Meeting hours this week")
        self.assertEqual(payload["chart_payload"]["title"], "Meeting hours this week")
        self.assertEqual(SavedInsight.objects.filter(user=self.user).count(), 1)
        self.assertFalse(payload["replaced_existing"])

    def test_create_saved_insight_replaces_existing_user_insight_when_limit_is_reached(self):
        self.client.force_login(self.user)
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

        response = self.client.post(
            "/api/v1/analytics/saved-insights",
            data={
                "assistant_message_id": self.assistant_message.id,
                "block_index": 1,
            },
            content_type="application/json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["replaced_existing"])
        self.assertEqual(payload["id"], existing.public_id)
        self.assertEqual(SavedInsight.objects.filter(user=self.user).count(), 1)

    def test_create_saved_insight_returns_validation_error_for_unsupported_save(self):
        self.client.force_login(self.user)

        with patch(
            "apps.bff.api.routers.saved_insight_router.SavedInsightService.save_from_message",
            side_effect=SavedInsightValidationError("This analytics result cannot be saved."),
        ):
            response = self.client.post(
                "/api/v1/analytics/saved-insights",
                data={
                    "assistant_message_id": self.assistant_message.id,
                    "block_index": 1,
                },
                content_type="application/json",
                HTTP_HOST="localhost",
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "This analytics result cannot be saved.")

    def test_refresh_saved_insight_returns_not_found_for_foreign_card(self):
        self.client.force_login(self.user)
        foreign_insight = SavedInsight.objects.create(
            user=self.other_user,
            title="Other insight",
            summary_text="Other summary",
            query_definition={"query_type": "meeting_hours_by_weekday_this_week"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Other insight",
                "data": [{"label": "Mon", "value": 1}],
            },
        )

        response = self.client.post(
            f"/api/v1/analytics/saved-insights/{foreign_insight.public_id}/refresh",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_saved_insight_removes_only_authenticated_users_card(self):
        self.client.force_login(self.user)
        own_insight = SavedInsight.objects.create(
            user=self.user,
            title="Own insight",
            summary_text="Own summary",
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
            summary_text="Other summary",
            query_definition={"query_type": "meeting_hours_by_weekday_this_week"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Other insight",
                "data": [{"label": "Mon", "value": 1}],
            },
        )

        response = self.client.delete(
            f"/api/v1/analytics/saved-insights/{own_insight.public_id}",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(SavedInsight.objects.filter(pk=own_insight.pk).exists())
        self.assertTrue(SavedInsight.objects.filter(pk=other_insight.pk).exists())

    def test_refresh_saved_insight_returns_user_safe_error_when_recompute_fails(self):
        self.client.force_login(self.user)
        insight = SavedInsight.objects.create(
            user=self.user,
            title="Own insight",
            summary_text="Own summary",
            query_definition={"query_type": "meeting_hours_by_weekday_this_week"},
            chart_payload={
                "type": "chart",
                "chart_type": "bar",
                "title": "Own insight",
                "data": [{"label": "Mon", "value": 1}],
            },
        )

        with patch(
            "apps.bff.api.routers.saved_insight_router.SavedInsightService.refresh",
            side_effect=SavedInsightValidationError("Unable to refresh this saved insight."),
        ):
            response = self.client.post(
                f"/api/v1/analytics/saved-insights/{insight.public_id}/refresh",
                HTTP_HOST="localhost",
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Unable to refresh this saved insight.")
