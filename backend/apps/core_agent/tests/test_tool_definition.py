from django.test import SimpleTestCase

from apps.core_agent.decorators import agent_tool
from apps.core_agent.models.tool_definition import ToolDefinition


def echo_tool(*, value: str) -> str:
    """Echo a value."""

    return value


@agent_tool(name="decorated_echo", description="Echoes a value through decorator metadata.")
def decorated_echo_tool(*, value: str, limit: int = 5) -> str:
    return f"{value}:{limit}"


class ToolDefinitionTests(SimpleTestCase):
    def test_invoke_calls_underlying_handler(self):
        tool_definition = ToolDefinition(
            name="echo_tool",
            description="Echoes a value.",
            handler=echo_tool,
        )

        result = tool_definition.invoke(value="hello")

        self.assertEqual(result, "hello")

    def test_from_callable_reads_decorator_metadata_and_infers_input_schema(self):
        tool_definition = ToolDefinition.from_callable(decorated_echo_tool)

        self.assertEqual(tool_definition.name, "decorated_echo")
        self.assertEqual(tool_definition.description, "Echoes a value through decorator metadata.")
        self.assertEqual(
            tool_definition.input_schema,
            {
                "type": "object",
                "properties": {
                    "value": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["value"],
                "additionalProperties": False,
            },
        )

    def test_from_callable_requires_decorator_metadata(self):
        with self.assertRaisesMessage(
            ValueError, "Tool callable must be decorated with @agent_tool"
        ):
            ToolDefinition.from_callable(echo_tool)

    def test_validate_args_accepts_valid_payload(self):
        tool_definition = ToolDefinition.from_callable(decorated_echo_tool)

        validated_args = tool_definition.validate_args({"value": "hello", "limit": 3})

        self.assertEqual(validated_args, {"value": "hello", "limit": 3})

    def test_validate_args_rejects_missing_required_fields(self):
        tool_definition = ToolDefinition.from_callable(decorated_echo_tool)

        with self.assertRaisesMessage(ValueError, "Missing required tool arguments: value"):
            tool_definition.validate_args({})

    def test_validate_args_rejects_unexpected_fields(self):
        tool_definition = ToolDefinition.from_callable(decorated_echo_tool)

        with self.assertRaisesMessage(ValueError, "Unexpected tool arguments: timezone"):
            tool_definition.validate_args({"value": "hello", "timezone": "UTC"})

    def test_validate_args_rejects_wrong_types(self):
        tool_definition = ToolDefinition.from_callable(decorated_echo_tool)

        with self.assertRaisesMessage(
            ValueError, "Invalid type for tool argument 'limit': expected integer"
        ):
            tool_definition.validate_args({"value": "hello", "limit": "3"})
