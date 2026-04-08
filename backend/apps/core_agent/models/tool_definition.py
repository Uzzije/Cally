from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from types import NoneType, UnionType
from typing import Any, Callable, Union, get_args, get_origin, get_type_hints

from apps.core_agent.decorators import AGENT_TOOL_METADATA_ATTR, AgentToolMetadata


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    handler: Callable[..., str]
    input_schema: dict[str, Any] = field(default_factory=dict)

    def invoke(self, **kwargs) -> str:
        return self.handler(**kwargs)

    def validate_args(self, args: dict[str, Any]) -> dict[str, Any]:
        if not self.input_schema:
            return dict(args)

        properties = self.input_schema.get("properties", {})
        required = set(self.input_schema.get("required", []))
        additional_properties = self.input_schema.get("additionalProperties", True)

        missing_fields = sorted(field_name for field_name in required if field_name not in args)
        if missing_fields:
            missing_display = ", ".join(missing_fields)
            raise ValueError(f"Missing required tool arguments: {missing_display}")

        if additional_properties is False:
            unexpected_fields = sorted(
                field_name for field_name in args if field_name not in properties
            )
            if unexpected_fields:
                unexpected_display = ", ".join(unexpected_fields)
                raise ValueError(f"Unexpected tool arguments: {unexpected_display}")

        validated_args: dict[str, Any] = {}
        for field_name, value in args.items():
            field_schema = properties.get(field_name, {})
            coerced = self._coerce_value(value=value, field_schema=field_schema)
            if not self._matches_json_type(value=coerced, field_schema=field_schema):
                expected_type = field_schema.get("type", "string")
                raise ValueError(
                    f"Invalid type for tool argument '{field_name}': expected {expected_type}"
                )
            validated_args[field_name] = coerced

        return validated_args

    @classmethod
    def from_callable(cls, handler: Callable[..., str]) -> "ToolDefinition":
        metadata = getattr(handler, AGENT_TOOL_METADATA_ATTR, None)
        if metadata is None or not isinstance(metadata, AgentToolMetadata):
            raise ValueError(
                "Tool callable must be decorated with @agent_tool before registration."
            )

        return cls(
            name=metadata.name,
            description=metadata.description,
            handler=handler,
            input_schema=cls._build_input_schema(handler),
        )

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    @staticmethod
    def _build_input_schema(handler: Callable[..., str]) -> dict[str, Any]:
        signature = inspect.signature(handler)
        type_hints = get_type_hints(handler)
        properties: dict[str, Any] = {}
        required: list[str] = []

        for parameter in signature.parameters.values():
            if parameter.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
                continue

            annotation = type_hints.get(parameter.name, parameter.annotation)
            json_type, nullable = ToolDefinition._map_annotation_to_json_type(annotation)
            schema: dict[str, Any] = {"type": json_type}
            if nullable:
                schema["nullable"] = True
            if parameter.default is not inspect.Signature.empty:
                schema["default"] = parameter.default
            else:
                required.append(parameter.name)
            properties[parameter.name] = schema

        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

    @staticmethod
    def _map_annotation_to_json_type(annotation: Any) -> tuple[str, bool]:
        if annotation is inspect.Signature.empty:
            return "string", False

        origin = get_origin(annotation)
        if origin in {UnionType, Union}:
            non_none_args = [arg for arg in get_args(annotation) if arg is not NoneType]
            if len(non_none_args) == 1:
                json_type, _ = ToolDefinition._map_annotation_to_json_type(non_none_args[0])
                return json_type, True

        if annotation is str:
            return "string", False
        if annotation is int:
            return "integer", False
        if annotation is float:
            return "number", False
        if annotation is bool:
            return "boolean", False
        if annotation is dict or origin is dict:
            return "object", False
        if annotation is list or origin is list:
            return "array", False

        return "string", False

    @staticmethod
    def _coerce_value(*, value: Any, field_schema: dict[str, Any]) -> Any:
        """Attempt to coerce string values to the expected type.

        LLMs sometimes return numeric values as strings inside tool_args_json
        (e.g. "10" instead of 10). This converts them before strict type checking
        so the tool receives the correct Python type.
        """
        if not isinstance(value, str):
            if field_schema.get("type") == "array" and not isinstance(value, list):
                if isinstance(value, tuple | set):
                    return list(value)
                return [value]
            return value

        expected_type = field_schema.get("type")
        if expected_type in {"array", "object"}:
            stripped = value.strip()
            if stripped.startswith("[") or stripped.startswith("{"):
                try:
                    decoded = json.loads(stripped)
                    if expected_type == "array" and not isinstance(decoded, list):
                        return [decoded]
                    return decoded
                except (json.JSONDecodeError, TypeError):
                    return value
            if expected_type == "array":
                return [value]
        if expected_type == "integer":
            try:
                return int(value)
            except (ValueError, TypeError):
                return value
        if expected_type == "number":
            try:
                return float(value)
            except (ValueError, TypeError):
                return value

        return value

    @staticmethod
    def _matches_json_type(*, value: Any, field_schema: dict[str, Any]) -> bool:
        if value is None:
            return bool(field_schema.get("nullable"))

        expected_type = field_schema.get("type")
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "number":
            return (isinstance(value, int) or isinstance(value, float)) and not isinstance(
                value, bool
            )
        if expected_type == "boolean":
            return isinstance(value, bool)
        if expected_type == "object":
            return isinstance(value, dict)
        if expected_type == "array":
            return isinstance(value, list)

        return True
