from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app import access


def test_unsigned_first_visit_is_guest_not_demo_student(monkeypatch):
    monkeypatch.setenv("IAQ_ENV", "development")
    monkeypatch.setenv("IAQ_AUTH_MODE", "development")
    monkeypatch.setenv("IAQ_GUEST_ASSESSMENT_ENABLED", "true")
    client = TestClient(app)

    anonymous = client.get("/me")
    assert anonymous.status_code == 200
    assert anonymous.json()["is_guest"] is True
    assert anonymous.json()["id"] != "demo-student"

    guest_response = client.post("/auth/guest")
    assert guest_response.status_code == 200
    guest = guest_response.json()
    token = guest["session_token"]
    guest_id = guest["user"]["id"]
    headers = {"X-IAQ-Session": token}

    assert guest["user"]["is_guest"] is True
    assert guest["user"]["roles"] == ["guest"]
    assert "order.self.create" not in guest["permissions"]
    assert client.get("/me", headers=headers).json()["id"] == guest_id

    session_response = client.post(
        "/assessments/iaq-cognitive/sessions",
        json={"mode": "complete", "age_band": "18-22"},
        headers=headers,
    )
    assert session_response.status_code == 200
    assert session_response.json()["question_count"] == 56
    session_details = client.get(f"/sessions/{session_response.json()['id']}", headers=headers)
    assert session_details.status_code == 200
    assert session_details.json()["user_id"] == guest_id

    blocked_order = client.post("/orders", json={"product_id": "iaq-complete"}, headers=headers)
    assert blocked_order.status_code == 403

    email = f"guest-upgrade-{uuid4().hex[:8]}@example.com"
    identity = client.post(
        "/me/identity",
        json={"email": email, "display_name": "Guest Test User", "age_band": "18-22", "granted": True},
        headers=headers,
    )
    assert identity.status_code == 200
    assert identity.json()["session_token"]
    assert identity.json()["user"]["is_guest"] is False
    upgraded_headers = {"X-IAQ-Session": identity.json()["session_token"]}
    upgraded = client.get("/me", headers=upgraded_headers)
    assert upgraded.status_code == 200
    assert upgraded.json()["email"] == email
    assert upgraded.json()["roles"] == ["student"]

    # Keep the in-memory test provider repeatable and avoid leaving fake users.
    access.SESSIONS.pop(token, None)
    for session_token, session in list(access.SESSIONS.items()):
        if session.get("user_id") == guest_id:
            access.SESSIONS.pop(session_token, None)
    access.USERS.pop(guest_id, None)
    for entitlement_id, entitlement in list(access.ENTITLEMENTS.items()):
        if entitlement["owner_id"] == guest_id:
            access.ENTITLEMENTS.pop(entitlement_id, None)
