from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OmniChatroom, OmniMessage, OmniThread
from app.schemas_omni import (
    OmniIntegrationRead,
    OmniIntegrationUpdate,
    OmniChatroomAIStatusRead,
    OmniChatroomAIScheduleUpdate,
    OmniChatroomAIStatusUpdate,
    OmniChatroomCreate,
    OmniChatroomRead,
    OmniInboundResult,
    OmniIncomingMessage,
    OmniMessageRead,
    OmniSendMessage,
    OmniThreadRead,
)
from app.services.omni_engine import OmniEngine, VALID_CHANNELS
from app.services.omni_integration import get_chatroom_integration, set_chatroom_integration

router = APIRouter(prefix="/omni", tags=["omnichannel"])


def _chatroom_or_404(db: Session, chatroom_id: int) -> OmniChatroom:
    row = db.query(OmniChatroom).filter(OmniChatroom.id == chatroom_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Chatroom not found.")
    return row


def _thread_or_404(db: Session, thread_id: int) -> OmniThread:
    row = db.query(OmniThread).filter(OmniThread.id == thread_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Thread not found.")
    return row


def _integration_read(chatroom: OmniChatroom, payload: dict) -> OmniIntegrationRead:
    return OmniIntegrationRead(
        chatroom_id=chatroom.id,
        phone_number_id=payload.get("phone_number_id") or chatroom.external_room_id,
        webhook_verify_token_set=bool(payload.get("webhook_verify_token")),
        whatsapp_access_token_set=bool(payload.get("whatsapp_access_token")),
        openai_api_key_set=bool(payload.get("openai_api_key")),
        openai_model=str(payload.get("openai_model") or "gpt-4o-mini"),
        ai_provider=str(payload.get("ai_provider") or "rule_based"),
    )


@router.get("/chatrooms", response_model=list[OmniChatroomRead])
def list_chatrooms(
    channel: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[OmniChatroomRead]:
    query = db.query(OmniChatroom)
    if channel:
        query = query.filter(OmniChatroom.channel == channel.lower())
    rows = query.order_by(OmniChatroom.updated_at.desc()).all()
    return [
        OmniChatroomRead(
            id=row.id,
            name=row.name,
            channel=row.channel,
            external_room_id=row.external_room_id,
            ai_enabled=row.ai_enabled,
            ai_schedule_start=row.ai_schedule_start,
            ai_schedule_end=row.ai_schedule_end,
            timezone=row.timezone,
            thread_count=len(row.threads),
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.post("/chatrooms", response_model=OmniChatroomRead)
def create_chatroom(payload: OmniChatroomCreate, db: Session = Depends(get_db)) -> OmniChatroomRead:
    existing = (
        db.query(OmniChatroom)
        .filter(
            OmniChatroom.channel == payload.channel,
            OmniChatroom.external_room_id == payload.external_room_id,
        )
        .one_or_none()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Chatroom already exists for this channel and external_room_id.")

    row = OmniChatroom(
        name=payload.name,
        channel=payload.channel,
        external_room_id=payload.external_room_id,
        ai_enabled=payload.ai_enabled,
        ai_schedule_start=payload.ai_schedule_start,
        ai_schedule_end=payload.ai_schedule_end,
        timezone=payload.timezone,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return OmniChatroomRead(
        id=row.id,
        name=row.name,
        channel=row.channel,
        external_room_id=row.external_room_id,
        ai_enabled=row.ai_enabled,
        ai_schedule_start=row.ai_schedule_start,
        ai_schedule_end=row.ai_schedule_end,
        timezone=row.timezone,
        thread_count=0,
        updated_at=row.updated_at,
    )


@router.get("/chatrooms/{chatroom_id}/ai", response_model=OmniChatroomAIStatusRead)
def get_chatroom_ai(chatroom_id: int, db: Session = Depends(get_db)) -> OmniChatroomAIStatusRead:
    row = _chatroom_or_404(db, chatroom_id)
    return OmniChatroomAIStatusRead(
        chatroom_id=row.id,
        ai_enabled=row.ai_enabled,
        ai_schedule_start=row.ai_schedule_start,
        ai_schedule_end=row.ai_schedule_end,
        timezone=row.timezone,
    )


@router.put("/chatrooms/{chatroom_id}/ai/status", response_model=OmniChatroomAIStatusRead)
def update_chatroom_ai_status(
    chatroom_id: int,
    payload: OmniChatroomAIStatusUpdate,
    db: Session = Depends(get_db),
) -> OmniChatroomAIStatusRead:
    row = _chatroom_or_404(db, chatroom_id)
    row.ai_enabled = payload.enabled
    db.commit()
    db.refresh(row)
    return OmniChatroomAIStatusRead(
        chatroom_id=row.id,
        ai_enabled=row.ai_enabled,
        ai_schedule_start=row.ai_schedule_start,
        ai_schedule_end=row.ai_schedule_end,
        timezone=row.timezone,
    )


@router.post("/chatrooms/{chatroom_id}/ai/pause", response_model=OmniChatroomAIStatusRead)
def pause_chatroom_ai(chatroom_id: int, db: Session = Depends(get_db)) -> OmniChatroomAIStatusRead:
    row = _chatroom_or_404(db, chatroom_id)
    row.ai_enabled = False
    db.commit()
    db.refresh(row)
    return OmniChatroomAIStatusRead(
        chatroom_id=row.id,
        ai_enabled=row.ai_enabled,
        ai_schedule_start=row.ai_schedule_start,
        ai_schedule_end=row.ai_schedule_end,
        timezone=row.timezone,
    )


@router.put("/chatrooms/{chatroom_id}/ai/schedule", response_model=OmniChatroomAIStatusRead)
def update_chatroom_ai_schedule(
    chatroom_id: int,
    payload: OmniChatroomAIScheduleUpdate,
    db: Session = Depends(get_db),
) -> OmniChatroomAIStatusRead:
    row = _chatroom_or_404(db, chatroom_id)
    row.ai_schedule_start = payload.ai_schedule_start
    row.ai_schedule_end = payload.ai_schedule_end
    row.timezone = payload.timezone
    db.commit()
    db.refresh(row)
    return OmniChatroomAIStatusRead(
        chatroom_id=row.id,
        ai_enabled=row.ai_enabled,
        ai_schedule_start=row.ai_schedule_start,
        ai_schedule_end=row.ai_schedule_end,
        timezone=row.timezone,
    )


@router.get("/chatrooms/{chatroom_id}/integration", response_model=OmniIntegrationRead)
def get_chatroom_integration_api(chatroom_id: int, db: Session = Depends(get_db)) -> OmniIntegrationRead:
    chatroom = _chatroom_or_404(db, chatroom_id)
    payload = get_chatroom_integration(db, chatroom_id)
    return _integration_read(chatroom, payload)


@router.put("/chatrooms/{chatroom_id}/integration", response_model=OmniIntegrationRead)
def update_chatroom_integration_api(
    chatroom_id: int,
    update: OmniIntegrationUpdate,
    db: Session = Depends(get_db),
) -> OmniIntegrationRead:
    chatroom = _chatroom_or_404(db, chatroom_id)
    current = get_chatroom_integration(db, chatroom_id)
    merged = dict(current)

    values = update.model_dump(exclude_unset=True)
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            merged.pop(key, None)
        else:
            merged[key] = value

    phone_number_id = merged.get("phone_number_id")
    if phone_number_id and chatroom.channel == "whatsapp":
        chatroom.external_room_id = str(phone_number_id)

    set_chatroom_integration(db, chatroom_id, merged)
    db.commit()
    db.refresh(chatroom)
    return _integration_read(chatroom, merged)


@router.get("/chatrooms/{chatroom_id}/threads", response_model=list[OmniThreadRead])
def list_chatroom_threads(
    chatroom_id: int,
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[OmniThreadRead]:
    _chatroom_or_404(db, chatroom_id)
    query = db.query(OmniThread).filter(OmniThread.chatroom_id == chatroom_id)
    if status:
        query = query.filter(OmniThread.status == status)
    rows = query.order_by(OmniThread.last_message_at.desc()).all()

    result: list[OmniThreadRead] = []
    for row in rows:
        latest = (
            db.query(OmniMessage)
            .filter(OmniMessage.thread_id == row.id)
            .order_by(OmniMessage.created_at.desc())
            .first()
        )
        result.append(
            OmniThreadRead(
                id=row.id,
                chatroom_id=row.chatroom_id,
                contact_channel=row.contact.channel,
                contact_external_user_id=row.contact.external_user_id,
                contact_display_name=row.contact.display_name,
                status=row.status,
                assigned_agent_name=row.assigned_agent.name if row.assigned_agent else None,
                last_message_at=row.last_message_at,
                last_message_preview=latest.content if latest else None,
            )
        )
    return result


@router.get("/threads/{thread_id}/messages", response_model=list[OmniMessageRead])
def list_thread_messages(
    thread_id: int,
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[OmniMessageRead]:
    _thread_or_404(db, thread_id)
    rows = (
        db.query(OmniMessage)
        .filter(OmniMessage.thread_id == thread_id)
        .order_by(OmniMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    return [
        OmniMessageRead(
            id=row.id,
            thread_id=row.thread_id,
            direction=row.direction,
            sender_type=row.sender_type,
            content=row.content,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/threads/{thread_id}/messages", response_model=OmniMessageRead)
def send_thread_message(
    thread_id: int,
    payload: OmniSendMessage,
    db: Session = Depends(get_db),
) -> OmniMessageRead:
    thread = _thread_or_404(db, thread_id)
    engine = OmniEngine(db)
    message = engine.save_message(
        thread_id=thread.id,
        direction="outbound",
        sender_type=payload.sender_type,
        content=payload.content,
        raw_payload=None,
    )
    thread.last_message_at = datetime.now(ZoneInfo(thread.chatroom.timezone))
    integration = get_chatroom_integration(db, thread.chatroom_id)
    engine.gateway.send_text(
        thread.chatroom.channel,
        thread.contact.external_user_id,
        payload.content,
        provider_config={
            "phone_number_id": integration.get("phone_number_id") or thread.chatroom.external_room_id,
            "access_token": integration.get("whatsapp_access_token"),
        },
    )
    db.commit()
    db.refresh(message)
    return OmniMessageRead(
        id=message.id,
        thread_id=message.thread_id,
        direction=message.direction,
        sender_type=message.sender_type,
        content=message.content,
        created_at=message.created_at,
    )


def _incoming_from_payload(channel: str, payload: dict) -> OmniIncomingMessage:
    external_id = (
        payload.get("chatroom_external_id")
        or payload.get("external_room_id")
        or payload.get("account_id")
        or payload.get("page_id")
        or payload.get("phone_number_id")
    )
    contact_id = (
        payload.get("contact_id")
        or payload.get("user_id")
        or payload.get("sender_id")
        or payload.get("from")
        or payload.get("phone")
    )
    text = payload.get("text") or payload.get("message") or payload.get("content")
    if not external_id or not contact_id or not text:
        raise HTTPException(
            status_code=400,
            detail="Payload requires chatroom identifier, contact identifier, and text content.",
        )
    return OmniIncomingMessage(
        channel=channel,
        chatroom_external_id=str(external_id),
        contact_id=str(contact_id),
        contact_name=payload.get("contact_name") or payload.get("name"),
        text=str(text),
        metadata={"raw": payload},
    )


def _incoming_from_whatsapp_payload(phone_number_id: str, payload: dict) -> OmniIncomingMessage:
    text = payload.get("text") or payload.get("message")
    contact_id = payload.get("contact_id") or payload.get("from") or payload.get("phone")
    if text and contact_id:
        return OmniIncomingMessage(
            channel="whatsapp",
            chatroom_external_id=phone_number_id,
            contact_id=str(contact_id),
            contact_name=payload.get("contact_name") or payload.get("name"),
            text=str(text),
            metadata={"raw": payload},
        )

    try:
        value = payload["entry"][0]["changes"][0]["value"]
        message = value["messages"][0]
        contacts = value.get("contacts") or []
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid WhatsApp payload: {exc}") from exc

    contact_id = str(message.get("from", "")).strip()
    text = (
        message.get("text", {}).get("body")
        or message.get("button", {}).get("text")
        or message.get("interactive", {}).get("button_reply", {}).get("title")
    )
    if not contact_id or not text:
        raise HTTPException(status_code=400, detail="Unsupported WhatsApp message format.")

    contact_name = None
    if contacts:
        contact_name = contacts[0].get("profile", {}).get("name")

    return OmniIncomingMessage(
        channel="whatsapp",
        chatroom_external_id=phone_number_id,
        contact_id=contact_id,
        contact_name=contact_name,
        text=str(text),
        metadata={"raw": payload},
    )


@router.get("/webhooks/whatsapp/{phone_number_id}")
def verify_whatsapp_for_chatroom(
    phone_number_id: str,
    mode: str = Query(default="", alias="hub.mode"),
    challenge: str = Query(default="", alias="hub.challenge"),
    verify_token: str = Query(default="", alias="hub.verify_token"),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    chatroom = (
        db.query(OmniChatroom)
        .filter(
            OmniChatroom.channel == "whatsapp",
            OmniChatroom.external_room_id == phone_number_id,
        )
        .one_or_none()
    )
    if chatroom is None:
        raise HTTPException(status_code=404, detail="WhatsApp chatroom not found for this phone_number_id.")

    integration = get_chatroom_integration(db, chatroom.id)
    expected_token = str(integration.get("webhook_verify_token") or "")
    if not expected_token:
        raise HTTPException(status_code=400, detail="Webhook verify token not configured for this chatroom.")

    if mode == "subscribe" and verify_token == expected_token:
        return PlainTextResponse(content=challenge)
    raise HTTPException(status_code=403, detail="Verification failed.")


@router.post("/webhooks/whatsapp/{phone_number_id}", response_model=OmniInboundResult)
def omni_whatsapp_webhook(
    phone_number_id: str,
    payload: dict,
    db: Session = Depends(get_db),
) -> OmniInboundResult:
    incoming = _incoming_from_whatsapp_payload(phone_number_id, payload)
    return OmniEngine(db).process_incoming(incoming)


@router.post("/webhooks/{channel}", response_model=OmniInboundResult)
def omni_webhook(channel: str, payload: dict, db: Session = Depends(get_db)) -> OmniInboundResult:
    normalized_channel = channel.strip().lower()
    if normalized_channel not in VALID_CHANNELS:
        raise HTTPException(status_code=400, detail="Unsupported channel.")
    incoming = _incoming_from_payload(normalized_channel, payload)
    return OmniEngine(db).process_incoming(incoming)


@router.post("/simulate", response_model=OmniInboundResult)
def omni_simulate(payload: OmniIncomingMessage, db: Session = Depends(get_db)) -> OmniInboundResult:
    return OmniEngine(db).process_incoming(payload)
