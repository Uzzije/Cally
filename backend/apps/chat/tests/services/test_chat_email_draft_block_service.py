from django.test import SimpleTestCase

from apps.chat.services.chat_email_draft_block_service import (
    ChatEmailDraftBlockService,
    ChatEmailDraftBlockServiceError,
)


class ChatEmailDraftBlockServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = ChatEmailDraftBlockService()

    def test_build_block_from_markdown_parses_subject_and_body(self):
        block = self.service.build_block_from_markdown(
            to=["joe@example.com"],
            cc=["manager@example.com"],
            suggested_times=[
                {
                    "date": "2026-04-14",
                    "start": "14:00",
                    "end": "14:30",
                    "timezone": "America/New_York",
                }
            ],
            draft_markdown=(
                "Subject: Quick sync this week?\n\n"
                "Hi Joe,\n\nCould we find 30 minutes this week?\n"
            ),
        )

        self.assertEqual(block["type"], "email_draft")
        self.assertEqual(block["subject"], "Quick sync this week?")
        self.assertEqual(block["body"], "Hi Joe,\n\nCould we find 30 minutes this week?")
        self.assertEqual(block["cc"], ["manager@example.com"])
        self.assertEqual(
            block["suggested_times"],
            [
                {
                    "date": "2026-04-14",
                    "start": "14:00",
                    "end": "14:30",
                    "timezone": "America/New_York",
                }
            ],
        )

    def test_build_block_coerces_bare_string_to_into_list(self):
        block = self.service.build_block(
            to="kayla@example.com",
            subject="Reschedule",
            body="Hi Kayla, can we move our meeting?",
        )

        self.assertEqual(block["to"], ["kayla@example.com"])

    def test_build_block_coerces_bare_string_cc_into_list(self):
        block = self.service.build_block(
            to=["kayla@example.com"],
            cc="manager@example.com",
            subject="Reschedule",
            body="Hi Kayla, can we move our meeting?",
        )

        self.assertEqual(block["cc"], ["manager@example.com"])

    def test_build_block_preserves_list_to_unchanged(self):
        block = self.service.build_block(
            to=["kayla@example.com", "joe@example.com"],
            subject="Reschedule",
            body="Hi all, can we move our meeting?",
        )

        self.assertEqual(block["to"], ["kayla@example.com", "joe@example.com"])

    def test_build_block_rejects_invalid_suggested_times(self):
        with self.assertRaises(ChatEmailDraftBlockServiceError):
            self.service.build_block(
                to=["kayla@example.com"],
                subject="Reschedule",
                body="Hi Kayla, can we move our meeting?",
                suggested_times=[{"date": "2026-04-09", "start": "", "end": "15:30"}],
            )

    def test_build_block_from_markdown_rejects_missing_subject(self):
        with self.assertRaises(ChatEmailDraftBlockServiceError):
            self.service.build_block_from_markdown(
                to=["joe@example.com"],
                draft_markdown="Hi Joe,\n\nCould we find 30 minutes this week?\n",
            )
