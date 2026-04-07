from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.analytics.models.saved_insight import SavedInsight
from apps.analytics.services.analytics_query_service import AnalyticsQueryService
from apps.chat.models.message import Message, MessageRole
from apps.core.types import AuthenticatedUser

logger = logging.getLogger(__name__)


class SavedInsightServiceError(ValueError):
    pass


class SavedInsightNotFoundError(SavedInsightServiceError):
    pass


class SavedInsightValidationError(SavedInsightServiceError):
    pass


@dataclass(frozen=True)
class SaveableAnalyticsArtifact:
    title: str
    summary_text: str
    query_definition: dict
    chart_payload: dict


@dataclass(frozen=True)
class SavedInsightPolicy:
    max_saved_insights: int
    current_count: int
    replaces_on_save: bool
    upgrade_message: str


@dataclass(frozen=True)
class SavedInsightSaveResult:
    insight: SavedInsight
    replaced_existing: bool


class SavedInsightService:
    max_saved_insights_per_user = 1
    upgrade_message = "Free plan saves one insight at a time. Upgrade to save more insights and organize them better."

    def __init__(
        self,
        *,
        analytics_query_service: AnalyticsQueryService | None = None,
    ) -> None:
        self.analytics_query_service = analytics_query_service or AnalyticsQueryService()

    def list_for_user(self, user: AuthenticatedUser):
        return SavedInsight.objects.filter(user=user)

    def get_policy_for_user(self, user: AuthenticatedUser) -> SavedInsightPolicy:
        current_count = SavedInsight.objects.filter(user=user).count()
        return SavedInsightPolicy(
            max_saved_insights=self.max_saved_insights_per_user,
            current_count=current_count,
            replaces_on_save=True,
            upgrade_message=self.upgrade_message,
        )

    @transaction.atomic
    def save_from_message(
        self,
        *,
        user: AuthenticatedUser,
        assistant_message_id: int,
        block_index: int,
    ) -> SavedInsightSaveResult:
        message = (
            Message.objects.select_related("session")
            .filter(
                id=assistant_message_id,
                role=MessageRole.ASSISTANT,
                session__user=user,
            )
            .first()
        )
        if message is None:
            raise SavedInsightNotFoundError("Saved insight source message was not found.")

        artifact = self._extract_saveable_artifact(message=message, block_index=block_index)
        insight = (
            SavedInsight.objects.filter(user=user).order_by("-last_refreshed_at", "-id").first()
        )
        replaced_existing = insight is not None

        if insight is None:
            insight = SavedInsight.objects.create(
                user=user,
                title=artifact.title,
                summary_text=artifact.summary_text,
                query_definition=artifact.query_definition,
                chart_payload=artifact.chart_payload,
            )
        else:
            insight.title = artifact.title
            insight.summary_text = artifact.summary_text
            insight.query_definition = artifact.query_definition
            insight.chart_payload = artifact.chart_payload
            insight.last_refreshed_at = timezone.now()
            insight.save(
                update_fields=[
                    "title",
                    "summary_text",
                    "query_definition",
                    "chart_payload",
                    "last_refreshed_at",
                    "updated_at",
                ]
            )
        logger.info(
            "analytics.saved_insight.saved user_id=%s message_id=%s insight_id=%s query_type=%s replaced_existing=%s",
            user.id,
            message.id,
            insight.public_id,
            artifact.query_definition["query_type"],
            replaced_existing,
        )
        return SavedInsightSaveResult(
            insight=insight,
            replaced_existing=replaced_existing,
        )

    @transaction.atomic
    def refresh(self, *, user: AuthenticatedUser, public_id: str) -> SavedInsight:
        insight = SavedInsight.objects.filter(user=user, public_id=public_id).first()
        if insight is None:
            raise SavedInsightNotFoundError("Saved insight was not found.")

        query_type = insight.query_definition["query_type"]
        result = self.analytics_query_service.run(user=user, query_type=query_type)
        insight.title = str(result.chart_block.get("title", "")).strip() or insight.title
        insight.summary_text = result.summary_text.strip()
        insight.chart_payload = self._normalize_chart_payload(result.chart_block)
        insight.last_refreshed_at = timezone.now()
        insight.save(
            update_fields=[
                "title",
                "summary_text",
                "chart_payload",
                "last_refreshed_at",
                "updated_at",
            ]
        )
        logger.info(
            "analytics.saved_insight.refreshed user_id=%s insight_id=%s query_type=%s",
            user.id,
            insight.public_id,
            query_type,
        )
        return insight

    @transaction.atomic
    def delete(self, *, user: AuthenticatedUser, public_id: str) -> bool:
        insight = SavedInsight.objects.filter(user=user, public_id=public_id).first()
        if insight is None:
            logger.info(
                "analytics.saved_insight.delete_skipped user_id=%s insight_id=%s",
                user.id,
                public_id,
            )
            return False

        insight.delete()
        logger.info(
            "analytics.saved_insight.deleted user_id=%s insight_id=%s",
            user.id,
            public_id,
        )
        return True

    def _extract_saveable_artifact(
        self,
        *,
        message: Message,
        block_index: int,
    ) -> SaveableAnalyticsArtifact:
        block = self._get_chart_block(message=message, block_index=block_index)
        tool_payload = self._find_matching_tool_payload(message=message, chart_block=block)
        if tool_payload is None:
            raise SavedInsightValidationError("This analytics result cannot be saved.")

        summary_text = tool_payload.get("summary_text")
        chart_block = tool_payload.get("chart_block")
        tool_query_type = self._extract_query_type(message=message, chart_block=chart_block)
        if not isinstance(summary_text, str) or not summary_text.strip() or tool_query_type is None:
            raise SavedInsightValidationError("This analytics result cannot be saved.")

        return SaveableAnalyticsArtifact(
            title=str(block.get("title", "")).strip(),
            summary_text=summary_text.strip(),
            query_definition={"query_type": tool_query_type},
            chart_payload=self._normalize_chart_payload(block),
        )

    def _get_chart_block(self, *, message: Message, block_index: int) -> dict:
        try:
            block = message.content_blocks[block_index]
        except IndexError as exc:
            raise SavedInsightValidationError("This analytics result cannot be saved.") from exc

        if (
            not isinstance(block, dict)
            or block.get("type") != "chart"
            or block.get("save_enabled") is not True
        ):
            raise SavedInsightValidationError("This analytics result cannot be saved.")

        return block

    def _find_matching_tool_payload(self, *, message: Message, chart_block: dict) -> dict | None:
        for tool_call in reversed(message.tool_calls or []):
            if tool_call.get("tool_name") != "query_analytics" or not tool_call.get("result"):
                continue

            try:
                payload = json.loads(tool_call["result"])
            except (TypeError, json.JSONDecodeError):
                continue

            if not isinstance(payload, dict) or not isinstance(payload.get("chart_block"), dict):
                continue

            payload_chart = self._normalize_chart_payload(payload["chart_block"])
            if payload_chart == self._normalize_chart_payload(chart_block):
                return payload

        return None

    def _extract_query_type(self, *, message: Message, chart_block: dict | None) -> str | None:
        if not isinstance(chart_block, dict):
            return None

        normalized_chart_block = self._normalize_chart_payload(chart_block)
        for tool_call in reversed(message.tool_calls or []):
            if tool_call.get("tool_name") != "query_analytics":
                continue

            tool_args = tool_call.get("tool_args")
            if not isinstance(tool_args, dict):
                continue

            try:
                payload = json.loads(tool_call.get("result") or "")
            except (TypeError, json.JSONDecodeError):
                continue

            if not isinstance(payload, dict) or not isinstance(payload.get("chart_block"), dict):
                continue

            if self._normalize_chart_payload(payload["chart_block"]) == normalized_chart_block:
                query_type = tool_args.get("query_type")
                if isinstance(query_type, str) and query_type.strip():
                    return query_type

        return None

    def _normalize_chart_payload(self, chart_block: dict) -> dict:
        normalized = dict(chart_block)
        normalized.pop("save_enabled", None)
        return normalized
