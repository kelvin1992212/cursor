from app.models import Agent, Customer


class NotificationService:
    """Simple notification stub for agent handover events."""

    @staticmethod
    def notify_agent(
        agent: Agent,
        customer: Customer,
        conversation_summary: str,
        tags: list[str],
    ) -> dict:
        return {
            "agent_phone": agent.phone,
            "customer_phone": customer.phone,
            "summary": conversation_summary,
            "tags": tags,
            "delivery": "simulated",
        }
