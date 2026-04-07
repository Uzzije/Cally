import json

from django.contrib import admin
from django.utils.html import format_html

from apps.chat.models.chat_session import ChatSession
from apps.chat.models.chat_turn import ChatTurn
from apps.chat.models.message import Message


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "updated_at")
    list_filter = ("updated_at",)
    search_fields = ("title", "user__email")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("session__title", "session__user__email")
    readonly_fields = ("tool_calls",)


@admin.register(ChatTurn)
class ChatTurnAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "status", "result_kind", "scope_decision", "created_at")
    list_filter = ("status", "result_kind", "scope_decision", "created_at", "session__user")
    search_fields = ("session__title", "session__user__email", "correlation_id")
    readonly_fields = (
        "trace_events",
        "eval_snapshot",
        "provider_metadata",
        "user_message_link",
        "assistant_message_link",
        "created_at",
        "started_at",
        "completed_at",
        "failed_at",
    )

    def user_message_link(self, obj: ChatTurn) -> str:
        return self._format_message_link(obj.user_message)

    user_message_link.short_description = "User message"

    def assistant_message_link(self, obj: ChatTurn) -> str:
        if not obj.assistant_message:
            return "-"
        return self._format_message_link(obj.assistant_message)

    assistant_message_link.short_description = "Assistant message"

    def _format_message_link(self, message: Message) -> str:
        return format_html(
            '<a href="/admin/chat/message/{}/change/">Message #{}</a>',
            message.id,
            message.id,
        )

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (
            "session",
            "user_message",
            "assistant_message",
            "status",
            "result_kind",
            "scope_decision",
            "failure_reason",
            "correlation_id",
        )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in {"trace_events", "eval_snapshot", "provider_metadata"} and formfield:
            formfield.initial = json.dumps(formfield.initial, indent=2, sort_keys=True)
        return formfield
