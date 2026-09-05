from app.domain import classify_session_quality, major_fit, recommendation_confidence, score_domains, score_riasec


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
