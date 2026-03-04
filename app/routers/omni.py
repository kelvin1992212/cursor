from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OmniChatroom, OmniMessage, OmniThread
from app.schemas_omni import (
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
    engine.gateway.send_text(thread.chatroom.channel, thread.contact.external_user_id, payload.content)
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
