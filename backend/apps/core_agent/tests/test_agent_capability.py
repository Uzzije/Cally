from django.test import SimpleTestCase

from apps.core_agent.models.agent_capability import AgentCapability


class AgentCapabilityTests(SimpleTestCase):
    def test_capability_defaults_to_enabled(self):
        capability = AgentCapability(
            name="read_only_chat",
            description="Allow read-only assistant turns.",
        )

        self.assertTrue(capability.enabled)
