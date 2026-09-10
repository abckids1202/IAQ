"""Adapt the local Dataset Lab catalog to the main assessment contract.

The staged catalog is opt-in. It is useful for QA of the real visual, memory,
and verbal records, but it remains research content and must never silently
replace the reviewed bank in a production deployment.
"""
from __future__ import annotations

import json
from typing import Any, Dict
from urllib.parse import quote

from . import external_data


STAGED_DOMAINS = {
    "abstract_reasoning",
    "deductive_logic",
    "numerical_reasoning",
    "verbal_reasoning",
    "visual_spatial_reasoning",
    "working_memory",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _asset_url(candidate: Dict[str, Any]) -> str | None:
    asset_path = candidate.get("asset_path")
    if not asset_path or not candidate.get("asset_exists"):
        return None
    return f"/assessment-assets/{quote(str(asset_path), safe='/')}"


def _memory_item(candidate: Dict[str, Any]) -> Dict[str, Any]:
    source = candidate.get("source_record") or {}
    response_type = source.get("response_type")
    stimulus = source.get("stimulus") or {}
    answer = source.get("answer")
    item: Dict[str, Any] = {
        "id": candidate["id"],
        "item_family_id": candidate.get("item_family_id") or candidate["id"],
        "construct_id": candidate.get("construct_id", "working_memory"),
        "domain": "working_memory",
        "type": "memory",
        "prompt": "Recall what you studied in the correct format.",
        "options": [],
        "answer": _canonical(answer),
        "explanation": candidate.get("rule") or "Compare the recalled response with the stored sequence or cell set.",
        "memory_response_type": response_type,
        "memory_input_length": len(answer) if isinstance(answer, list) else 0,
        "memory_grid_size": stimulus.get("grid_size") if isinstance(stimulus, dict) else None,
        "memory_stimulus": stimulus,
        "image_url": _asset_url(candidate),
        "render_type": "external_image",
        "status": "DRAFT",
        "lifecycle_status": "DRAFT",
        "language": "en",
        "data_origin": candidate.get("data_origin", "IAQ_GENERATED_RESEARCH_DATA"),
        "review_required": True,
        "review_history": [],
        "content_version": candidate.get("content_version", 1),
        "provenance": candidate.get("provenance"),
    }
    return item


def _choice_item(candidate: Dict[str, Any]) -> Dict[str, Any]:
    source = candidate.get("source_record") or {}
    options = source.get("options") if isinstance(source.get("options"), list) else []
    answer_index = source.get("answer_index")
    is_visual = candidate.get("domain") in {"abstract_reasoning", "deductive_logic", "numerical_reasoning", "visual_spatial_reasoning"}
    if is_visual:
        # The supplied image is the complete visual stimulus. The main app
        # receives only presentation labels while the raw panels stay in the
        # image and the answer key remains server-side.
        safe_options = ["A", "B", "C", "D"]
        safe_answer = safe_options[answer_index] if isinstance(answer_index, int) and 0 <= answer_index < 4 else ""
        prompt = "Choose the answer shown by the visual pattern."
    else:
        safe_options = [str(option) for option in options]
        safe_answer = safe_options[answer_index] if isinstance(answer_index, int) and 0 <= answer_index < len(safe_options) else ""
        prompt = candidate.get("prompt") or "Choose the best answer."
    return {
        "id": candidate["id"],
        "item_family_id": candidate.get("item_family_id") or candidate["id"],
        "construct_id": candidate.get("construct_id", candidate.get("domain")),
        "domain": candidate.get("domain"),
        "type": "choice",
        "prompt": prompt,
        "helper": None if is_visual else candidate.get("context"),
        "options": safe_options,
        "answer": safe_answer,
        "explanation": candidate.get("rule"),
        "image_url": _asset_url(candidate) if is_visual else None,
        "render_type": "external_image" if is_visual else "choice",
        "status": "DRAFT",
        "lifecycle_status": "DRAFT",
        "language": "en",
        "data_origin": candidate.get("data_origin", "EXTERNAL_RESEARCH_DATA"),
        "review_required": True,
        "review_history": [],
        "content_version": candidate.get("content_version", 1),
        "provenance": candidate.get("provenance"),
    }


def load_items() -> Dict[str, Dict[str, Any]]:
    """Load lightweight staged records without retaining source answer data."""
    items: Dict[str, Dict[str, Any]] = {}
    try:
        candidates = external_data.iter_external_items(include_verbal=True, language="en")
        for candidate in candidates:
            if candidate.get("domain") not in STAGED_DOMAINS:
                continue
            item = _memory_item(candidate) if candidate.get("type") == "memory" else _choice_item(candidate)
            if item.get("answer") and item["id"] not in items:
                items[item["id"]] = item
    except (OSError, ValueError, TypeError, KeyError):
        # Missing local research folders should leave the normal authored bank
        # available instead of preventing the API from starting.
        return {}
    return items
