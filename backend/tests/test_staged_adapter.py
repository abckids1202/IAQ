from app import external_data, staged_assessment
from app.main import public_item


def test_visual_staged_item_uses_the_image_and_label_only_choices():
    candidate = external_data.preview_items(limit=1, domain="abstract_reasoning")[0]
    item = staged_assessment._choice_item(candidate)
    payload = public_item(item)

    assert item["image_url"]
    assert item["options"] == ["A", "B", "C", "D"]
    assert item["answer"] in item["options"]
    assert payload["options"] == ["A", "B", "C", "D"]
    assert "answer" not in payload
    assert "answer_index" not in payload
    assert "rule" not in payload


def test_staged_memory_item_preserves_the_recall_protocol_without_an_answer_key():
    candidate = external_data.preview_items(limit=1, domain="working_memory")[0]
    item = staged_assessment._memory_item(candidate)
    payload = public_item(item)

    assert item["memory_response_type"] in {"ordered_sequence", "cell_set"}
    assert isinstance(item["memory_stimulus"], dict)
    assert item["options"] == []
    assert payload["visual"] == item["memory_stimulus"]
    assert "answer" not in payload
    assert "answer_index" not in payload
    assert "rule" not in payload


def test_staged_verbal_item_separates_passage_from_the_question():
    candidate = external_data.preview_items(limit=1, domain="verbal_reasoning")[0]
    item = staged_assessment._choice_item(candidate)

    assert item["prompt"] == candidate["question"]
    assert item["helper"] == candidate["context"]
    assert len(item["options"]) == 4
