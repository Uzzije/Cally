from datetime import timedelta
from typing import Any, cast

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.calendars.models.calendar import Calendar
from apps.calendars.models.event import Event
from apps.chat.models.chat_session import ChatSession
from apps.chat.models.chat_turn import ChatTurnResultKind, ChatTurnStatus
from apps.chat.services.chat_assistant_turn_service import ChatAssistantTurnService
from apps.chat.services.chat_message_service import ChatMessageService
from apps.chat.services.chat_prompt_builder import ChatPromptBuilder
from apps.chat.services.chat_turn_execution_service import ChatTurnExecutionService
from apps.chat.services.chat_turn_service import ChatTurnService
from apps.core_agent.models.agent_loop_step_request import AgentLoopStepRequest
from apps.core_agent.models.agent_loop_step_result import AgentLoopStepResult
from apps.core_agent.models.tool_execution_result import ToolExecutionResult
from apps.core_agent.services.game_loop_service import GameLoopExceededMaxIterationsError
from apps.core_agent.providers.agent_provider import AgentProvider

User = get_user_model()


class FakeAgentProvider(AgentProvider):
    def __init__(self, step_results: list[AgentLoopStepResult]) -> None:
        self.step_results = list(step_results)
        self.call_count = 0

    def run_step(self, request: AgentLoopStepRequest) -> AgentLoopStepResult:
        self.call_count += 1
        return self.step_results.pop(0)


class ChatTurnExecutionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="chat-turn-execution@example.com",
            password="test-pass-123",
        )
        self.session = ChatSession.objects.create(user=self.user)
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
            title="Design Review",
            description="Weekly sync",
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=1),
            timezone="America/New_York",
            organizer_email="owner@example.com",
        )
        self.message_service = ChatMessageService()
        self.turn_service = ChatTurnService()

    def _assistant_message(self, turn) -> Any:
        self.assertIsNotNone(turn.assistant_message)
        return turn.assistant_message

    def test_process_turn_persists_assistant_message_for_in_scope_question(self):
        user_message = self.message_service.create_user_message(
            self.session,
            content="What does tomorrow look like?",
        )
        turn = self.turn_service.create_turn(session=self.session, user_message=user_message)
        provider = FakeAgentProvider(
            [
                AgentLoopStepResult(
                    decision="finish",
                    kind="answer",
                    text="You have a design review tomorrow.",
                )
            ]
        )
        service = ChatTurnExecutionService(
            assistant_turn_service=ChatAssistantTurnService(provider=provider)
        )

        result_turn = service.process_turn(turn=turn)

        result_turn.refresh_from_db()
        assistant_message = self._assistant_message(result_turn)
        self.assertEqual(result_turn.status, ChatTurnStatus.COMPLETED)
        self.assertEqual(
            assistant_message.content_blocks[0]["text"],
            "You have a design review tomorrow.",
        )
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(result_turn.trace_events[-1]["type"], "turn_completed")

    def test_process_turn_uses_provider_for_model_driven_fallback_requests(self):
        user_message = self.message_service.create_user_message(
            self.session,
            content="Tell me about the US stock market",
        )
        turn = self.turn_service.create_turn(session=self.session, user_message=user_message)
        provider = FakeAgentProvider(
            [
                AgentLoopStepResult(
                    decision="finish",
                    kind="fallback",
                    text=(
                        "I only handle calendar and workspace questions in this environment. "
                        "You can ask things like “What does tomorrow look like?”"
                    ),
                )
            ],
        )
        service = ChatTurnExecutionService(
            assistant_turn_service=ChatAssistantTurnService(provider=provider)
        )

        result_turn = service.process_turn(turn=turn)

        result_turn.refresh_from_db()
        assistant_message = self._assistant_message(result_turn)
        self.assertEqual(result_turn.status, ChatTurnStatus.COMPLETED)
        self.assertIn(
            "calendar and workspace",
            assistant_message.content_blocks[0]["text"].lower(),
        )
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(result_turn.result_kind, "fallback")

    def test_process_turn_persists_action_card_for_supported_scheduling_prompt_via_provider(self):
        user_message = self.message_service.create_user_message(
            self.session,
            content="Schedule a 30 minute meeting with Joe tomorrow",
        )
        turn = self.turn_service.create_turn(session=self.session, user_message=user_message)
        provider = FakeAgentProvider(
            [
                AgentLoopStepResult(
                    decision="finish",
                    kind="answer",
                    text="I found a review-only option.",
                    content_blocks=[
                        {
                            "type": "action_card",
                            "actions": [
                                {
                                    "id": "proposal-1",
                                    "action_type": "create_event",
                                    "summary": "Meeting with Joe",
                                    "details": {
                                        "date": "Tue Apr 7",
                                        "time": "8:00 AM-8:30 AM",
                                        "attendees": ["Joe"],
                                    },
                                    "status": "pending",
                                }
                            ],
                        }
                    ],
                )
            ],
        )
        service = ChatTurnExecutionService(
            assistant_turn_service=ChatAssistantTurnService(provider=provider)
        )

        result_turn = service.process_turn(turn=turn)

        result_turn.refresh_from_db()
        assistant_message = self._assistant_message(result_turn)
        self.assertEqual(result_turn.status, ChatTurnStatus.COMPLETED)
        self.assertEqual(assistant_message.content_blocks[0]["type"], "action_card")
        self.assertEqual(
            assistant_message.content_blocks[0]["actions"][0]["summary"],
            "Meeting with Joe",
        )
        self.assertEqual(provider.call_count, 1)

    def test_process_turn_persists_email_draft_for_supported_scheduling_email_prompt(self):
        user_message = self.message_service.create_user_message(
            self.session,
            content="Draft an email to Joe asking for 30 minutes tomorrow afternoon",
        )
        turn = self.turn_service.create_turn(session=self.session, user_message=user_message)
        provider = FakeAgentProvider(
            [
                AgentLoopStepResult(
                    decision="finish",
                    kind="answer",
                    text="Here's a draft you can review.",
                    content_blocks=[
                        {
                            "type": "email_draft",
                            "to": ["joe@example.com"],
                            "cc": [],
                            "subject": "30-minute sync tomorrow afternoon",
                            "body": "Hi Joe,\n\nWould you be available for 30 minutes tomorrow afternoon?\n",
                            "status": "draft",
                            "status_detail": "Draft only. Not sent.",
                        }
                    ],
                )
            ],
        )
        service = ChatTurnExecutionService(
            assistant_turn_service=ChatAssistantTurnService(provider=provider)
        )

        result_turn = service.process_turn(turn=turn)

        result_turn.refresh_from_db()
        assistant_message = self._assistant_message(result_turn)
        self.assertEqual(result_turn.status, ChatTurnStatus.COMPLETED)
        self.assertEqual(assistant_message.content_blocks[0]["type"], "email_draft")
        self.assertEqual(
            assistant_message.content_blocks[0]["subject"],
            "30-minute sync tomorrow afternoon",
        )
        self.assertEqual(provider.call_count, 1)

    def test_process_turn_persists_chart_block_for_supported_analytics_prompt(self):
        user_message = self.message_service.create_user_message(
            self.session,
            content="What are my meeting hours this week?",
        )
        turn = self.turn_service.create_turn(session=self.session, user_message=user_message)
        provider = FakeAgentProvider(
            [
                AgentLoopStepResult(
                    decision="finish",
                    kind="answer",
                    text="You have 6.0 hours of meetings this week so far.",
                    content_blocks=[
                        {
                            "type": "chart",
                            "chart_type": "bar",
                            "title": "Meeting hours this week",
                            "data": [
                                {"label": "Mon", "value": 4},
                                {"label": "Tue", "value": 2},
                            ],
                            "save_enabled": True,
                        }
                    ],
                )
            ],
        )
        service = ChatTurnExecutionService(
            assistant_turn_service=ChatAssistantTurnService(provider=provider)
        )

        result_turn = service.process_turn(turn=turn)

        result_turn.refresh_from_db()
        assistant_message = self._assistant_message(result_turn)
        self.assertEqual(result_turn.status, ChatTurnStatus.COMPLETED)
        self.assertEqual(assistant_message.content_blocks[0]["type"], "chart")
        self.assertEqual(assistant_message.content_blocks[0]["title"], "Meeting hours this week")

    def test_process_turn_records_current_prompt_version_in_eval_snapshot(self):
        user_message = self.message_service.create_user_message(
            self.session,
            content="What does tomorrow look like?",
        )
        turn = self.turn_service.create_turn(session=self.session, user_message=user_message)
        provider = FakeAgentProvider(
            [
                AgentLoopStepResult(
                    decision="finish",
                    kind="answer",
                    text="You have a design review tomorrow.",
                )
            ]
        )
        service = ChatTurnExecutionService(
            assistant_turn_service=ChatAssistantTurnService(provider=provider)
        )

        result_turn = service.process_turn(turn=turn)

        result_turn.refresh_from_db()
        self.assertEqual(
            result_turn.eval_snapshot["prompt_version"], ChatPromptBuilder.prompt_version
        )

    def test_process_turn_records_loop_tool_usage_in_eval_snapshot(self):
        user_message = self.message_service.create_user_message(
            self.session,
            content="What are my preferences?",
        )
        turn = self.turn_service.create_turn(session=self.session, user_message=user_message)
        provider = FakeAgentProvider(
            [
                AgentLoopStepResult(
                    decision="call_tool",
                    tool_name="get_preferences",
                ),
                AgentLoopStepResult(
                    decision="finish",
                    kind="answer",
                    text="Your execution mode is draft_only.",
                ),
            ]
        )
        service = ChatTurnExecutionService(
            assistant_turn_service=ChatAssistantTurnService(provider=provider)
        )

        result_turn = service.process_turn(turn=turn)

        result_turn.refresh_from_db()
        self.assertEqual(result_turn.eval_snapshot["used_tools"], ["get_preferences"])
        self.assertEqual(result_turn.eval_snapshot["assistant_kind"], "answer")
        self.assertEqual(result_turn.eval_snapshot["provider_name"], "openai")
        self.assertEqual(
            result_turn.eval_snapshot["tool_outputs"],
            ['{"execution_mode": "draft_only", "blocked_times": [], "temp_blocked_times": []}'],
        )

    def test_process_turn_records_loop_events_in_trace_and_eval_snapshot(self):
        user_message = self.message_service.create_user_message(
            self.session,
            content="What are my preferences?",
        )
        turn = self.turn_service.create_turn(session=self.session, user_message=user_message)
        provider = FakeAgentProvider(
            [
                AgentLoopStepResult(
                    decision="call_tool",
                    tool_name="get_preferences",
                ),
                AgentLoopStepResult(
                    decision="finish",
                    kind="answer",
                    text="Your execution mode is draft_only.",
                ),
            ]
        )
        service = ChatTurnExecutionService(
            assistant_turn_service=ChatAssistantTurnService(provider=provider)
        )

        result_turn = service.process_turn(turn=turn)

        result_turn.refresh_from_db()
        event_types = [event["type"] for event in result_turn.trace_events]
        self.assertIn("provider_step_completed", event_types)
        self.assertIn("tool_executed", event_types)
        provider_step = next(
            event
            for event in result_turn.trace_events
            if event["type"] == "provider_step_completed"
        )
        self.assertEqual(provider_step["data"]["provider_name"], "openai")
        self.assertTrue(provider_step["data"]["provider_model"])
        self.assertEqual(result_turn.eval_snapshot["loop_events"][0]["type"], "loop_step_completed")

    def test_fail_turn_preserves_existing_provider_loop_metadata(self):
        user_message = self.message_service.create_user_message(
            self.session,
            content="Schedule something for me",
        )
        turn = self.turn_service.create_turn(session=self.session, user_message=user_message)
        turn.provider_metadata = {
            "raw_content": '{"decision":"call_tool"}',
            "loop_events": [
                {
                    "type": "loop_step_completed",
                    "iteration": 1,
                    "decision": "call_tool",
                    "tool_name": "get_events",
                    "tool_args": {"start": "2026-04-06T00:00:00-05:00"},
                    "kind": "",
                    "text": "",
                    "raw_content": '{"decision":"call_tool"}',
                }
            ],
            "tool_calls": [
                {
                    "tool_name": "get_events",
                    "tool_args": {"start": "2026-04-06T00:00:00-05:00"},
                    "result": "[]",
                }
            ],
        }
        turn.save(update_fields=["provider_metadata"])
        service = ChatTurnExecutionService()

        failed_turn = service._fail_turn(
            turn=turn,
            user_prompt="Schedule something for me",
            failure_reason="provider_error",
            exc=RuntimeError("Game loop exceeded max iterations without finishing."),
        )

        failed_turn.refresh_from_db()
        self.assertEqual(failed_turn.status, ChatTurnStatus.FAILED)
        self.assertEqual(failed_turn.result_kind, ChatTurnResultKind.ERROR)
        self.assertEqual(failed_turn.eval_snapshot["loop_events"][0]["tool_name"], "get_events")
        self.assertEqual(failed_turn.eval_snapshot["used_tools"], ["get_events"])

    def test_process_turn_persists_loop_metadata_when_game_loop_exceeds_iterations(self):
        class FailingAssistantTurnService:
            provider = type("Provider", (), {"model_id": "gpt-5-mini"})()

            def generate_response(self, *, session, user_prompt):
                raise GameLoopExceededMaxIterationsError(
                    tool_calls=[
                        ToolExecutionResult(
                            tool_name="get_events",
                            tool_args={"start": "2026-04-06T00:00:00-05:00"},
                            result="[]",
                        )
                    ],
                    loop_events=[
                        {
                            "type": "loop_step_completed",
                            "iteration": 1,
                            "decision": "call_tool",
                            "tool_name": "get_events",
                            "tool_args": {"start": "2026-04-06T00:00:00-05:00"},
                            "kind": "",
                            "text": "",
                            "raw_content": '{"decision":"call_tool"}',
                        }
                    ],
                )

            capability_service = ChatAssistantTurnService().capability_service
            tool_registry_service = ChatAssistantTurnService().tool_registry_service

        user_message = self.message_service.create_user_message(
            self.session,
            content="Schedule something for me",
        )
        turn = self.turn_service.create_turn(session=self.session, user_message=user_message)
        service = ChatTurnExecutionService(
            assistant_turn_service=cast(Any, FailingAssistantTurnService())
        )

        failed_turn = service.process_turn(turn=turn)

        failed_turn.refresh_from_db()
        event_types = [event["type"] for event in failed_turn.trace_events]
        self.assertIn("provider_step_completed", event_types)
        self.assertEqual(failed_turn.eval_snapshot["used_tools"], ["get_events"])
        self.assertEqual(failed_turn.eval_snapshot["loop_events"][0]["type"], "loop_step_completed")
