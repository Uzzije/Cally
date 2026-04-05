from django.test import SimpleTestCase

from apps.core_agent.models.tool_definition import ToolDefinition


def echo_tool(*, value: str) -> str:
    """Echo a value."""

    return value


class ToolDefinitionTests(SimpleTestCase):
    def test_invoke_calls_underlying_handler(self):
        tool_definition = ToolDefinition(
            name="echo_tool",
            description="Echoes a value.",
            handler=echo_tool,
        )

        result = tool_definition.invoke(value="hello")

        self.assertEqual(result, "hello")

