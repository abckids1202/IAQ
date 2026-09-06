from starlette.requests import Request

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
)


def local_request() -> Request:
    return Request({"type": "http", "headers": []})


def test_interest_checkin_is_persisted_for_the_current_user():
    result = questionnaire_responses("compass-v1", InterestResponseCreate(responses={"I": 90, "A": 80, "C": 70, "R": 20, "S": 10, "E": 30}), local_request())
    assert result["code"] == "IAC"
    assert result["data_origin"] == "REAL_PILOT"


def test_certificate_is_private_but_verifiable_without_exposing_a_score():
    session = create_session("iaq-cognitive", SessionCreate())
    first = start_session(session["id"])["next_item"]
    submit_response(session["id"], ResponseCreate(item_id=first["id"], answer=ITEMS[first["id"]]["answer"], response_time_ms=4200, presented_order=0), f"certificate:{session['id']}:0")
    result = submit_session(session["id"])
    certificate = create_certificate(CertificateCreate(result_id=result["id"]), local_request())
    assert certificate["status"] == "issued"
    assert certificate["certificate_identifier"].startswith("IAQ-")
    assert "composite" not in certificate
