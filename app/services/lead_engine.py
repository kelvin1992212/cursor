from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Agent, ConversationMessage, Customer, LeadAssignment, Tag
from app.schemas import IncomingMessage, WebhookProcessResponse
from app.services.calendar_service import CalendarService
from app.services.channel import ChannelGateway
from app.services.intents import detect_intent, extract_budget, infer_tags
from app.services.knowledge_base import KnowledgeBaseService
from app.services.notification import NotificationService
from app.services.reporting import create_report
from app.services.settings_service import RR_COUNTER_KEY, get_setting, is_ai_available_now, set_setting


class LeadEngine:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.calendar = CalendarService(db)
        self.channel = ChannelGateway(self.settings)
        self.knowledge_base = KnowledgeBaseService(db)
        self.notification_service = NotificationService()

    def process_incoming(self, incoming: IncomingMessage) -> WebhookProcessResponse:
        customer = self._get_or_create_customer(incoming.phone, incoming.name, incoming.channel)
        self._save_message(
            customer_id=customer.id,
            direction="inbound",
            channel=incoming.channel,
            content=incoming.text,
            handled_by="customer",
            payload=incoming.metadata,
        )

        tags = infer_tags(incoming.text)
        self._attach_tags(customer, tags)
        self._update_customer_budget(customer, incoming.text)

        intent = detect_intent(incoming.text)
        customer.intent_stage = self._intent_stage(intent.intent)

        ai_available = is_ai_available_now(self.db, self.settings)
        if not ai_available:
            self.db.commit()
            return WebhookProcessResponse(
                mode="human_only",
                customer_phone=customer.phone,
                ai_replied=False,
                handover=False,
                tags=[tag.name for tag in customer.tags],
            )

        reply_text, cards = self._generate_reply(customer, incoming.text, intent.intent, intent.needs_booking)
        handover = False
        assigned_agent_name: str | None = None
        if intent.needs_handover:
            assignment = self._handover_to_agent(customer, reason=intent.intent)
            if assignment:
                handover = True
                customer.follow_up_status = "handover"
                assigned_agent_name = assignment.agent.name
                report = create_report(
                    db=self.db,
                    customer=customer,
                    tags=[tag.name for tag in customer.tags],
                    agent_id=assignment.agent_id,
                )
                self.notification_service.notify_agent(
                    assignment.agent,
                    customer,
                    report.summary_json.get("conversation_summary", ""),
                    [tag.name for tag in customer.tags],
                )
                reply_text = f"已為你轉接真人 Agent {assignment.agent.name}，稍後會直接跟進你。\n{reply_text}"

        self._save_message(
            customer_id=customer.id,
            direction="outbound",
            channel=incoming.channel,
            content=reply_text,
            handled_by="ai" if not handover else "system",
            payload={"cards": cards} if cards else None,
        )

        self.channel.send_text(incoming.channel, customer.phone, reply_text)
        if cards:
            self.channel.send_property_cards(incoming.channel, customer.phone, cards)

        self.db.commit()
        return WebhookProcessResponse(
            mode="handover" if handover else "ai_replied",
            customer_phone=customer.phone,
            ai_replied=True,
            handover=handover,
            assigned_agent=assigned_agent_name,
            reply_text=reply_text,
            tags=[tag.name for tag in customer.tags],
        )

    def _generate_reply(
        self,
        customer: Customer,
        text: str,
        intent: str,
        needs_booking: bool,
    ) -> tuple[str, list[dict[str, Any]]]:
        if needs_booking:
            slots = self.calendar.suggest_slots(self.settings.default_timezone)
            slot_text = ", ".join(slot.strftime("%m-%d %H:%M") for slot in slots[:4])
            return (
                (
                    "明白，你想預約睇樓/諮詢。以下是可選時段："
                    f"{slot_text}。請回覆你心儀時間，我會立即安排。"
                ),
                [],
            )

        faq = self.knowledge_base.faq_answer(intent)
        if faq:
            properties = self.knowledge_base.search_properties(text, limit=2)
            return faq, self.knowledge_base.property_cards(properties)

        properties = self.knowledge_base.search_properties(text, limit=3)
        if properties:
            top = properties[0]
            price_text = f"{top.currency} {top.price:,}" if top.price else "價格待確認"
            reply = (
                f"幫你找到 {len(properties)} 個相關樓盤。"
                f"先看 {top.title}（{top.district}），參考價 {price_text}。"
                "我已一併發送樓盤圖文與連結。"
            )
            return reply, self.knowledge_base.property_cards(properties)

        fallback = (
            "你好，我係 House 88 AI 助手。你可直接講區域、預算、買/租需求，"
            "我會即時提供樓盤資料、價錢、設施及按揭資訊。"
        )
        return fallback, []

    def _get_or_create_customer(self, phone: str, name: str | None, channel: str) -> Customer:
        row = self.db.query(Customer).filter(Customer.phone == phone).one_or_none()
        if row is None:
            row = Customer(phone=phone, name=name, preferred_channel=channel)
            self.db.add(row)
            self.db.flush()
            return row
        if name and not row.name:
            row.name = name
        row.preferred_channel = channel
        return row

    def _save_message(
        self,
        customer_id: int,
        direction: str,
        channel: str,
        content: str,
        handled_by: str,
        payload: dict[str, Any] | None,
    ) -> None:
        row = ConversationMessage(
            customer_id=customer_id,
            direction=direction,
            channel=channel,
            content=content,
            handled_by=handled_by,
            interactive_payload=payload,
        )
        self.db.add(row)
        self.db.flush()

    def _attach_tags(self, customer: Customer, tag_names: list[str]) -> None:
        if not tag_names:
            return
        existing = (
            self.db.query(Tag)
            .filter(Tag.name.in_(tag_names))
            .all()
        )
        existing_map = {tag.name: tag for tag in existing}
        for name in tag_names:
            tag = existing_map.get(name)
            if tag is None:
                tag = Tag(name=name)
                self.db.add(tag)
                self.db.flush()
            if tag not in customer.tags:
                customer.tags.append(tag)

    def _update_customer_budget(self, customer: Customer, text: str) -> None:
        budget_min, budget_max = extract_budget(text)
        if budget_min is None or budget_max is None:
            return
        customer.budget_min = budget_min
        customer.budget_max = budget_max

    @staticmethod
    def _intent_stage(intent: str) -> str:
        if intent == "handover":
            return "hot_lead"
        if intent == "booking":
            return "booking_requested"
        if intent in {"buy_interest", "rent_interest"}:
            return "qualified"
        if intent in {"pricing", "mortgage", "facilities"}:
            return "engaged"
        return "new"

    def _handover_to_agent(self, customer: Customer, reason: str) -> LeadAssignment | None:
        agents = (
            self.db.query(Agent)
            .filter(Agent.is_active.is_(True))
            .order_by(Agent.id.asc())
            .all()
        )
        if not agents:
            return None

        index = int(get_setting(self.db, RR_COUNTER_KEY, 0))
        agent = agents[index % len(agents)]
        assignment = LeadAssignment(
            customer_id=customer.id,
            agent_id=agent.id,
            reason=reason,
            status="open",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(assignment)
        set_setting(self.db, RR_COUNTER_KEY, index + 1)
        self.db.flush()
        return assignment
