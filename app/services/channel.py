from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import Settings


class ChannelGateway:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send_text(
        self,
        channel: str,
        to_phone: str,
        text: str,
        provider_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        provider_config = provider_config or {}
        api_url = provider_config.get("api_url") or self.settings.whatsapp_api_url
        access_token = provider_config.get("access_token") or self.settings.whatsapp_access_token
        phone_number_id = provider_config.get("phone_number_id")

        if channel == "whatsapp" and not api_url and phone_number_id:
            api_url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"

        if channel == "whatsapp" and api_url and access_token:
            payload = {"to": to_phone, "type": "text", "text": {"body": text}}
            try:
                response = httpx.post(
                    api_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=8.0,
                )
                response.raise_for_status()
                return {"status": "sent", "provider": "whatsapp_api", "response": response.json()}
            except Exception as exc:  # pragma: no cover - network dependency
                return {"status": "failed", "provider": "whatsapp_api", "error": str(exc)}

        # Simulated send channel for local/dev mode.
        return {
            "status": "sent",
            "provider": "simulated",
            "channel": channel,
            "to": to_phone,
            "message_id": f"sim-{int(datetime.now(timezone.utc).timestamp())}",
        }

    def send_property_cards(self, channel: str, to_phone: str, cards: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "status": "sent",
            "provider": "simulated",
            "channel": channel,
            "to": to_phone,
            "cards": cards,
        }
