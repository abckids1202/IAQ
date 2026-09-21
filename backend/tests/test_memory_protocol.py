from fastapi.testclient import TestClient

from app.main import ITEMS, app, public_item, runtime_readiness


def test_working_memory_is_not_part_of_the_scored_product():
    domains = {item["domain"] for item in ITEMS.values()}
    assert "working_memory" not in domains
    assert "processing_speed" not in domains
    assert all(item["domain"] != "working_memory" for item in ITEMS.values())


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


def test_production_readiness_probe_fails_closed(monkeypatch):
    monkeypatch.setenv("IAQ_ENV", "production")
    monkeypatch.setenv("IAQ_REQUIRE_REVIEWED_ITEMS", "true")
    monkeypatch.setenv("IAQ_ACCESS_STORE", "memory")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_JWKS_URL", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("APP_BASE_URL", raising=False)

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "needs_configuration"
