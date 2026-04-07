from django.test import SimpleTestCase

from apps.core_agent.models.agent_loop_step_request import AgentLoopStepRequest
from apps.core_agent.models.agent_loop_step_result import AgentLoopStepResult
from apps.core_agent.models.agent_turn_request import AgentTurnRequest
from apps.core_agent.models.tool_definition import ToolDefinition
from apps.core_agent.providers.agent_provider import AgentProvider
from apps.core_agent.services.game_loop_service import (
    GameLoopExceededMaxIterationsError,
    GameLoopService,
)


class FakeLoopProvider(AgentProvider):
    def __init__(self, step_results: list[AgentLoopStepResult]) -> None:
        self.step_results = list(step_results)
        self.step_requests: list[AgentLoopStepRequest] = []

    def run_step(self, request: AgentLoopStepRequest) -> AgentLoopStepResult:
        self.step_requests.append(request)
        return self.step_results.pop(0)


class GameLoopServiceTests(SimpleTestCase):
    def test_run_executes_tool_then_finishes(self):
        provider = FakeLoopProvider(
            [
                AgentLoopStepResult(
                    decision="call_tool",
                    tool_name="get_preferences",
                ),
                AgentLoopStepResult(
                    decision="finish",
                    kind="answer",
                    text="Your execution mode is confirm.",
                ),
            ]
        )
        service = GameLoopService(provider=provider)

        result = service.run(
            AgentTurnRequest(
                message="What are my preferences?",
                system_prompt="Run the loop.",
                tools=[
                    ToolDefinition(
                        name="get_preferences",
                        description="Get saved preferences.",
                        handler=lambda: '{"execution_mode": "confirm"}',
                    )
                ],
                session_state={"workspace": {"mode": "confirm_before_execute"}},
            )
        )

        self.assertEqual(result.kind, "answer")
        self.assertEqual(result.text, "Your execution mode is confirm.")
        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].tool_name, "get_preferences")
        self.assertEqual(result.tool_calls[0].result, '{"execution_mode": "confirm"}')
        self.assertEqual(result.loop_events[0]["type"], "loop_step_completed")
        self.assertEqual(result.loop_events[1]["type"], "tool_executed")
        self.assertEqual(result.loop_events[-1]["decision"], "finish")
        self.assertEqual(provider.step_requests[0].iteration, 1)
        self.assertEqual(provider.step_requests[1].iteration, 2)
        self.assertEqual(provider.step_requests[1].tool_calls[0].tool_name, "get_preferences")

    def test_run_rejects_unknown_tools(self):
        provider = FakeLoopProvider(
            [
                AgentLoopStepResult(
                    decision="call_tool",
                    tool_name="missing_tool",
                )
            ]
        )
        service = GameLoopService(provider=provider)

        with self.assertRaisesMessage(
            ValueError, "Unknown tool requested by provider: missing_tool"
        ):
            service.run(
                AgentTurnRequest(
                    message="What are my preferences?",
                    system_prompt="Run the loop.",
                )
            )

    def test_run_fails_fast_when_loop_never_finishes(self):
        provider = FakeLoopProvider(
            [
                AgentLoopStepResult(
                    decision="call_tool",
                    tool_name="get_preferences",
                )
            ]
        )
        service = GameLoopService(provider=provider, max_iterations=1)

        with self.assertRaisesMessage(
            GameLoopExceededMaxIterationsError,
            "Game loop exceeded max iterations without finishing.",
        ) as raised:
            service.run(
                AgentTurnRequest(
                    message="What are my preferences?",
                    system_prompt="Run the loop.",
                    tools=[
                        ToolDefinition(
                            name="get_preferences",
                            description="Get saved preferences.",
                            handler=lambda: '{"execution_mode": "confirm"}',
                        )
                    ],
                )
            )
        self.assertEqual(raised.exception.loop_events[0]["decision"], "call_tool")
        self.assertEqual(raised.exception.tool_calls[0].tool_name, "get_preferences")

    def test_run_rejects_tool_args_that_fail_schema_validation(self):
        provider = FakeLoopProvider(
            [
                AgentLoopStepResult(
                    decision="call_tool",
                    tool_name="get_preferences",
                    tool_args={"timezone": "UTC"},
                )
            ]
        )
        service = GameLoopService(provider=provider)

        with self.assertRaisesMessage(
            ValueError,
            "Invalid arguments for tool 'get_preferences': Unexpected tool arguments: timezone",
        ):
            service.run(
                AgentTurnRequest(
                    message="What are my preferences?",
                    system_prompt="Run the loop.",
                    tools=[
                        ToolDefinition(
                            name="get_preferences",
                            description="Get saved preferences.",
                            handler=lambda: '{"execution_mode": "confirm"}',
                            input_schema={
                                "type": "object",
                                "properties": {},
                                "required": [],
                                "additionalProperties": False,
                            },
                        )
                    ],
                )
            )
