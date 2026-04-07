from django.test import SimpleTestCase


class ChatGoldenEvalSuiteTests(SimpleTestCase):
    def test_release_four_eval_matrix_covers_loop_and_proposal_scenarios(self):
        eval_case_names = {
            "next_meeting_query",
            "tomorrow_schedule_summary",
            "busy_free_query",
            "clarification_required",
            "unsupported_mutation_request",
            "prompt_injection_in_event_content",
            "cross_user_data_isolation",
            "preferences_question_uses_get_preferences_tool",
            "scheduling_question_returns_review_only_action_card",
            "loop_rejects_invalid_tool_arguments",
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
                "preferences_question_uses_get_preferences_tool",
                "scheduling_question_returns_review_only_action_card",
                "loop_rejects_invalid_tool_arguments",
            },
        )
