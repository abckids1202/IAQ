from collections import Counter
from datetime import datetime, timedelta, timezone
import pytest

from app.domain import DOMAINS, classify_session_quality, major_fit, recommendation_confidence, score_domains, score_riasec
from app.main import DURATION_SECONDS, ITEMS, SESSIONS, SessionCreate, ResponseCreate, create_randomized_form, create_session, get_result, public_item, start_session, submit_response, submit_session


def test_domain_scoring_is_versioned_and_provisional():
    result = score_domains([{"item_id": "one", "answer": "A", "response_time_ms": 4000}], {"one": "abstract_reasoning"}, {"one": "A"})
    assert result.score_version == "IAQ-PROVISIONAL-ACCURACY-1"
    assert result.score_kind == "provisional_domain_signal"
    assert result.domain_scores["abstract_reasoning"] is None
    assert result.domain_metrics["abstract_reasoning"]["interpretation_eligible"] is False
    assert result.confidence == "low"


def test_riasec_keeps_top_three_code():
    result = score_riasec({"R": 20, "I": 90, "A": 80, "S": 30, "E": 40, "C": 70})
    assert result["code"] == "IAC"


def test_fit_and_confidence_are_bounded():
    result = major_fit({"abstract_reasoning": 80}, {"I": 90, "A": 70, "C": 60}, 65, {"abstract_reasoning": 1})
    assert 0 <= result["fit"] <= 100
    assert 0 <= recommendation_confidence(7, .34, 5, 24) <= 100


def test_provisional_signal_reports_observed_accuracy_without_synthetic_floor():
    result = score_domains(
        [
            {"item_id": "one", "answer": "wrong", "response_time_ms": 4000},
            {"item_id": "two", "answer": "wrong", "response_time_ms": 4000},
            {"item_id": "three", "answer": "wrong", "response_time_ms": 4000},
            {"item_id": "four", "answer": "wrong", "response_time_ms": 4000},
        ],
        {"one": "abstract_reasoning", "two": "abstract_reasoning", "three": "abstract_reasoning", "four": "abstract_reasoning"},
        {"one": "right", "two": "right", "three": "right", "four": "right"},
    )
    assert result.domain_scores["abstract_reasoning"] == 0
    assert result.composite is None
    assert result.iq_score is None


def test_experimental_iq_score_requires_complete_profile_and_uses_reference_transform():
    item_domains = {f"{domain}-{index}": domain for domain in DOMAINS for index in range(4)}
    item_keys = {item_id: "right" for item_id in item_domains}
    responses = [{"item_id": item_id, "answer": "right", "response_time_ms": 4000} for item_id in item_domains]

    result = score_domains(responses, item_domains, item_keys)

    assert result.composite == 100
    assert result.iq_score == 130
    assert result.iq_score_kind == "experimental_iq_style_estimate"
    assert result.iq_score_scale == "100_mean_15_sd_reference_only"


def test_quality_flags_rapid_and_interruptions():
    result = classify_session_quality([500, 600, 5000], interruptions=1)
    assert result["status"] == "low"
    assert "rapid_guessing_possible" in result["warnings"]
    assert "interruptions" in result["warnings"]


def test_question_bank_has_balanced_complete_forms_and_hides_keys():
    form = create_randomized_form("complete")
    assert len(ITEMS) == 840
    assert len(form) == 56
    assert len(set(form)) == 56
    assert set(Counter(ITEMS[item_id]["domain"] for item_id in form).values()) == {8}
    families_by_domain = {}
    for item_id in form:
        item = ITEMS[item_id]
        families_by_domain.setdefault(item["domain"], []).append(item["item_family_id"])
    assert all(len(families) == len(set(families)) for families in families_by_domain.values())
    item = public_item(ITEMS[form[0]])
    assert "answer" not in item
    assert "explanation" not in item


def test_question_bank_randomizes_between_sessions():
    forms = {tuple(create_randomized_form("complete")) for _ in range(5)}
    assert len(forms) > 1


def test_question_bank_has_reviewable_generation_metadata():
    generated = [item for item in ITEMS.values() if item.get("data_origin") == "ORIGINAL_GENERATED"]
    assert len(generated) == 700
    assert set(Counter(item["domain"] for item in generated).values()) == {100}
    assert len({item["prompt"] for item in generated}) == len(generated)
    assert all(item["status"] == "PILOT" for item in generated)
    assert all(item["options"].count(item["answer"]) == 1 for item in generated)
    assert all(item["generation_run_id"] for item in generated)
    assert all(item["difficulty_estimate"] is None for item in generated)


def test_session_has_timed_contract_and_persists_real_metrics():
    session = create_session("iaq-cognitive", SessionCreate())
    assert session["duration_seconds"] == DURATION_SECONDS
    assert session["question_count"] == 56
    started = start_session(session["id"])
    first = started["next_item"]
    submit_response(session["id"], ResponseCreate(item_id=first["id"], answer=ITEMS[first["id"]]["answer"], response_time_ms=4200, presented_order=0), f"test:{session['id']}:0")
    result = submit_session(session["id"])
    assert result["answered_count"] == 1
    assert result["domain_metrics"][ITEMS[first["id"]]["domain"]]["correct"] == 1
    assert get_result(result["id"])["composite"] == result["composite"]


def test_expired_session_cannot_start_or_accept_an_answer():
    session = create_session("iaq-cognitive", SessionCreate())
    SESSIONS[session["id"]]["deadline_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with pytest.raises(Exception):
        start_session(session["id"])
    assert SESSIONS[session["id"]]["status"] == "timed_out"


def test_presented_order_is_bound_to_the_randomized_form():
    session = create_session("iaq-cognitive", SessionCreate())
    first = start_session(session["id"])["next_item"]
    with pytest.raises(Exception):
        submit_response(session["id"], ResponseCreate(item_id=first["id"], answer=ITEMS[first["id"]]["answer"], response_time_ms=4200, presented_order=1), f"order:{session['id']}")


def test_minor_practice_is_ephemeral_and_unscored():
    session = create_session("iaq-cognitive", SessionCreate(mode="practice", age_band="15-17"))
    first = start_session(session["id"])["next_item"]
    submit_response(session["id"], ResponseCreate(item_id=first["id"], answer=ITEMS[first["id"]]["answer"], response_time_ms=4200, presented_order=0), f"practice:{session['id']}")
    result = submit_session(session["id"])
    assert result["practice"] is True
    assert session["id"] not in SESSIONS
