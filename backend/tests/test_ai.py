import pytest

from app import ai


def test_ai_layer_is_disabled_without_a_server_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("IAQ_AI_ENABLED", raising=False)
    status = ai.public_status()
    assert status["enabled"] is False
    assert status["configured"] is False
    with pytest.raises(ai.AIUnavailable):
        ai.interpret_result({"domain_scores": {}}, {})


def test_ai_json_parser_accepts_fenced_json():
    assert ai._parse_json("```json\n{\"directions\": []}\n```") == {"directions": []}


def test_ai_interpretation_is_aggregate_and_validated(monkeypatch):
    class FakeResponse:
        output_text = '{"what_stands_out":["Abstract reasoning was comparatively stronger."],"where_more_evidence":["Verbal reasoning needs more answered items."],"timing_context":"Timing is context, not a verdict.","next_step":"Try one short logic activity."}'
        _request_id = "req_test"

    class FakeResponses:
        def create(self, **kwargs):
            assert kwargs["store"] is False
            assert '"answer"' not in kwargs["input"]
            return FakeResponse()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai, "_client", lambda: (FakeClient(), ai.get_config()))
    result, metadata = ai.interpret_result({"composite": 74, "domain_scores": {"abstract_reasoning": 80}, "domain_metrics": {}, "quality": {}, "confidence": "moderate", "answered_count": 4, "question_count": 56}, {"abstract_reasoning": "Abstract reasoning"})
    assert result["what_stands_out"]
    assert metadata["request_id"] == "req_test"
