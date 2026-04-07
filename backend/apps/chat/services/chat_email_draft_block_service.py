from __future__ import annotations


class ChatEmailDraftBlockServiceError(ValueError):
    pass


class ChatEmailDraftBlockService:
    default_status_detail = "Draft only. Not sent."

    def build_block(
        self,
        *,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        status_detail: str | None = None,
    ) -> dict:
        return {
            "type": "email_draft",
            "to": list(to),
            "cc": list(cc or []),
            "subject": subject,
            "body": body,
            "status": "draft",
            "status_detail": status_detail or self.default_status_detail,
        }

    def build_block_from_markdown(
        self,
        *,
        to: list[str],
        draft_markdown: str,
        cc: list[str] | None = None,
        status_detail: str | None = None,
    ) -> dict:
        subject, body = self.parse_markdown_draft(draft_markdown)
        return self.build_block(
            to=to,
            cc=cc or [],
            subject=subject,
            body=body,
            status_detail=status_detail,
        )

    def parse_markdown_draft(self, draft_markdown: str) -> tuple[str, str]:
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
