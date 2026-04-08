import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.calendars.models.calendar import Calendar
from apps.calendars.models.event import Event
from apps.chat.services.chat_execution_mode_profile_service import ChatExecutionModeProfileService
from apps.chat.services.chat_tool_registry_service import ChatToolRegistryService
from apps.preferences.models.temporary_blocked_time import TemporaryBlockedTime
from apps.preferences.models.user_preferences import ExecutionMode, UserPreferences

User = get_user_model()


class ChatToolRegistryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="chat-tool-registry@example.com",
            password="test-pass-123",
        )
        calendar = Calendar.objects.create(
            user=self.user,
            google_calendar_id="primary",
            name="Primary",
            is_primary=True,
            last_synced_at=timezone.now(),
        )
        Event.objects.create(
            calendar=calendar,
            google_event_id="event-1",
            title="Interview Loop with Nathan Turner",
            description="Final interview stage for backend role",
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=1),
            timezone="America/New_York",
            location="STLabs HQ",
            status="confirmed",
            attendees=[
                {"email": "recruiter@example.com", "display_name": "Recruiter"},
                {"email": "nathan@example.com", "display_name": "Nathan Turner"},
            ],
            organizer_email="recruiter@example.com",
        )

    def test_get_events_exposes_attendees_for_semantic_reasoning(self):
        profile = ChatExecutionModeProfileService().from_execution_mode(
            execution_mode=ExecutionMode.DRAFT_ONLY
        )
        tools = ChatToolRegistryService().build_tools(user=self.user, profile=profile)
        get_events = next(tool for tool in tools if tool.name == "get_events")
        now = timezone.now()

        payload = get_events.handler(
            start=(now - timedelta(days=1)).isoformat(),
            end=(now + timedelta(days=7)).isoformat(),
        )
        events = json.loads(payload)

        self.assertEqual(events[0]["attendees"][0]["email"], "recruiter@example.com")
        self.assertIn("Final interview stage", events[0]["description"])
        self.assertEqual(
            get_events.input_schema,
            {
                "type": "object",
                "properties": {
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                },
                "required": ["start", "end"],
                "additionalProperties": False,
            },
        )

    def test_get_preferences_exposes_saved_preferences_for_reasoning(self):
        UserPreferences.objects.create(
            user=self.user,
            execution_mode=ExecutionMode.CONFIRM,
            display_timezone="America/Los_Angeles",
            blocked_times=[
                {
                    "id": "focus-block",
                    "label": "Focus time",
                    "days": ["mon", "wed"],
                    "start": "09:00",
                    "end": "11:00",
                }
            ],
        )
        profile = ChatExecutionModeProfileService().from_execution_mode(
            execution_mode=ExecutionMode.CONFIRM
        )
        tools = ChatToolRegistryService().build_tools(user=self.user, profile=profile)
        get_preferences = next(tool for tool in tools if tool.name == "get_preferences")

        payload = get_preferences.handler()
        preferences = json.loads(payload)

        self.assertEqual(preferences["execution_mode"], ExecutionMode.CONFIRM)
        self.assertEqual(preferences["display_timezone"], "America/Los_Angeles")
        self.assertEqual(preferences["blocked_times"][0]["id"], "focus-block")

    def test_get_preferences_exposes_active_temporary_blocked_times(self):
        blocked_time = TemporaryBlockedTime.objects.create(
            user=self.user,
            label="Short-term hold",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        profile = ChatExecutionModeProfileService().from_execution_mode(
            execution_mode=ExecutionMode.CONFIRM
        )
        tools = ChatToolRegistryService().build_tools(user=self.user, profile=profile)
        get_preferences = next(tool for tool in tools if tool.name == "get_preferences")

        payload = json.loads(get_preferences.handler())

        self.assertEqual(len(payload["temp_blocked_times"]), 1)
        self.assertEqual(payload["temp_blocked_times"][0]["label"], "Short-term hold")
        self.assertEqual(payload["temp_blocked_times"][0]["id"], blocked_time.public_id)

    def test_get_temp_blocked_times_returns_requested_public_ids(self):
        first_block = TemporaryBlockedTime.objects.create(
            user=self.user,
            label="First hold",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        TemporaryBlockedTime.objects.create(
            user=self.user,
            label="Second hold",
            start_time=timezone.now() + timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1, minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        profile = ChatExecutionModeProfileService().from_execution_mode(
            execution_mode=ExecutionMode.CONFIRM
        )
        tools = ChatToolRegistryService().build_tools(user=self.user, profile=profile)
        get_temp_blocked_times = next(
            tool for tool in tools if tool.name == "get_temp_blocked_times"
        )

        payload = json.loads(get_temp_blocked_times.handler(public_ids=[first_block.public_id]))

        self.assertEqual(payload["requested_public_ids"], [first_block.public_id])
        self.assertEqual(len(payload["temp_blocked_times"]), 1)
        self.assertEqual(payload["temp_blocked_times"][0]["id"], first_block.public_id)

    def test_delete_temp_blocked_times_removes_requested_entries(self):
        first_block = TemporaryBlockedTime.objects.create(
            user=self.user,
            label="First hold",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        second_block = TemporaryBlockedTime.objects.create(
            user=self.user,
            label="Second hold",
            start_time=timezone.now() + timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1, minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        profile = ChatExecutionModeProfileService().from_execution_mode(
            execution_mode=ExecutionMode.CONFIRM
        )
        tools = ChatToolRegistryService().build_tools(user=self.user, profile=profile)
        delete_temp_blocked_times = next(
            tool for tool in tools if tool.name == "delete_temp_blocked_times"
        )

        payload = json.loads(
            delete_temp_blocked_times.handler(
                public_ids=[first_block.public_id, "missing-public-id"]
            )
        )

        self.assertEqual(payload["deleted_public_ids"], [first_block.public_id])
        self.assertEqual(payload["missing_public_ids"], ["missing-public-id"])
        self.assertEqual(
            [entry["id"] for entry in payload["remaining_temp_blocked_times"]],
            [second_block.public_id],
        )
        self.assertFalse(
            TemporaryBlockedTime.objects.filter(public_id=first_block.public_id).exists()
        )

    def test_build_tools_uses_decorator_defined_metadata(self):
        profile = ChatExecutionModeProfileService().from_execution_mode(
            execution_mode=ExecutionMode.DRAFT_ONLY
        )
        tools = ChatToolRegistryService().build_tools(user=self.user, profile=profile)
        search_events = next(tool for tool in tools if tool.name == "search_events")

        self.assertEqual(search_events.description, "Search calendar events by keyword.")
        self.assertEqual(search_events.input_schema["properties"]["query"]["type"], "string")
        self.assertEqual(search_events.input_schema["properties"]["limit"]["default"], 5)

    def test_build_tools_registers_email_draft_builder_tool(self):
        profile = ChatExecutionModeProfileService().from_execution_mode(
            execution_mode=ExecutionMode.DRAFT_ONLY
        )

        tools = ChatToolRegistryService().build_tools(user=self.user, profile=profile)

        self.assertIn("build_email_draft", [tool.name for tool in tools])
        build_email_draft = next(tool for tool in tools if tool.name == "build_email_draft")
        payload = json.loads(
            build_email_draft.handler(
                to=["joe@example.com"],
                cc=["manager@example.com"],
                suggested_times=[
                    {
                        "date": "2026-04-14",
                        "start": "14:00",
                        "end": "14:30",
                        "timezone": "America/New_York",
                    }
                ],
                draft_markdown=(
                    "Subject: Quick sync this week?\n\n"
                    "Hi Joe,\n\nCould we find 30 minutes this week?\n"
                ),
            )
        )

        self.assertEqual(payload["type"], "email_draft")
        self.assertEqual(payload["to"], ["joe@example.com"])
        self.assertEqual(payload["cc"], ["manager@example.com"])
        self.assertEqual(payload["status"], "draft")
        self.assertEqual(payload["subject"], "Quick sync this week?")
        self.assertEqual(payload["suggested_times"][0]["timezone"], "America/New_York")
        self.assertEqual(
            build_email_draft.input_schema["properties"]["suggested_times"]["type"],
            "array",
        )

    def test_build_email_draft_handler_wraps_single_suggested_time_object(self):
        profile = ChatExecutionModeProfileService().from_execution_mode(
            execution_mode=ExecutionMode.DRAFT_ONLY
        )

        tools = ChatToolRegistryService().build_tools(user=self.user, profile=profile)

        build_email_draft = next(tool for tool in tools if tool.name == "build_email_draft")
        payload = json.loads(
            build_email_draft.handler(
                to=["joe@example.com"],
                suggested_times={
                    "date": "2026-04-14",
                    "start": "14:00",
                    "end": "14:30",
                    "timezone": "America/New_York",
                },
                draft_markdown=(
                    "Subject: Quick sync this week?\n\n"
                    "Hi Joe,\n\nCould we find 30 minutes this week?\n"
                ),
            )
        )

        self.assertEqual(
            payload["suggested_times"],
            [
                {
                    "date": "2026-04-14",
                    "start": "14:00",
                    "end": "14:30",
                    "timezone": "America/New_York",
                }
            ],
        )

    def test_build_tools_registers_query_analytics_tool(self):
        profile = ChatExecutionModeProfileService().from_execution_mode(
            execution_mode=ExecutionMode.DRAFT_ONLY
        )

        tools = ChatToolRegistryService().build_tools(user=self.user, profile=profile)

        self.assertIn("query_analytics", [tool.name for tool in tools])
        query_analytics = next(tool for tool in tools if tool.name == "query_analytics")
        payload = json.loads(
            query_analytics.handler(query_type="meeting_hours_by_weekday_this_week")
        )

        self.assertIn("summary_text", payload)
        self.assertEqual(payload["chart_block"]["type"], "chart")
        self.assertEqual(payload["chart_block"]["chart_type"], "bar")

    def test_build_tools_does_not_register_calendar_event_creation_tool_for_confirm_mode(self):
        profile = ChatExecutionModeProfileService().from_execution_mode(
            execution_mode=ExecutionMode.CONFIRM
        )

        tools = ChatToolRegistryService().build_tools(user=self.user, profile=profile)

        self.assertNotIn("create_event", [tool.name for tool in tools])
