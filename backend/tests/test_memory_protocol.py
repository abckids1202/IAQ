from app.main import ITEMS, public_item, runtime_readiness


def test_memory_items_hide_the_stimulus_from_the_prompt_but_keep_a_transient_visual():
    memory_items = [item for item in ITEMS.values() if item["domain"] == "working_memory"]
    assert len(memory_items) == 120
    for item in memory_items:
        payload = public_item(item)
        assert "answer" not in payload
        assert "answer_index" not in payload
        assert "memory_stimulus" not in payload
        assert payload.get("visual")
        assert str(item["answer"]) not in payload["prompt"]


def test_development_preflight_does_not_claim_production_ready():
    readiness = runtime_readiness()
    assert readiness["environment"] == "development"
    assert readiness["status"] == "ready"
    assert readiness["student_sessions"] == "development_pilot_bank"


def test_production_preflight_blocks_unconfigured_release(monkeypatch):
    monkeypatch.setenv("IAQ_ENV", "production")
    monkeypatch.setenv("IAQ_REQUIRE_REVIEWED_ITEMS", "true")
    monkeypatch.setenv("IAQ_ACCESS_STORE", "memory")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_JWKS_URL", raising=False)
    monkeypatch.delenv("MIDTRANS_SERVER_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("APP_BASE_URL", raising=False)

    readiness = runtime_readiness()

    assert readiness["status"] == "needs_configuration"
    assert {"database", "commerce_persistence", "supabase_auth", "review_gate", "payments", "email", "app_base_url"}.issubset(set(readiness["blockers"]))


def test_production_preflight_does_not_trust_access_store_flag(monkeypatch):
    monkeypatch.setenv("IAQ_ENV", "production")
    monkeypatch.setenv("IAQ_ACCESS_STORE", "postgres")
    monkeypatch.setenv("IAQ_DATABASE_URL", "postgresql+psycopg://configured.example/iaq")
    readiness = runtime_readiness()
    assert readiness["checks"]["commerce_persistence"] is False
    assert "commerce_persistence" in readiness["blockers"]
