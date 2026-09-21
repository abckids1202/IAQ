from collections import Counter

from app.main import FeedbackCreate, ITEMS, create_feedback, create_randomized_form, public_item, question_bank_summary


def test_bank_has_five_item_domains_and_balanced_40_question_forms():
    counts = Counter(item["domain"] for item in ITEMS.values())
    assert len(ITEMS) >= 40
    assert "working_memory" not in counts
    assert "processing_speed" not in counts
    assert all(counts[domain] >= 8 for domain in {
        "abstract_reasoning", "deductive_logic", "numerical_reasoning",
        "verbal_reasoning", "visual_spatial_reasoning",
    })
    for mode in ("complete", "quick", "practice"):
        form = create_randomized_form(mode)
        assert len(form) == 40
        assert set(Counter(ITEMS[item_id]["domain"] for item_id in form).values()) == {8}


def test_student_item_payload_is_allowlisted():
    item = public_item(next(iter(ITEMS.values())))
    assert "answer" not in item
    assert "explanation" not in item
    assert "generation_parameters" not in item
    assert "provenance" not in item
    assert set(item) <= {"id", "domain", "type", "prompt", "options", "helper", "visual", "render_type", "presentation_mode"}


def test_summary_exposes_review_readiness_without_memory_or_speed_bank():
    summary = question_bank_summary()
    assert "working_memory" not in summary["counts"]
    assert "processing_speed" not in summary["counts"]
    assert summary["form_sizes"]["complete"] == 40
    assert "review_gate" in summary


def test_feedback_is_accepted_without_exposing_message_in_response():
    result = create_feedback(FeedbackCreate(message="The results page is clear.", page="/results"))
    assert result["accepted"] is True
    assert "message" not in result


def test_question_bank_has_balanced_complete_forms_and_hides_keys():
    form = create_randomized_form("complete")
    assert len(form) == 40
    assert len(set(form)) == 40
    assert set(Counter(ITEMS[item_id]["domain"] for item_id in form).values()) == {8}
    families_by_domain = {}
    for item_id in form:
        item = ITEMS[item_id]
        families_by_domain.setdefault(item["domain"], []).append(item.get("item_family_id", item_id))
    assert all(len(families) == len(set(families)) for families in families_by_domain.values())
    item = public_item(ITEMS[form[0]])
    assert "answer" not in item
    assert "explanation" not in item


def test_question_bank_randomizes_between_sessions():
    forms = {tuple(create_randomized_form("complete")) for _ in range(5)}
    assert len(forms) > 1
