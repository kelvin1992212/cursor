from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas import IncomingMessage, WebhookProcessResponse
from app.services.lead_engine import LeadEngine

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _from_simple_payload(channel: str, payload: dict[str, Any]) -> IncomingMessage | None:
    text = payload.get("text") or payload.get("message")
    phone = payload.get("phone")
    if phone and text:
        return IncomingMessage(
            channel=channel,
            phone=str(phone),
            name=payload.get("name"),
            text=str(text),
            metadata=payload.get("metadata", {}),
        )
    return None


def _parse_whatsapp_payload(payload: dict[str, Any]) -> IncomingMessage:
    simple = _from_simple_payload("whatsapp", payload)
    if simple:
        return simple

    try:
        value = payload["entry"][0]["changes"][0]["value"]
        message = value["messages"][0]
        contacts = value.get("contacts") or []
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid WhatsApp payload: {exc}") from exc

    phone = str(message.get("from", "")).strip()
    text = (
        message.get("text", {}).get("body")
        or message.get("button", {}).get("text")
        or message.get("interactive", {}).get("button_reply", {}).get("title")
    )
    if not phone or not text:
        raise HTTPException(status_code=400, detail="Unsupported WhatsApp message format.")

    name: str | None = None
    if contacts:
        name = contacts[0].get("profile", {}).get("name")

    return IncomingMessage(
        channel="whatsapp",
        phone=phone,
        name=name,
        text=text,
        metadata={"raw": payload},
    )


def _parse_wechat_payload(payload: dict[str, Any]) -> IncomingMessage:
    simple = _from_simple_payload("wechat", payload)
    if simple:
        return simple

    phone = payload.get("from_user") or payload.get("phone")
    text = payload.get("content") or payload.get("text")
    if not phone or not text:
        raise HTTPException(status_code=400, detail="Invalid WeChat payload.")
    return IncomingMessage(
        channel="wechat",
        phone=str(phone),
        name=payload.get("name"),
        text=str(text),
        metadata={"raw": payload},
    )


@router.get("/whatsapp")
def verify_whatsapp(
    mode: str = Query(default="", alias="hub.mode"),
    challenge: str = Query(default="", alias="hub.challenge"),
    verify_token: str = Query(default="", alias="hub.verify_token"),
) -> PlainTextResponse:
    settings = get_settings()
    if mode == "subscribe" and verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(content=challenge)
    raise HTTPException(status_code=403, detail="Verification failed.")


@router.post("/whatsapp", response_model=WebhookProcessResponse)
def incoming_whatsapp(payload: dict[str, Any], db: Session = Depends(get_db)) -> WebhookProcessResponse:
    incoming = _parse_whatsapp_payload(payload)
    return LeadEngine(db).process_incoming(incoming)


@router.post("/wechat", response_model=WebhookProcessResponse)
def incoming_wechat(payload: dict[str, Any], db: Session = Depends(get_db)) -> WebhookProcessResponse:
    incoming = _parse_wechat_payload(payload)
    return LeadEngine(db).process_incoming(incoming)


@router.post("/simulate", response_model=WebhookProcessResponse)
def incoming_simulated(data: IncomingMessage, db: Session = Depends(get_db)) -> WebhookProcessResponse:
    return LeadEngine(db).process_incoming(data)
