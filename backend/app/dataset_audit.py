"""Deterministic audit for the quarantined assessment catalog.

This checks machine-verifiable integrity only. It does not claim an item is
psychometrically good or licensed for deployment; those remain human review
and release gates.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from . import external_data


def audit_catalog() -> Dict[str, Any]:
    seen_ids: set[str] = set()
    errors: List[Dict[str, Any]] = []
    counts: Counter[str] = Counter()
    families: Counter[str] = Counter()
    total = 0
    for item in external_data.iter_external_items(include_verbal=True, language="en"):
        total += 1
        item_id = str(item["id"])
        counts[item["domain"]] += 1
        families[f"{item['domain']}:{item['item_family_id']}"] += 1
        if item_id in seen_ids:
            errors.append({"id": item_id, "code": "duplicate_id"})
        seen_ids.add(item_id)
        options = item.get("options")
        answer_index = item.get("answer_index")
        if item.get("type") == "memory" and isinstance(item.get("answer"), list):
            stimulus = item.get("stimulus")
            sequence = stimulus.get("sequence") if isinstance(stimulus, dict) else None
            filled_cells = stimulus.get("filled_cells") if isinstance(stimulus, dict) else None
            memory_ok = isinstance(sequence, list) and len(sequence) == len(item["answer"])
            memory_ok = memory_ok or isinstance(filled_cells, list) and set(filled_cells) == set(item["answer"])
            if not memory_ok:
                errors.append({"id": item_id, "code": "memory_protocol_mismatch"})
        elif not isinstance(options, list) or len(options) != 4:
            errors.append({"id": item_id, "code": "options_not_four"})
        elif not isinstance(answer_index, int) or not 0 <= answer_index < len(options):
            errors.append({"id": item_id, "code": "answer_index_invalid"})
        elif item.get("answer") is not None and options[answer_index] != item["answer"]:
            errors.append({"id": item_id, "code": "answer_index_mismatch"})
        if not item.get("prompt"):
            errors.append({"id": item_id, "code": "empty_prompt"})
        if not item.get("source_file") or not item.get("provenance"):
            errors.append({"id": item_id, "code": "missing_provenance"})
        if item.get("lifecycle_status") != "DRAFT" or item.get("production_eligible") is not False:
            errors.append({"id": item_id, "code": "release_gate_bypass"})
        if item.get("image_path") and not item.get("asset_exists"):
            errors.append({"id": item_id, "code": "missing_asset"})
    return {
        "total": total,
        "by_domain": dict(counts),
        "unique_ids": len(seen_ids),
        "unique_families": len(families),
        "errors": errors[:200],
        "error_count": len(errors),
        "machine_integrity_passed": not errors,
        "human_review_required": True,
        "student_sessions_use": False,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(audit_catalog(), indent=2))
