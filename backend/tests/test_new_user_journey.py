from fastapi.testclient import TestClient

from app.main import app
from app import access


def test_new_user_can_register_test_unlock_and_continue():
    client = TestClient(app)
    email = "new-pilot-user@example.com"

    requested = client.post("/auth/otp/request", json={"email": email})
    assert requested.status_code == 200
    verified = client.post("/auth/otp/verify", json={"email": email, "code": "123456"})
    assert verified.status_code == 200
    token = verified.json()["session_token"]
    headers = {"X-IAQ-Session": token}

    session_response = client.post("/assessments/iaq-cognitive/sessions", json={"mode": "complete"}, headers=headers)
    assert session_response.status_code == 200
    session_id = session_response.json()["id"]
    assert session_response.json()["question_count"] == 40

    started = client.post(f"/sessions/{session_id}/start", headers=headers)
    assert started.status_code == 200

    for presented_order in range(40):
        item_response = client.get(f"/sessions/{session_id}/next-item", headers=headers)
        assert item_response.status_code == 200
        item = item_response.json()
        assert "answer" not in item
        assert "answer_index" not in item
        response_payload = {"item_id": item["id"], "presented_order": presented_order, "response_time_ms": 900}
        if item.get("type") == "memory":
            assert client.post(f"/sessions/{session_id}/items/{item['id']}/begin-recall", headers=headers).status_code == 200
            memory_type = item.get("memory_response_type") or "ordered_sequence"
            memory_length = item.get("memory_input_length") or 4
            response_payload["response_type"] = memory_type
            response_payload["response"] = list(range(memory_length)) if memory_type == "cell_set" else [0] * memory_length
        else:
            response_payload["answer_index"] = 0
        answer_response = client.post(
            f"/sessions/{session_id}/responses",
            json=response_payload,
            headers={**headers, "Idempotency-Key": f"new-user:{session_id}:{presented_order}"},
        )
        assert answer_response.status_code == 200, f"order {presented_order} item {item['id']} payload {response_payload}: {answer_response.text}"

    submitted = client.post(f"/sessions/{session_id}/submit", headers=headers)
    assert submitted.status_code == 200
    result = submitted.json()
    result_id = result["id"]
    assert result["full_access"] is False
    assert result["domain_scores"] == {}
    assert "answered_count" not in result

    # The free attempt is one-time per account, and the result is discoverable
    # without relying on a browser-local result pointer.
    repeat = client.post("/assessments/iaq-cognitive/sessions", json={"mode": "complete"}, headers=headers)
    assert repeat.status_code == 409
    history = client.get("/results", headers=headers)
    assert history.status_code == 200
    assert [item["id"] for item in history.json()["results"]] == [result_id]

    order_response = client.post("/orders", json={"product_id": "iaq-complete", "result_id": result_id}, headers=headers)
    assert order_response.status_code == 200
    order_id = order_response.json()["id"]
    checkout = client.post(f"/orders/{order_id}/checkout", headers=headers)
    assert checkout.status_code == 200
    settled = client.post(f"/payments/mock/{order_id}/settle", headers=headers)
    assert settled.status_code == 200
    assert settled.json()["entitlement_created"] is True

    unlocked = client.get(f"/results/{result_id}", headers=headers)
    assert unlocked.status_code == 200
    assert unlocked.json()["full_access"] is True
    assert len(unlocked.json()["domain_scores"]) == 6

    interests = client.post(
        "/questionnaires/compass-v1/responses",
        json={"responses": {"R": 70, "I": 90, "A": 60, "S": 45, "E": 50, "C": 80}, "result_id": result_id},
        headers=headers,
    )
    assert interests.status_code == 200
    directions = client.post("/ai/directions", json={"result_id": result_id}, headers=headers)
    assert directions.status_code == 200
    assert directions.json()["directions"]

    certificate = client.post("/certificates", json={"result_id": result_id}, headers=headers)
    assert certificate.status_code == 200
    assert certificate.json()["title"].startswith("IAQ Cognitive Profile")
    assert "composite" not in certificate.json()

    # Keep the test repeatable without leaving a reusable fake account behind.
    user = access.user_for_identifier(email)
    access.USERS.pop(user["id"], None)
    access.INTEREST_ATTEMPTS.pop(user["id"], None)
    for key in [key for key, value in access.ENTITLEMENTS.items() if value["owner_id"] == user["id"]]:
        access.ENTITLEMENTS.pop(key, None)
