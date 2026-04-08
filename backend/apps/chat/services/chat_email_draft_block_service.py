from __future__ import annotations


class ChatEmailDraftBlockServiceError(ValueError):
    pass


class ChatEmailDraftBlockService:
    default_status_detail = "Draft only. Not sent."

    def build_block(
        self,
        *,
        to: list[str] | str,
        subject: str,
        body: str,
        cc: list[str] | str | None = None,
        suggested_times: list[dict] | None = None,
        status_detail: str | None = None,
    ) -> dict:
        """Build a normalized email_draft content block for UI rendering and persistence."""
        return {
            "type": "email_draft",
            "to": self._coerce_recipients(to),
            "cc": self._coerce_recipients(cc) if cc else [],
            "subject": subject,
            "body": body,
            "suggested_times": self._coerce_suggested_times(suggested_times),
            "status": "draft",
            "status_detail": status_detail or self.default_status_detail,
        }

    @staticmethod
    def _coerce_recipients(value: list[str] | str) -> list[str]:
        if isinstance(value, str):
            return [value]
        return list(value)

    def build_block_from_markdown(
        self,
        *,
        to: list[str] | str,
        draft_markdown: str,
        cc: list[str] | str | None = None,
        suggested_times: list[dict] | None = None,
        status_detail: str | None = None,
    ) -> dict:
        """Parse a Subject:+body markdown draft and return a validated email_draft block."""
        subject, body = self.parse_markdown_draft(draft_markdown)
        return self.build_block(
            to=to,
            cc=cc or [],
            subject=subject,
            body=body,
            suggested_times=suggested_times,
            status_detail=status_detail,
        )

    def parse_markdown_draft(self, draft_markdown: str) -> tuple[str, str]:
        """Extract (subject, body) from a markdown string containing a `Subject:` line."""
        if not isinstance(draft_markdown, str) or not draft_markdown.strip():
            raise ChatEmailDraftBlockServiceError("draft_markdown must be a non-empty string.")

        lines = draft_markdown.strip().splitlines()
        subject_line = next(
            (line.strip() for line in lines if line.strip().lower().startswith("subject:")),
            None,
        )
        if subject_line is None:
            raise ChatEmailDraftBlockServiceError("draft_markdown must include a Subject: line.")

        subject = subject_line.split(":", 1)[1].strip()
        if not subject:
            raise ChatEmailDraftBlockServiceError("draft_markdown subject must not be empty.")

        subject_index = lines.index(
            next(line for line in lines if line.strip().lower().startswith("subject:"))
        )
        body_lines = lines[subject_index + 1 :]
        while body_lines and not body_lines[0].strip():
            body_lines = body_lines[1:]
        body = "\n".join(body_lines).strip()
        if not body:
            raise ChatEmailDraftBlockServiceError("draft_markdown body must not be empty.")

        return subject, body

    def _coerce_suggested_times(self, value: list[dict] | dict | None) -> list[dict]:
        if value is None:
            return []
        if isinstance(value, dict):
            value = [value]
        if not isinstance(value, list):
            raise ChatEmailDraftBlockServiceError("suggested_times must be a list when provided.")

        normalized_entries: list[dict] = []
        for entry in value:
            if not isinstance(entry, dict):
                raise ChatEmailDraftBlockServiceError("suggested_times entries must be objects.")

            date = entry.get("date")
            start = entry.get("start")
            end = entry.get("end")
            timezone = entry.get("timezone")

            if not isinstance(date, str) or not date.strip():
                raise ChatEmailDraftBlockServiceError(
                    "suggested_times entries require a non-empty date."
                )
            if not isinstance(start, str) or not start.strip():
                raise ChatEmailDraftBlockServiceError(
                    "suggested_times entries require a non-empty start."
                )
            if not isinstance(end, str) or not end.strip():
                raise ChatEmailDraftBlockServiceError(
                    "suggested_times entries require a non-empty end."
                )
            if timezone is not None and (not isinstance(timezone, str) or not timezone.strip()):
                raise ChatEmailDraftBlockServiceError(
                    "suggested_times timezone must be a non-empty string when provided."
                )

            normalized_entry = {
                "date": date.strip(),
                "start": start.strip(),
                "end": end.strip(),
            }
            if isinstance(timezone, str) and timezone.strip():
                normalized_entry["timezone"] = timezone.strip()

            normalized_entries.append(normalized_entry)

        return normalized_entries
