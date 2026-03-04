from fastapi.testclient import TestClient
import pytest

from app.main import create_app


@pytest.fixture()
def client(tmp_path) -> TestClient:
    db_file = tmp_path / "omni.db"
    app = create_app(database_url=f"sqlite:///{db_file}")
    return TestClient(app)


def _chatroom_by_channel(client: TestClient, channel: str) -> dict:
    rows = client.get("/omni/chatrooms").json()
    for row in rows:
        if row["channel"] == channel:
            return row
    raise AssertionError(f"chatroom not found for channel: {channel}")


def test_seeded_channels_exist(client: TestClient) -> None:
    rows = client.get("/omni/chatrooms")
    assert rows.status_code == 200
    channels = {row["channel"] for row in rows.json()}
    assert {"whatsapp", "wechat", "facebook", "instagram"}.issubset(channels)


def test_pause_is_per_chatroom(client: TestClient) -> None:
    whatsapp_room = _chatroom_by_channel(client, "whatsapp")
    instagram_room = _chatroom_by_channel(client, "instagram")

    pause = client.post(f"/omni/chatrooms/{whatsapp_room['id']}/ai/pause")
    assert pause.status_code == 200
    assert pause.json()["ai_enabled"] is False

    whatsapp_inbound = client.post(
        "/omni/simulate",
        json={
            "channel": "whatsapp",
            "chatroom_external_id": whatsapp_room["external_room_id"],
            "contact_id": "wa-user-1",
            "contact_name": "WA User",
            "text": "hello from whatsapp",
        },
    )
    assert whatsapp_inbound.status_code == 200
    assert whatsapp_inbound.json()["ai_replied"] is False

    instagram_inbound = client.post(
        "/omni/simulate",
        json={
            "channel": "instagram",
            "chatroom_external_id": instagram_room["external_room_id"],
            "contact_id": "ig-user-1",
            "contact_name": "IG User",
            "text": "hello from instagram",
        },
    )
    assert instagram_inbound.status_code == 200
    assert instagram_inbound.json()["ai_replied"] is True


def test_thread_message_flow(client: TestClient) -> None:
    wechat_room = _chatroom_by_channel(client, "wechat")

    inbound = client.post(
        "/omni/simulate",
        json={
            "channel": "wechat",
            "chatroom_external_id": wechat_room["external_room_id"],
            "contact_id": "wechat-999",
            "contact_name": "Wei",
            "text": "need support",
        },
    )
    assert inbound.status_code == 200
    thread_id = inbound.json()["thread_id"]

    threads = client.get(f"/omni/chatrooms/{wechat_room['id']}/threads")
    assert threads.status_code == 200
    assert any(row["id"] == thread_id for row in threads.json())

    before = client.get(f"/omni/threads/{thread_id}/messages")
    assert before.status_code == 200
    assert len(before.json()) >= 1

    outbound = client.post(
        f"/omni/threads/{thread_id}/messages",
        json={"content": "human agent follow-up", "sender_type": "agent"},
    )
    assert outbound.status_code == 200
    assert outbound.json()["sender_type"] == "agent"

    after = client.get(f"/omni/threads/{thread_id}/messages")
    assert after.status_code == 200
    assert after.json()[-1]["content"] == "human agent follow-up"


def test_update_chatroom_schedule(client: TestClient) -> None:
    room = _chatroom_by_channel(client, "facebook")
    update = client.put(
        f"/omni/chatrooms/{room['id']}/ai/schedule",
        json={
            "ai_schedule_start": "20:00",
            "ai_schedule_end": "09:00",
            "timezone": "Asia/Hong_Kong",
        },
    )
    assert update.status_code == 200
    body = update.json()
    assert body["ai_schedule_start"] == "20:00"
    assert body["ai_schedule_end"] == "09:00"


def test_chatroom_integration_and_whatsapp_verify(client: TestClient) -> None:
    room = _chatroom_by_channel(client, "whatsapp")

    update = client.put(
        f"/omni/chatrooms/{room['id']}/integration",
        json={
            "phone_number_id": room["external_room_id"],
            "webhook_verify_token": "wa-verify-123",
            "ai_provider": "rule_based",
        },
    )
    assert update.status_code == 200
    assert update.json()["webhook_verify_token_set"] is True

    verify = client.get(
        f"/omni/webhooks/whatsapp/{room['external_room_id']}",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "abc123",
            "hub.verify_token": "wa-verify-123",
        },
    )
    assert verify.status_code == 200
    assert verify.text == "abc123"


def test_whatsapp_payload_path_uses_phone_number_id(client: TestClient) -> None:
    room = _chatroom_by_channel(client, "whatsapp")
    client.put(
        f"/omni/chatrooms/{room['id']}/integration",
        json={"phone_number_id": room["external_room_id"], "webhook_verify_token": "wa-token"},
    )

    inbound = client.post(
        f"/omni/webhooks/whatsapp/{room['external_room_id']}",
        json={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "contacts": [{"profile": {"name": "WA Client"}}],
                                "messages": [{"from": "85260112233", "text": {"body": "hello"}}],
                            }
                        }
                    ]
                }
            ]
        },
    )
    assert inbound.status_code == 200
    body = inbound.json()
    assert body["chatroom_id"] == room["id"]
    assert body["channel"] == "whatsapp"
