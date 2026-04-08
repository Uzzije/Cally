from django.test import SimpleTestCase

from apps.chat.services.chat_content_block_validation_service import (
    ChatContentBlockValidationError,
    ChatContentBlockValidationService,
)


class ChatContentBlockValidationServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = ChatContentBlockValidationService()

    def test_validate_accepts_email_draft_blocks(self):
        content_blocks = [
            {
                "type": "email_draft",
                "to": ["joe@example.com"],
                "cc": ["manager@example.com"],
                "subject": "Quick sync this week?",
                "body": "Hi Joe,\n\nCould we find 30 minutes this week?\n",
                "suggested_times": [
                    {
                        "date": "2026-04-14",
                        "start": "14:00",
                        "end": "14:30",
                        "timezone": "America/New_York",
                    }
                ],
                "status": "draft",
                "status_detail": "Draft only. Not sent.",
            }
        ]

        validated = self.service.validate(content_blocks)

        self.assertEqual(validated[0]["type"], "email_draft")
        self.assertEqual(validated[0]["to"], ["joe@example.com"])
        self.assertEqual(validated[0]["suggested_times"][0]["date"], "2026-04-14")

    def test_validate_rejects_email_draft_without_recipients(self):
        with self.assertRaises(ChatContentBlockValidationError):
            self.service.validate(
                [
                    {
                        "type": "email_draft",
                        "to": [],
                        "subject": "Quick sync this week?",
                        "body": "Hi Joe",
                        "status": "draft",
                    }
                ]
            )

    def test_validate_rejects_email_draft_with_invalid_status(self):
        with self.assertRaises(ChatContentBlockValidationError):
            self.service.validate(
                [
                    {
                        "type": "email_draft",
                        "to": ["joe@example.com"],
                        "subject": "Quick sync this week?",
                        "body": "Hi Joe",
                        "status": "sent",
                    }
                ]
            )

    def test_validate_rejects_email_draft_with_invalid_suggested_times(self):
        with self.assertRaises(ChatContentBlockValidationError):
            self.service.validate(
                [
                    {
                        "type": "email_draft",
                        "to": ["joe@example.com"],
                        "subject": "Quick sync this week?",
                        "body": "Hi Joe",
                        "suggested_times": [{"date": "2026-04-14", "start": "", "end": "14:30"}],
                        "status": "draft",
                    }
                ]
            )

    def test_validate_accepts_chart_blocks(self):
        validated = self.service.validate(
            [
                {
                    "type": "chart",
                    "chart_type": "bar",
                    "title": "Meeting hours this week",
                    "subtitle": "Based on synced events grouped by weekday.",
                    "data": [
                        {"label": "Mon", "value": 4},
                        {"label": "Tue", "value": 2.5},
                    ],
                    "save_enabled": True,
                }
            ]
        )

        self.assertEqual(validated[0]["type"], "chart")
        self.assertEqual(validated[0]["chart_type"], "bar")

    def test_validate_rejects_chart_blocks_with_invalid_data(self):
        with self.assertRaises(ChatContentBlockValidationError):
            self.service.validate(
                [
                    {
                        "type": "chart",
                        "chart_type": "bar",
                        "title": "Meeting hours this week",
                        "data": [{"label": "", "value": "four"}],
                    }
                ]
            )
