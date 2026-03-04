from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import Settings


class ChannelGateway:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send_text(self, channel: str, to_phone: str, text: str) -> dict[str, Any]:
        if channel == "whatsapp" and self.settings.whatsapp_api_url and self.settings.whatsapp_access_token:
            payload = {"to": to_phone, "type": "text", "text": {"body": text}}
            try:
                response = httpx.post(
                    self.settings.whatsapp_api_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self.settings.whatsapp_access_token}"},
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
