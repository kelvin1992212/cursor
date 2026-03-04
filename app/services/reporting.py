from sqlalchemy.orm import Session

from app.models import ConversationMessage, Customer, LeadReport


def _summarize_messages(messages: list[ConversationMessage]) -> str:
    if not messages:
        return "No conversation history yet."
    latest = messages[-6:]
    lines = [f"{row.direction}: {row.content}" for row in latest]
    return " | ".join(lines)


def build_report_payload(customer: Customer, messages: list[ConversationMessage], tags: list[str]) -> dict:
    return {
        "customer_phone": customer.phone,
        "customer_name": customer.name,
        "budget_min": customer.budget_min,
        "budget_max": customer.budget_max,
        "intent_stage": customer.intent_stage,
        "follow_up_status": customer.follow_up_status,
        "tags": tags,
        "conversation_summary": _summarize_messages(messages),
    }


def create_report(
    db: Session,
    customer: Customer,
    tags: list[str],
    agent_id: int | None = None,
) -> LeadReport:
    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.customer_id == customer.id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )
    payload = build_report_payload(customer, messages, tags)
    report = LeadReport(customer_id=customer.id, agent_id=agent_id, summary_json=payload)
    db.add(report)
    db.flush()
    return report
