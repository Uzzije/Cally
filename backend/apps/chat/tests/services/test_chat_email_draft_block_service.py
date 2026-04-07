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
            draft_markdown=(
                "Subject: Quick sync this week?\n\n"
                "Hi Joe,\n\nCould we find 30 minutes this week?\n"
            ),
        )

        self.assertEqual(block["type"], "email_draft")
        self.assertEqual(block["subject"], "Quick sync this week?")
        self.assertEqual(block["body"], "Hi Joe,\n\nCould we find 30 minutes this week?")
        self.assertEqual(block["cc"], ["manager@example.com"])

    def test_build_block_from_markdown_rejects_missing_subject(self):
        with self.assertRaises(ChatEmailDraftBlockServiceError):
            self.service.build_block_from_markdown(
                to=["joe@example.com"],
                draft_markdown="Hi Joe,\n\nCould we find 30 minutes this week?\n",
            )
