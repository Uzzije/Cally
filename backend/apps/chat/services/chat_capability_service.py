from apps.core_agent.models.agent_capability import AgentCapability


class ChatCapabilityService:
    def get_release_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="approval_gated_calendar_execution",
                description=(
                    "Allow the assistant to propose single-event calendar actions that only execute "
                    "after explicit user approval."
                ),
            ),
            AgentCapability(
                name="clarification",
                description="Allow a single clarification turn when critical data is missing.",
            ),
            AgentCapability(
                name="draft_email_preview",
                description=(
                    "Allow the assistant to return grounded email_draft preview blocks for "
                    "scheduling-related coordination requests without sending them."
                ),
            ),
            AgentCapability(
                name="read_only_analytics",
                description=(
                    "Allow the assistant to answer a narrow set of read-only analytics questions "
                    "with grounded text and chart blocks over synced calendar data."
                ),
            ),
        ]
