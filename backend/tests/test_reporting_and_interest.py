from starlette.requests import Request
from app import access

from app.main import (
    CertificateCreate,
    InterestResponseCreate,
    create_certificate,
    questionnaire_responses,
    start_session,
    submit_response,
    submit_session,
    create_session,
    SessionCreate,
    ResponseCreate,
    ITEMS,
    begin_memory_recall,
)


def local_request() -> Request:
    return Request({"type": "http", "headers": []})


def test_interest_checkin_is_persisted_for_the_current_user():
    session = create_session("iaq-cognitive", SessionCreate())
    start_session(session["id"])
    report = submit_session(session["id"])
    order = access.create_order("demo-student", "iaq-complete", result_id=report["id"])
    access.fulfill_order(order["id"], "test_fixture")
    result = questionnaire_responses("compass-v1", InterestResponseCreate(result_id=report["id"], responses={"I": 90, "A": 80, "C": 70, "R": 20, "S": 10, "E": 30}), local_request())
    assert result["code"] == "IAC"
    assert result["data_origin"] == "REAL_PILOT"


def test_certificate_is_private_but_verifiable_without_exposing_a_score():
    session = create_session("iaq-cognitive", SessionCreate())
    first = start_session(session["id"])["next_item"]
    item = ITEMS[first["id"]]
    if item.get("type") == "memory":
        begin_memory_recall(session["id"], first["id"])
    if item.get("memory_response_type") == "ordered_sequence":
        memory_response = [int(value) for value in item["memory_stimulus"] if str(value).isdigit()]
        payload = ResponseCreate(item_id=first["id"], response_type="ordered_sequence", response=memory_response, response_time_ms=4200, presented_order=0)
    elif item.get("memory_response_type") == "cell_set":
        payload = ResponseCreate(item_id=first["id"], response_type="cell_set", response=item["memory_answer"], response_time_ms=4200, presented_order=0)
    else:
        payload = ResponseCreate(item_id=first["id"], answer_index=item["options"].index(item["answer"]), response_time_ms=4200, presented_order=0)
    submit_response(session["id"], payload, f"certificate:{session['id']}:0")
    result = submit_session(session["id"])
    order = access.create_order("demo-student", "iaq-complete", result_id=result["id"])
    access.fulfill_order(order["id"], "test_fixture")
    certificate = create_certificate(CertificateCreate(result_id=result["id"]), local_request())
    assert certificate["status"] == "issued"
    assert certificate["certificate_identifier"].startswith("IAQ-")
    assert "composite" not in certificate
