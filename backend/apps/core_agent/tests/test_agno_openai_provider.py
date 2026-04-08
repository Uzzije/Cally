from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from apps.core_agent.decorators import agent_tool
from apps.core_agent.models.agent_loop_step_request import AgentLoopStepRequest
from apps.core_agent.models.tool_definition import ToolDefinition
from apps.core_agent.providers.agno_openai_provider import (
    ActionCardBlock,
    AgentLoopStructuredResponse,
    AgnoOpenAIProvider,
    ChartBlock,
    EmailDraftBlock,
)


class AgnoOpenAIProviderTests(SimpleTestCase):
    @override_settings(OPENAI_API_KEY="test-openai-key", AGNO_MODEL_ID="gpt-5-mini")
    @patch("apps.core_agent.providers.agno_openai_provider.OpenAIChat")
    @patch("apps.core_agent.providers.agno_openai_provider.Agent")
    def test_run_step_uses_native_structured_outputs_and_parses_typed_response(
        self,
        agent_class: Mock,
        openai_chat_class: Mock,
    ):
        agent_instance = Mock()
        agent_instance.run.return_value = SimpleNamespace(
            content=AgentLoopStructuredResponse(
                decision="call_tool",
                decision_reason="I need the event range before I can answer.",
                tool_name="get_events",
                tool_args_json='{"start":"2026-04-06T00:00:00+00:00","end":"2026-04-07T00:00:00+00:00"}',
                kind="",
                text="",
                content_blocks=[],
            ),
            tools=[],
        )
        agent_class.return_value = agent_instance
        provider = AgnoOpenAIProvider()

        result = provider.run_step(
            AgentLoopStepRequest(
                message="Tell me about the stock market.",
                system_prompt="Return structured loop steps.",
                session_state={
                    "workspace": {"mode": "confirm_before_execute"},
                    "execution_profile": {"mutation_mode": "action_card"},
                },
                session_id="session-123",
                user_id="user-123",
            )
        )

        openai_chat_class.assert_called_once_with(id="gpt-5-mini", api_key="test-openai-key")
        agent_class.assert_called_once()
        agent_kwargs = agent_class.call_args.kwargs
        self.assertEqual(agent_kwargs["response_model"], AgentLoopStructuredResponse)
        self.assertTrue(agent_kwargs["structured_outputs"])
        self.assertTrue(agent_kwargs["parse_response"])
        self.assertTrue(agent_kwargs["add_state_in_messages"])
        self.assertNotIn("tools", agent_kwargs)

        self.assertEqual(result.decision, "call_tool")
        self.assertEqual(result.decision_reason, "I need the event range before I can answer.")
        self.assertEqual(result.tool_name, "get_events")
        self.assertEqual(
            result.tool_args,
            {
                "start": "2026-04-06T00:00:00+00:00",
                "end": "2026-04-07T00:00:00+00:00",
            },
        )
        self.assertEqual(
            result.raw_content,
            '{"decision":"call_tool","decision_reason":"I need the event range before I can answer.","tool_name":"get_events","tool_args_json":"{\\"start\\":\\"2026-04-06T00:00:00+00:00\\",\\"end\\":\\"2026-04-07T00:00:00+00:00\\"}","kind":"","text":"","content_blocks":[]}',
        )

    def test_coerce_step_content_accepts_generic_pydantic_models(self):
        provider = AgnoOpenAIProvider(api_key="test-openai-key")

        payload = provider._coerce_step_content(
            AgentLoopStructuredResponse(
                decision="finish",
                decision_reason="The answer is already grounded by the current context.",
                tool_name="",
                tool_args_json="{}",
                kind="clarification",
                text="Which week would you like me to look at?",
                content_blocks=[],
            )
        )

        self.assertEqual(
            payload.model_dump(),
            AgentLoopStructuredResponse(
                decision="finish",
                decision_reason="The answer is already grounded by the current context.",
                tool_name="",
                tool_args_json="{}",
                kind="clarification",
                text="Which week would you like me to look at?",
                content_blocks=[],
            ).model_dump(),
        )

    def test_coerce_step_content_preserves_content_blocks(self):
        provider = AgnoOpenAIProvider(api_key="test-openai-key")

        payload = provider._coerce_step_content(
            {
                "decision": "finish",
                "decision_reason": "The proposal is grounded by the current request details.",
                "tool_name": "",
                "tool_args_json": "{}",
                "kind": "answer",
                "text": "I found a review-only option.",
                "content_blocks": [
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
                                "payload": {
                                    "start_time": "2026-04-07T08:00:00-04:00",
                                    "end_time": "2026-04-07T08:30:00-04:00",
                                    "timezone": "America/New_York",
                                    "attendees": ["joe@example.com"],
                                    "title": "Meeting with Joe",
                                },
                                "status": "pending",
                            }
                        ],
                    }
                ],
            }
        )

        block = cast(ActionCardBlock, payload.content_blocks[0])
        self.assertEqual(block.type, "action_card")
        action_payload = block.actions[0].payload
        if action_payload is None:
            self.fail("Expected action payload to be present")
        self.assertEqual(action_payload.timezone, "America/New_York")

    def test_coerce_step_content_preserves_email_draft_blocks(self):
        provider = AgnoOpenAIProvider(api_key="test-openai-key")

        payload = provider._coerce_step_content(
            {
                "decision": "finish",
                "decision_reason": "The draft content is already grounded by the request.",
                "tool_name": "",
                "tool_args_json": "{}",
                "kind": "answer",
                "text": "Here is a draft you can review.",
                "content_blocks": [
                    {
                        "type": "email_draft",
                        "to": ["joe@example.com"],
                        "cc": [],
                        "subject": "Quick sync this week?",
                        "body": "Hi Joe\n\nCould we find 30 minutes this week?\n",
                        "suggested_times": [
                            {
                                "date": "2026-04-14",
                                "start": "14:00",
                                "end": "14:30",
                                "timezone": "America/New_York",
                            }
                        ],
                        "status": "draft",
                        "status_detail": "Draft only. Not sent.",
                    }
                ],
            }
        )

        block = cast(EmailDraftBlock, payload.content_blocks[0])
        self.assertEqual(block.type, "email_draft")
        self.assertEqual(block.subject, "Quick sync this week?")
        self.assertEqual(block.suggested_times[0].timezone, "America/New_York")

    def test_coerce_step_content_preserves_chart_blocks(self):
        provider = AgnoOpenAIProvider(api_key="test-openai-key")

        payload = provider._coerce_step_content(
            {
                "decision": "finish",
                "decision_reason": "The analytics result already grounds the answer.",
                "tool_name": "",
                "tool_args_json": "{}",
                "kind": "answer",
                "text": "You have 6.0 hours of meetings this week so far.",
                "content_blocks": [
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
                    }
                ],
            }
        )

        block = cast(ChartBlock, payload.content_blocks[0])
        self.assertEqual(block.type, "chart")
        self.assertEqual(block.chart_type, "bar")
        self.assertEqual(block.data[0].label, "Mon")

    def test_coerce_step_content_defaults_missing_finish_kind_to_answer(self):
        provider = AgnoOpenAIProvider(api_key="test-openai-key")

        payload = provider._coerce_step_content(
            {
                "decision": "finish",
                "decision_reason": "The current session state already contains the answer.",
                "tool_name": "",
                "tool_args_json": "{}",
                "text": "Your execution mode is draft_only.",
                "content_blocks": [],
            }
        )

        self.assertEqual(payload.kind, "answer")

    def test_build_step_message_includes_explicit_history_scratchpad_and_tool_schema_sections(self):
        provider = AgnoOpenAIProvider(api_key="test-openai-key")

        @agent_tool(name="get_events", description="Get calendar events in an ISO datetime range.")
        def get_events(*, start: str, end: str) -> str:
            return "[]"

        request = AgentLoopStepRequest(
            message="What does tomorrow look like?",
            system_prompt="Loop system prompt.",
            history=[
                {"role": "user", "content": "What does tomorrow look like?"},
            ],
            tools=[ToolDefinition.from_callable(get_events)],
            session_state={
                "workspace": {"mode": "confirm_before_execute"},
                "execution_profile": {
                    "mutation_mode": "action_card",
                    "grounded_mutation_finish_instruction": (
                        "When a calendar change is sufficiently grounded, finish with one "
                        "approval-gated action_card instead of asking for optional extras."
                    ),
                },
            },
            iteration=2,
            max_iterations=4,
        )

        message = provider._build_step_message(request)

        self.assertIn("## Loop protocol", message)
        self.assertIn("## Response shape rules", message)
        self.assertIn("## Scratchpad", message)
        self.assertIn("## Runtime context snapshot", message)
        self.assertIn("## Time context", message)
        self.assertIn("## Available tools", message)
        self.assertIn("## Completed tool calls", message)
        self.assertIn('"input_schema"', message)
        self.assertIn('"start"', message)
        self.assertIn('"current_date"', message)
        self.assertIn('"current_weekday"', message)
        self.assertIn("decision_reason", message)
        self.assertIn('"decision":"call_tool"', message)
        self.assertIn('"decision":"finish"', message)
        self.assertIn("Keep it brief, operational, and safe to log.", message)
        self.assertIn('"kind":"answer"', message)
        self.assertIn('"tool_args_json":"{}"', message)
        self.assertIn(
            "call `build_email_draft` with `to`, optional `cc`, one `draft_markdown` string",
            message,
        )
        self.assertIn("structured `suggested_times` entries", message)
        self.assertIn("call `query_analytics`", message)
        self.assertIn("callable tool for draft-only scheduling email previews", message)
        self.assertIn("callable tool for supported read-only analytics", message)
        self.assertIn("Provide the draft as one markdown string in `draft_markdown`", message)
        self.assertIn("next user-facing result supported by the schema", message)
        self.assertIn("Base each decision on the current runtime snapshot", message)
        self.assertIn("`create_event` is an action type for `action_card` content", message)
        self.assertIn("do not return `call_tool` with `tool_name`=`create_event`", message)
        self.assertIn(
            "call `build_email_draft` once the recipient and purpose are grounded", message
        )
        self.assertIn(
            "Do not call `build_email_draft` again in the same turn once a valid draft result already exists.",
            message,
        )
        self.assertIn(
            "If you are on the final iteration and the completed tool calls already contain a valid draft or chart result, you must `finish`.",
            message,
        )
        self.assertIn(
            "finish with one approval-gated action_card instead of asking for optional extras",
            message,
        )
        self.assertIn("should include a `payload` object", message)
        self.assertNotIn("## Conversation history snapshot", message)

    def test_parse_tool_args_json_handles_valid_json(self):
        provider = AgnoOpenAIProvider()
        result = provider._parse_tool_args_json('{"query": "meetings this week"}')
        self.assertEqual(result, {"query": "meetings this week"})

    def test_parse_tool_args_json_returns_empty_dict_for_empty_string(self):
        provider = AgnoOpenAIProvider()
        result = provider._parse_tool_args_json("")
        self.assertEqual(result, {})

    def test_parse_tool_args_json_handles_invalid_escape_sequences(self):
        provider = AgnoOpenAIProvider()
        malformed = r'{"body": "Hello\nWorld \Users\example"}'
        result = provider._parse_tool_args_json(malformed)
        self.assertIsInstance(result, dict)
        self.assertIn("body", result)

    def test_loop_response_schema_marks_all_top_level_properties_required(self):
        schema = AgentLoopStructuredResponse.model_json_schema()

        self.assertEqual(
            set(schema["required"]),
            {
                "decision",
                "decision_reason",
                "tool_name",
                "tool_args_json",
                "kind",
                "text",
                "content_blocks",
            },
        )
        self.assertEqual(
            set(schema["properties"].keys()),
            {
                "decision",
                "decision_reason",
                "tool_name",
                "tool_args_json",
                "kind",
                "text",
                "content_blocks",
            },
        )
