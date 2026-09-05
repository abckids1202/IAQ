from collections import Counter

from app.domain import classify_session_quality, major_fit, recommendation_confidence, score_domains, score_riasec
from app.main import ITEMS, create_randomized_form, public_item


def test_domain_scoring_is_versioned_and_provisional():
    result = score_domains([{"item_id": "one", "answer": "A", "response_time_ms": 4000}], {"one": "abstract_reasoning"}, {"one": "A"})
    assert result.score_version == "SCORING-V1"
    assert result.domain_scores["abstract_reasoning"] == 95
    assert result.confidence == "low"


def test_riasec_keeps_top_three_code():
    result = score_riasec({"R": 20, "I": 90, "A": 80, "S": 30, "E": 40, "C": 70})
    assert result["code"] == "IAC"


def test_fit_and_confidence_are_bounded():
    result = major_fit({"abstract_reasoning": 80}, {"I": 90, "A": 70, "C": 60}, 65, {"abstract_reasoning": 1})
    assert 0 <= result["fit"] <= 100
    assert 0 <= recommendation_confidence(7, .34, 5, 24) <= 100


def test_quality_flags_rapid_and_interruptions():
    result = classify_session_quality([500, 600, 5000], interruptions=1)
    assert result["status"] == "low"
    assert "rapid_guessing_possible" in result["warnings"]
    assert "interruptions" in result["warnings"]


def test_question_bank_has_balanced_complete_forms_and_hides_keys():
    form = create_randomized_form("complete")
    assert len(ITEMS) == 140
    assert len(form) == 56
    assert len(set(form)) == 56
    assert set(Counter(ITEMS[item_id]["domain"] for item_id in form).values()) == {8}
    item = public_item(ITEMS[form[0]])
    assert "answer" not in item
    assert "explanation" not in item


def test_question_bank_randomizes_between_sessions():
    forms = {tuple(create_randomized_form("complete")) for _ in range(5)}
    assert len(forms) > 1
