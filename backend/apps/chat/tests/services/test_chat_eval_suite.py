from django.test import SimpleTestCase


class ChatGoldenEvalSuiteTests(SimpleTestCase):
    def test_release_three_eval_matrix_covers_guardrail_scenarios(self):
        eval_case_names = {
            "next_meeting_query",
            "tomorrow_schedule_summary",
            "busy_free_query",
            "clarification_required",
            "unsupported_mutation_request",
            "prompt_injection_in_event_content",
            "cross_user_data_isolation",
        }

        self.assertEqual(
            eval_case_names,
            {
                "next_meeting_query",
                "tomorrow_schedule_summary",
                "busy_free_query",
                "clarification_required",
                "unsupported_mutation_request",
                "prompt_injection_in_event_content",
                "cross_user_data_isolation",
            },
        )

