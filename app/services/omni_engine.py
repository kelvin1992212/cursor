from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import OmniChatroom, OmniContact, OmniMessage, OmniThread
from app.schemas_omni import OmniInboundResult, OmniIncomingMessage
from app.services.channel import ChannelGateway
from app.services.omni_integration import get_chatroom_integration

VALID_CHANNELS = {"whatsapp", "wechat", "facebook", "instagram"}


def _parse_hhmm(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)


def is_ai_active_for_chatroom(chatroom: OmniChatroom, now: datetime | None = None) -> bool:
    if not chatroom.ai_enabled:
        return False

    current = now.astimezone(ZoneInfo(chatroom.timezone)) if now else datetime.now(ZoneInfo(chatroom.timezone))
    current_minutes = current.hour * 60 + current.minute

    start_hour, start_minute = _parse_hhmm(chatroom.ai_schedule_start)
    end_hour, end_minute = _parse_hhmm(chatroom.ai_schedule_end)
    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute

    # Same value means 24/7.
    if start_minutes == end_minutes:
        return True
    if start_minutes < end_minutes:
        return start_minutes <= current_minutes < end_minutes
    return current_minutes >= start_minutes or current_minutes < end_minutes


def _auto_reply_text(channel: str, chatroom_name: str, inbound_text: str) -> str:
    lowered = inbound_text.lower()
    if "真人" in inbound_text or "human" in lowered or "agent" in lowered:
        return "已收到，你想轉真人客服。團隊會盡快喺此聊天室跟進你。"
    if "價錢" in inbound_text or "price" in lowered:
        return "收到查詢價錢，我哋會即刻整理資料回覆你。"
    if "預約" in inbound_text or "booking" in lowered:
        return "收到預約需求，請提供你希望時段，我哋會安排。"
    return f"你好，這裡是 {chatroom_name}（{channel}）智能客服，已收到你的訊息，稍後會為你跟進。"


def _openai_reply(inbound_text: str, integration: dict) -> str | None:
    api_key = str(integration.get("openai_api_key") or "").strip()
    if not api_key:
        return None

    model = str(integration.get("openai_model") or "gpt-4o-mini")
    system_prompt = (
        "You are a concise customer support assistant for a multi-channel chatroom. "
        "Reply in Traditional Chinese unless the user writes clearly in English."
    )
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": inbound_text},
        ],
    }
    try:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("output_text")
        if isinstance(text, str) and text.strip():
            return text.strip()

        output = data.get("output", [])
        if output and isinstance(output, list):
            content = output[0].get("content", [])
            if content and isinstance(content, list):
                first = content[0]
                extracted = first.get("text")
                if isinstance(extracted, str) and extracted.strip():
                    return extracted.strip()
    except Exception:  # pragma: no cover - network dependent
        return None
    return None


class OmniEngine:
    def __init__(self, db: Session):
        self.db = db
        self.gateway = ChannelGateway(get_settings())

    def get_or_create_chatroom(self, channel: str, external_room_id: str) -> OmniChatroom:
        channel = channel.strip().lower()
        if channel not in VALID_CHANNELS:
            raise ValueError(f"Unsupported channel: {channel}")

        chatroom = (
            self.db.query(OmniChatroom)
            .filter(
                OmniChatroom.channel == channel,
                OmniChatroom.external_room_id == external_room_id,
            )
            .one_or_none()
        )
        if chatroom is None:
            chatroom = OmniChatroom(
                name=f"{channel.title()} - {external_room_id}",
                channel=channel,
                external_room_id=external_room_id,
                ai_enabled=True,
                ai_schedule_start="00:00",
                ai_schedule_end="00:00",
                timezone="Asia/Hong_Kong",
            )
            self.db.add(chatroom)
            self.db.flush()
        return chatroom

    def get_or_create_contact(self, channel: str, contact_id: str, contact_name: str | None) -> OmniContact:
        contact = (
            self.db.query(OmniContact)
            .filter(
                OmniContact.channel == channel,
                OmniContact.external_user_id == contact_id,
            )
            .one_or_none()
        )
        if contact is None:
            contact = OmniContact(
                channel=channel,
                external_user_id=contact_id,
                display_name=contact_name,
            )
            self.db.add(contact)
            self.db.flush()
        elif contact_name and not contact.display_name:
            contact.display_name = contact_name
        return contact

    def get_or_create_thread(self, chatroom: OmniChatroom, contact: OmniContact) -> OmniThread:
        thread = (
            self.db.query(OmniThread)
            .filter(
                OmniThread.chatroom_id == chatroom.id,
                OmniThread.contact_id == contact.id,
            )
            .one_or_none()
        )
        if thread is None:
            thread = OmniThread(chatroom_id=chatroom.id, contact_id=contact.id, status="open")
            self.db.add(thread)
            self.db.flush()
        return thread

    def save_message(
        self,
        thread_id: int,
        direction: str,
        sender_type: str,
        content: str,
        raw_payload: dict | None = None,
    ) -> OmniMessage:
        message = OmniMessage(
            thread_id=thread_id,
            direction=direction,
            sender_type=sender_type,
            content=content,
            raw_payload=raw_payload,
        )
        self.db.add(message)
        self.db.flush()
        return message

    def process_incoming(self, incoming: OmniIncomingMessage) -> OmniInboundResult:
        chatroom = self.get_or_create_chatroom(incoming.channel, incoming.chatroom_external_id)
        integration = get_chatroom_integration(self.db, chatroom.id)
        contact = self.get_or_create_contact(incoming.channel, incoming.contact_id, incoming.contact_name)
        thread = self.get_or_create_thread(chatroom, contact)

        self.save_message(
            thread_id=thread.id,
            direction="inbound",
            sender_type="customer",
            content=incoming.text,
            raw_payload=incoming.metadata,
        )
        thread.last_message_at = datetime.now(ZoneInfo(chatroom.timezone))

        reply_text: str | None = None
        ai_replied = False
        if is_ai_active_for_chatroom(chatroom):
            provider = str(integration.get("ai_provider") or "rule_based")
            if provider == "openai":
                reply_text = _openai_reply(incoming.text, integration)
            if not reply_text:
                reply_text = _auto_reply_text(chatroom.channel, chatroom.name, incoming.text)
            self.save_message(
                thread_id=thread.id,
                direction="outbound",
                sender_type="ai",
                content=reply_text,
                raw_payload=None,
            )
            self.gateway.send_text(chatroom.channel, incoming.contact_id, reply_text)
            ai_replied = True

        thread.last_message_at = datetime.now(ZoneInfo(chatroom.timezone))
        self.db.commit()

        return OmniInboundResult(
            chatroom_id=chatroom.id,
            chatroom_name=chatroom.name,
            channel=chatroom.channel,
            thread_id=thread.id,
            contact_id=contact.external_user_id,
            ai_replied=ai_replied,
            reply_text=reply_text,
        )
