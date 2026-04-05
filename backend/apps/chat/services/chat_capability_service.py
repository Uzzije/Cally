from apps.core_agent.models.agent_capability import AgentCapability


class ChatCapabilityService:
    def get_release_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="read_only_chat",
                description="Allow read-only assistant answers over synced calendar data.",
            ),
            AgentCapability(
                name="clarification",
                description="Allow a single clarification turn when critical data is missing.",
            ),
        ]

