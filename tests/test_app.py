from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(tmp_path) -> TestClient:
    db_file = tmp_path / "test.db"
    app = create_app(database_url=f"sqlite:///{db_file}")
    return TestClient(app)


def _enable_ai_always_on(client: TestClient) -> None:
    response = client.put("/admin/ai/status", json={"enabled": True})
    assert response.status_code == 200
    response = client.put(
        "/admin/ai/schedule",
        json={
            "schedule_start": "00:00",
            "schedule_end": "00:00",
            "timezone": "Asia/Hong_Kong",
        },
    )
    assert response.status_code == 200


def test_ai_auto_reply(client: TestClient) -> None:
    _enable_ai_always_on(client)
    response = client.post(
        "/webhooks/simulate",
        json={
            "channel": "whatsapp",
            "phone": "+85261111111",
            "name": "Chris",
            "text": "想知按揭資訊",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "ai_replied"
    assert data["ai_replied"] is True
    assert "按揭" in data["reply_text"]


def test_handover_and_report(client: TestClient) -> None:
    _enable_ai_always_on(client)
    response = client.post(
        "/webhooks/simulate",
        json={
            "channel": "whatsapp",
            "phone": "+85262222222",
            "text": "我想同真人傾，想即時報價",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["handover"] is True
    assert data["assigned_agent"] is not None

    reports = client.get("/admin/reports/+85262222222")
    assert reports.status_code == 200
    assert len(reports.json()) >= 1


def test_ai_pause_switch(client: TestClient) -> None:
    response = client.post("/admin/ai/pause")
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    reply = client.post(
        "/webhooks/simulate",
        json={
            "channel": "whatsapp",
            "phone": "+85263333333",
            "text": "想了解樓盤資料",
        },
    )
    assert reply.status_code == 200
    assert reply.json()["mode"] == "human_only"
    assert reply.json()["ai_replied"] is False


def test_auto_tags_and_lead_filtering(client: TestClient) -> None:
    _enable_ai_always_on(client)
    phone = "+85264444444"
    response = client.post(
        "/webhooks/simulate",
        json={
            "channel": "whatsapp",
            "phone": phone,
            "text": "我想租樓，budget 20000",
        },
    )
    assert response.status_code == 200
    detail = client.get(f"/crm/customers/{phone}")
    assert detail.status_code == 200
    tags = detail.json()["tags"]
    assert "want_rent" in tags
    assert "budget_20000_20000" in tags

    leads = client.get("/crm/leads", params={"tag": "want_rent"})
    assert leads.status_code == 200
    phones = [row["phone"] for row in leads.json()]
    assert phone in phones


def test_booking_api(client: TestClient) -> None:
    scheduled_at = datetime.now(timezone.utc) + timedelta(days=1)
    response = client.post(
        "/crm/bookings",
        json={
            "phone": "+85265555555",
            "scheduled_at": scheduled_at.isoformat(),
            "notes": "prefer morning",
            "channel": "whatsapp",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["customer_phone"] == "+85265555555"
