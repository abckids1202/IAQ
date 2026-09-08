from app import external_data
from app.dataset_audit import audit_catalog


def test_staged_dataset_inventory_is_available_and_not_production_eligible():
    summary = external_data.dataset_summary()

    assert summary["available"] is True
    assert summary["student_sessions_use"] is False
    assert summary["totals"]["by_domain"]["abstract_reasoning"] == 2000
    assert summary["totals"]["by_domain"]["deductive_logic"] == 2000
    assert summary["totals"]["by_domain"]["numerical_reasoning"] == 2000
    assert summary["totals"]["by_domain"]["visual_spatial_reasoning"] == 2000
    assert summary["totals"]["by_domain"]["working_memory"] == 2000
    assert summary["totals"]["by_domain"]["verbal_reasoning"] == 24386
    assert summary["totals"]["missing_assets"] == 0


def test_external_preview_preserves_answer_data_for_admin_review_only():
    item = external_data.preview_items(limit=1, domain="abstract_reasoning")[0]

    assert item["id"].startswith("external:")
    assert item["review_status"] == "unreviewed"
    assert item["lifecycle_status"] == "DRAFT"
    assert item["production_eligible"] is False
    assert item["answer_index"] in {0, 1, 2, 3}
    assert item["rule"] is not None
    assert item["asset_exists"] is True
    assert external_data.resolve_asset_path("five_domains", item["asset_path"]).is_file()


def test_external_asset_resolution_rejects_path_traversal():
    assert external_data.resolve_asset_path("five_domains", "../verbal/jsonl/logiqa1_en_train.jsonl") is None


def test_external_catalog_machine_audit_passes_without_granting_release_eligibility():
    audit = audit_catalog()
    assert audit["total"] == 34386
    assert audit["unique_ids"] == audit["total"]
    assert audit["machine_integrity_passed"] is True
    assert audit["human_review_required"] is True
    assert audit["student_sessions_use"] is False
