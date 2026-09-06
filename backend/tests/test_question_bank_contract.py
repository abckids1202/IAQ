from collections import Counter

from app.main import FeedbackCreate, ITEMS, create_feedback, create_randomized_form, public_item, question_bank_summary


def test_bank_has_120_candidates_per_domain_and_balanced_complete_forms():
    counts = Counter(item["domain"] for item in ITEMS.values())
    assert len(ITEMS) == 840
    assert set(counts.values()) == {120}
    form = create_randomized_form("complete")
    assert len(form) == 56
    assert set(Counter(ITEMS[item_id]["domain"] for item_id in form).values()) == {8}


def test_student_item_payload_is_allowlisted():
    item = public_item(next(iter(ITEMS.values())))
    assert "answer" not in item
    assert "explanation" not in item
    assert "generation_parameters" not in item
    assert "provenance" not in item
    assert set(item) <= {"id", "domain", "type", "prompt", "options", "helper", "visual", "render_type"}


def test_summary_exposes_review_readiness_without_answer_keys():
    summary = question_bank_summary()
    assert summary["counts"]["working_memory"] == 120
    assert summary["origin_counts"]["ORIGINAL_GENERATED"] == 700
    assert "review_gate" in summary


def test_feedback_is_accepted_without_exposing_message_in_response():
    result = create_feedback(FeedbackCreate(message="The results page is clear.", page="/results"))
    assert result["accepted"] is True
    assert "message" not in result
