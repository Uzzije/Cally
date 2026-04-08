from __future__ import annotations


class ChatContentBlockValidationError(ValueError):
    pass


class ChatContentBlockValidationService:
    text_block_types = {"text", "clarification", "status"}
    action_statuses = {"pending", "approved", "rejected", "executing", "executed", "failed"}
    email_draft_statuses = {"draft"}
    chart_types = {"bar", "line", "pie", "heatmap"}

    def validate(self, content_blocks: list[dict]) -> list[dict]:
        """Validate persisted UI content blocks (text/action_card/email_draft/chart), raising on invalid shape."""
        if not isinstance(content_blocks, list):
            raise ChatContentBlockValidationError("content_blocks must be a list.")

        for block in content_blocks:
            self._validate_block(block)

        return content_blocks

    def _validate_block(self, block: dict) -> None:
        if not isinstance(block, dict):
            raise ChatContentBlockValidationError("Each content block must be an object.")

        block_type = block.get("type")
        if block_type in self.text_block_types:
            if not isinstance(block.get("text"), str) or not block["text"].strip():
                raise ChatContentBlockValidationError(
                    f"{block_type} blocks require non-empty text."
                )
            return

        if block_type == "action_card":
            self._validate_action_card_block(block)
            return

        if block_type == "email_draft":
            self._validate_email_draft_block(block)
            return

        if block_type == "chart":
            self._validate_chart_block(block)
            return

        raise ChatContentBlockValidationError(f"Unsupported content block type: {block_type}.")

    def _validate_action_card_block(self, block: dict) -> None:
        actions = block.get("actions")
        if not isinstance(actions, list) or not actions:
            raise ChatContentBlockValidationError("action_card blocks require at least one action.")

        for action in actions:
            self._validate_action(action)

    def _validate_action(self, action: dict) -> None:
        if not isinstance(action, dict):
            raise ChatContentBlockValidationError("Each action must be an object.")

        if not isinstance(action.get("id"), str) or not action["id"].strip():
            raise ChatContentBlockValidationError("Actions require a non-empty id.")

        if action.get("action_type") != "create_event":
            raise ChatContentBlockValidationError(
                "Iteration 05 supports only create_event action cards."
            )

        if not isinstance(action.get("summary"), str) or not action["summary"].strip():
            raise ChatContentBlockValidationError("Actions require a non-empty summary.")

        details = action.get("details")
        if not isinstance(details, dict):
            raise ChatContentBlockValidationError("Actions require a details object.")

        if not isinstance(details.get("date"), str) or not details["date"].strip():
            raise ChatContentBlockValidationError("Action details require a date.")

        if not isinstance(details.get("time"), str) or not details["time"].strip():
            raise ChatContentBlockValidationError("Action details require a time range.")

        attendees = details.get("attendees")
        if not isinstance(attendees, list) or not all(
            isinstance(attendee, str) and attendee.strip() for attendee in attendees
        ):
            raise ChatContentBlockValidationError(
                "Action details attendees must be a list of non-empty strings."
            )

        rank = details.get("rank")
        if rank is not None and (not isinstance(rank, int) or rank < 1):
            raise ChatContentBlockValidationError(
                "Action details rank must be a positive integer when provided."
            )

        why = details.get("why")
        if why is not None and (not isinstance(why, str) or not why.strip()):
            raise ChatContentBlockValidationError(
                "Action details why must be a non-empty string when provided."
            )

        if action.get("status") not in self.action_statuses:
            raise ChatContentBlockValidationError("Actions require a supported status.")

        status_detail = action.get("status_detail")
        if status_detail is not None and (
            not isinstance(status_detail, str) or not status_detail.strip()
        ):
            raise ChatContentBlockValidationError(
                "Action status_detail must be a non-empty string when provided."
            )

        result = action.get("result")
        if result is not None and not isinstance(result, dict):
            raise ChatContentBlockValidationError("Action result must be an object when provided.")

        payload = action.get("payload")
        if payload is not None and not isinstance(payload, dict):
            raise ChatContentBlockValidationError("Action payload must be an object when provided.")

    def _validate_email_draft_block(self, block: dict) -> None:
        to_recipients = block.get("to")
        if (
            not isinstance(to_recipients, list)
            or not to_recipients
            or not all(
                isinstance(recipient, str) and recipient.strip() for recipient in to_recipients
            )
        ):
            raise ChatContentBlockValidationError(
                "email_draft blocks require at least one non-empty recipient in to."
            )

        cc_recipients = block.get("cc", [])
        if not isinstance(cc_recipients, list) or not all(
            isinstance(recipient, str) and recipient.strip() for recipient in cc_recipients
        ):
            raise ChatContentBlockValidationError(
                "email_draft blocks require cc to be a list of non-empty strings when provided."
            )

        if not isinstance(block.get("subject"), str) or not block["subject"].strip():
            raise ChatContentBlockValidationError("email_draft blocks require a non-empty subject.")

        if not isinstance(block.get("body"), str) or not block["body"].strip():
            raise ChatContentBlockValidationError("email_draft blocks require a non-empty body.")

        if block.get("status") not in self.email_draft_statuses:
            raise ChatContentBlockValidationError(
                "email_draft blocks require a supported draft status."
            )

        status_detail = block.get("status_detail")
        if status_detail is not None and (
            not isinstance(status_detail, str) or not status_detail.strip()
        ):
            raise ChatContentBlockValidationError(
                "email_draft status_detail must be a non-empty string when provided."
            )

        suggested_times = block.get("suggested_times", [])
        if not isinstance(suggested_times, list):
            raise ChatContentBlockValidationError(
                "email_draft suggested_times must be a list when provided."
            )

        for suggested_time in suggested_times:
            self._validate_email_draft_suggested_time(suggested_time)

    def _validate_email_draft_suggested_time(self, suggested_time: dict) -> None:
        if not isinstance(suggested_time, dict):
            raise ChatContentBlockValidationError(
                "email_draft suggested_times entries must be objects."
            )

        if not isinstance(suggested_time.get("date"), str) or not suggested_time["date"].strip():
            raise ChatContentBlockValidationError(
                "email_draft suggested_times entries require a non-empty date."
            )

        if not isinstance(suggested_time.get("start"), str) or not suggested_time["start"].strip():
            raise ChatContentBlockValidationError(
                "email_draft suggested_times entries require a non-empty start."
            )

        if not isinstance(suggested_time.get("end"), str) or not suggested_time["end"].strip():
            raise ChatContentBlockValidationError(
                "email_draft suggested_times entries require a non-empty end."
            )

        timezone = suggested_time.get("timezone")
        if timezone is not None and (not isinstance(timezone, str) or not timezone.strip()):
            raise ChatContentBlockValidationError(
                "email_draft suggested_times timezone must be a non-empty string when provided."
            )

    def _validate_chart_block(self, block: dict) -> None:
        if block.get("chart_type") not in self.chart_types:
            raise ChatContentBlockValidationError("chart blocks require a supported chart_type.")

        if not isinstance(block.get("title"), str) or not block["title"].strip():
            raise ChatContentBlockValidationError("chart blocks require a non-empty title.")

        subtitle = block.get("subtitle")
        if subtitle is not None and (not isinstance(subtitle, str) or not subtitle.strip()):
            raise ChatContentBlockValidationError(
                "chart subtitle must be a non-empty string when provided."
            )

        data = block.get("data")
        if not isinstance(data, list) or not data:
            raise ChatContentBlockValidationError("chart blocks require at least one data point.")

        for point in data:
            if not isinstance(point, dict):
                raise ChatContentBlockValidationError("chart data points must be objects.")
            if not isinstance(point.get("label"), str) or not point["label"].strip():
                raise ChatContentBlockValidationError(
                    "chart data points require a non-empty label."
                )
            value = point.get("value")
            if not isinstance(value, int | float):
                raise ChatContentBlockValidationError("chart data points require a numeric value.")

        save_enabled = block.get("save_enabled")
        if save_enabled is not None and not isinstance(save_enabled, bool):
            raise ChatContentBlockValidationError(
                "chart save_enabled must be a boolean when provided."
            )
