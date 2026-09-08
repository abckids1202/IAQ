"""Server-side access to the staged IAQ research datasets.

The files under ``data/assessment`` are intentionally not imported into the
student question bank. They are research candidates: every record remains
unreviewed, uncalibrated, and ineligible for scored IAQ sessions until the
human-review and pilot gates are satisfied.
"""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Iterator, List, Optional
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FIVE_DOMAIN_FILES = {
    "logical": ("logical_original.jsonl", "deductive_logic"),
    "numerical": ("numerical_original.jsonl", "numerical_reasoning"),
    "abstract": ("abstract_original.jsonl", "abstract_reasoning"),
    "spatial": ("spatial_original.jsonl", "visual_spatial_reasoning"),
    "memory": ("memory_original.jsonl", "working_memory"),
}

REQUIRED_REVIEW_CHECKS = (
    "one_correct_answer",
    "unambiguous",
    "instructions_clear",
    "reading_level_ok",
    "rendering_ok",
    "distractors_plausible",
    "bias_reviewed",
    "family_unique_in_form",
)
_REVIEW_STATE: Dict[str, List[Dict[str, Any]]] = {}
_REVIEW_STATE_LOADED = False
_REVIEW_STATE_PATH: Optional[Path] = None


def assessment_root() -> Path:
    configured = os.getenv("IAQ_ASSESSMENT_DATA_ROOT")
    if not configured:
        return PROJECT_ROOT / "data" / "assessment"
    configured_path = Path(configured).expanduser()
    return configured_path if configured_path.is_absolute() else PROJECT_ROOT / configured_path


def _ensure_review_state() -> None:
    global _REVIEW_STATE_LOADED, _REVIEW_STATE_PATH
    state_path = assessment_root() / ".dataset-review-state.json"
    if _REVIEW_STATE_LOADED and _REVIEW_STATE_PATH == state_path:
        return
    _REVIEW_STATE_PATH = state_path
    _REVIEW_STATE.clear()
    try:
        if state_path.exists():
            raw = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                _REVIEW_STATE.update({str(key): value for key, value in raw.items() if isinstance(value, list)})
    except (OSError, json.JSONDecodeError):
        # A corrupt local review cache should never make the dataset or API
        # unavailable. Reviewers can simply start a fresh review record.
        _REVIEW_STATE.clear()
    _REVIEW_STATE_LOADED = True


def _save_review_state() -> None:
    if not _REVIEW_STATE_PATH:
        return
    try:
        _REVIEW_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _REVIEW_STATE_PATH.write_text(json.dumps(_REVIEW_STATE, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        # Production uses the database-backed review tables. Local preview
        # mode remains usable if its optional sidecar is read-only.
        return


def _read_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSONL in {path.name} at line {line_number}") from error
            if not isinstance(record, dict):
                raise ValueError(f"Expected an object in {path.name} at line {line_number}")
            yield record


def _source_license(dataset: str) -> str:
    if dataset == "logiqa2":
        return "CC BY-NC-SA 4.0 stated by source kit; item-level deployment still requires review"
    if dataset == "logiqa1":
        return "UNVERIFIED — public source availability is not commercial permission"
    return "UNVERIFIED — IAQ research candidate; review source terms before deployment"


def _asset_path(record: Dict[str, Any], kind: str) -> Optional[str]:
    if kind != "five_domains" or not record.get("image_path"):
        return None
    return f"five_domains/{record['image_path']}"


def resolve_asset_path(dataset: str, asset_path: str) -> Optional[Path]:
    """Resolve an admin preview asset while preventing path traversal."""
    root = assessment_root().resolve()
    if dataset not in {"five_domains"}:
        return None
    # The API path is relative to the dataset's asset root. Accept the
    # normalised ``assets/...`` form and the internal ``five_domains/assets``
    # form used in stored candidate metadata.
    normalised = asset_path.replace("\\", "/").lstrip("/")
    if normalised.startswith("five_domains/"):
        normalised = normalised[len("five_domains/"):]
    candidate = (root / "five_domains" / normalised).resolve()
    allowed = (root / "five_domains" / "assets").resolve()
    try:
        candidate.relative_to(allowed)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _normalise(record: Dict[str, Any], *, dataset: str, source_file: str, domain: str, kind: str) -> Dict[str, Any]:
    _ensure_review_state()
    source_id = str(record.get("id") or record.get("source_id") or "unknown")
    dataset_name = str(record.get("dataset") or dataset)
    context = str(record.get("context") or "").strip()
    question = str(record.get("question") or "").strip()
    prompt = f"{context}\n\n{question}" if context else question
    asset_path = _asset_path(record, kind)
    asset_exists = bool(asset_path and resolve_asset_path("five_domains", asset_path))
    item = {
        "id": f"external:{dataset_name}:{source_id}",
        "source_id": source_id,
        "source_dataset": dataset_name,
        "source_file": source_file,
        "domain": domain,
        "item_family_id": f"{dataset_name}:{record.get('family') or record.get('protocol') or source_id}",
        "construct_id": domain,
        "type": "memory" if record.get("protocol") else "choice",
        "prompt": prompt,
        "context": context or None,
        "question": question,
        "options": record.get("options"),
        "answer": record.get("answer"),
        "answer_index": record.get("answer_index"),
        "rule": record.get("rule"),
        "stimulus": record.get("stimulus"),
        "protocol": record.get("protocol"),
        "image_path": record.get("image_path"),
        "asset_path": asset_path,
        "asset_exists": asset_exists,
        "review_status": "unreviewed",
        "lifecycle_status": "DRAFT",
        "status": "DRAFT",
        "calibrated": False,
        "production_eligible": False,
        "commercial_use_approved": False,
        "difficulty_estimate": None,
        "content_version": 1,
        "language": record.get("language", "en"),
        "data_origin": "EXTERNAL_RESEARCH_DATA" if kind == "verbal" else "IAQ_GENERATED_RESEARCH_DATA",
        "provenance": {
            "source_file": source_file,
            "source_url": record.get("source_url"),
            "source_license": _source_license(dataset_name),
            "generator": record.get("generator"),
            "generator_version": record.get("generator_version"),
            "seed": record.get("seed"),
            "stimulus_sha256": record.get("stimulus_sha256"),
        },
        "source_record": record,
        "review_history": [],
    }
    reviews = list(_REVIEW_STATE.get(item["id"], []))
    approvals = sum(1 for review in reviews if review.get("decision") == "approve")
    if approvals >= 2:
        item["review_status"] = "human_reviewed"
        item["lifecycle_status"] = "HUMAN_REVIEWED"
    elif any(review.get("decision") == "changes_requested" for review in reviews):
        item["review_status"] = "changes_requested"
    elif any(review.get("decision") == "reject" for review in reviews):
        item["review_status"] = "rejected"
    elif reviews:
        item["review_status"] = "in_review"
    item["review_history"] = [{key: row.get(key) for key in ("id", "reviewer_id", "decision", "created_at", "notes")} for row in reviews]
    item["review"] = {
        "review_count": len(reviews),
        "approval_count": approvals,
        "required_approvals": 2,
        "review_ready": approvals >= 2,
        "reviews": reviews,
    }
    return item


def iter_external_items(*, include_verbal: bool = True, language: Optional[str] = "en", domain: Optional[str] = None) -> Iterator[Dict[str, Any]]:
    """Yield normalised candidates without adding them to student ``ITEMS``."""
    root = assessment_root()
    five_root = root / "five_domains"
    for dataset, (filename, mapped_domain) in FIVE_DOMAIN_FILES.items():
        if domain and mapped_domain != domain:
            continue
        path = five_root / "banks" / filename
        for record in _read_jsonl(path):
            yield _normalise(record, dataset=dataset, source_file=filename, domain=mapped_domain, kind="five_domains")
    if not include_verbal:
        return
    verbal_root = root / "verbal" / "jsonl"
    for path in sorted(verbal_root.glob("*_en_*.jsonl")):
        for record in _read_jsonl(path):
            dataset = str(record.get("dataset") or path.name.split("_en_", 1)[0])
            mapped_domain = "verbal_reasoning"
            if domain and mapped_domain != domain:
                continue
            if language and record.get("language", "en") != language:
                continue
            yield _normalise(record, dataset=dataset, source_file=path.name, domain=mapped_domain, kind="verbal")


def _file_summary(path: Path, *, dataset: str, domain: Optional[str], kind: str, language: Optional[str]) -> Dict[str, Any]:
    _ensure_review_state()
    records = list(_read_jsonl(path))
    if language:
        records = [record for record in records if record.get("language", "en") == language]
    ids = [str(record.get("id") or record.get("source_id")) for record in records]
    families = [str(record.get("family") or record.get("protocol") or "unclassified") for record in records]
    missing_assets = 0
    if kind == "five_domains":
        missing_assets = sum(1 for record in records if record.get("image_path") and not resolve_asset_path("five_domains", f"five_domains/{record['image_path']}"))
    review_status: Counter[str] = Counter()
    for record in records:
        source_id = str(record.get("id") or record.get("source_id"))
        dataset_name = str(record.get("dataset") or dataset)
        rows = _REVIEW_STATE.get(f"external:{dataset_name}:{source_id}", [])
        approvals = sum(1 for row in rows if row.get("decision") == "approve")
        status = "human_reviewed" if approvals >= 2 else "in_review" if rows else "unreviewed"
        review_status[status] += 1
    return {
        "file": path.name,
        "dataset": dataset,
        "domain": domain,
        "language": language,
        "records": len(records),
        "unique_ids": len(set(ids)),
        "families": len(set(families)),
        "missing_assets": missing_assets,
        "review_status": dict(review_status),
        "production_eligible": 0,
    }


def dataset_summary() -> Dict[str, Any]:
    root = assessment_root()
    five_root = root / "five_domains"
    files: List[Dict[str, Any]] = []
    for dataset, (filename, mapped_domain) in FIVE_DOMAIN_FILES.items():
        path = five_root / "banks" / filename
        if path.exists():
            files.append(_file_summary(path, dataset=dataset, domain=mapped_domain, kind="five_domains", language=None))
    verbal_root = root / "verbal" / "jsonl"
    for path in sorted(verbal_root.glob("*_en_*.jsonl")):
        if path.exists():
            dataset = path.name.split("_en_", 1)[0]
            files.append(_file_summary(path, dataset=dataset, domain="verbal_reasoning", kind="verbal", language="en"))
    by_domain: Counter[str] = Counter()
    for item in files:
        by_domain[item["domain"]] += item["records"]
    return {
        "available": bool(files),
        "root": "data/assessment",
        "student_sessions_use": False,
        "review_gate": "All staged records are DRAFT/unreviewed and production_eligible=false.",
        "files": files,
        "totals": {
            "files": len(files),
            "records": sum(item["records"] for item in files),
            "by_domain": dict(by_domain),
            "missing_assets": sum(item["missing_assets"] for item in files),
        },
        "review": review_summary(files=files),
    }


def preview_items(*, limit: int = 20, domain: Optional[str] = None, dataset: Optional[str] = None) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for item in iter_external_items(include_verbal=True, language="en", domain=domain):
        if dataset and item["source_dataset"] != dataset:
            continue
        results.append(item)
        if len(results) >= limit:
            break
    return results


def find_external_item(item_id: str) -> Optional[Dict[str, Any]]:
    """Find one staged candidate by its stable external id."""
    return next((item for item in iter_external_items(include_verbal=True, language="en") if item["id"] == item_id), None)


def review_external_item(item_id: str, reviewer_id: str, reviewer_role: str, decision: str, notes: str, checks: Dict[str, bool]) -> Dict[str, Any]:
    """Record a reviewer decision without promoting a candidate into scoring."""
    _ensure_review_state()
    item = find_external_item(item_id)
    if not item:
        raise ValueError("Dataset candidate not found")
    if decision not in {"approve", "reject", "changes_requested"}:
        raise ValueError("Review decision is not supported")
    if decision == "approve" and any(checks.get(key) is not True for key in REQUIRED_REVIEW_CHECKS):
        raise ValueError("Every review checklist item must be confirmed before approval")
    version = int(item.get("content_version", 1))
    existing = list(_REVIEW_STATE.get(item_id, []))
    if any(row.get("reviewer_id") == reviewer_id and row.get("version") == version for row in existing):
        raise ValueError("This reviewer already reviewed this item version")
    review = {
        "id": str(uuid4()),
        "item_id": item_id,
        "version": version,
        "reviewer_id": reviewer_id,
        "reviewer_role": reviewer_role,
        "decision": decision,
        "status": "HUMAN_REVIEWED" if decision == "approve" else decision.upper(),
        "notes": notes.strip()[:2000],
        "checks": checks,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _REVIEW_STATE.setdefault(item_id, []).append(review)
    _save_review_state()
    refreshed = find_external_item(item_id)
    return {"accepted": True, "review": review, "item": refreshed, "student_sessions_use": False}


def review_summary(*, files: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Return review progress for the quarantined catalog."""
    _ensure_review_state()
    if files is None:
        # This route is rarely called directly. Build lightweight inventory
        # metadata without normalising every candidate or opening images.
        files = []
        root = assessment_root()
        for dataset, (filename, mapped_domain) in FIVE_DOMAIN_FILES.items():
            path = root / "five_domains" / "banks" / filename
            if path.exists():
                files.append({"dataset": dataset, "domain": mapped_domain, "records": sum(1 for _ in _read_jsonl(path))})
        for path in sorted((root / "verbal" / "jsonl").glob("*_en_*.jsonl")):
            files.append({"dataset": path.name.split("_en_", 1)[0], "domain": "verbal_reasoning", "records": sum(1 for record in _read_jsonl(path) if record.get("language", "en") == "en")})
    counts: Counter[str] = Counter()
    approvals: Counter[str] = Counter()
    candidate_totals: Counter[str] = Counter()
    for file in files:
        candidate_totals[str(file["domain"])] += int(file.get("records", 0))
    dataset_domains = {dataset: domain for dataset, (_, domain) in FIVE_DOMAIN_FILES.items()}
    dataset_domains.update({str(file["dataset"]): str(file["domain"]) for file in files})
    for item_id, rows in _REVIEW_STATE.items():
        parts = str(item_id).split(":", 2)
        domain = dataset_domains.get(parts[1], "") if len(parts) > 1 else ""
        if not domain:
            continue
        approval_count = sum(1 for row in rows if row.get("decision") == "approve")
        approvals[domain] += approval_count
        if approval_count >= 2:
            counts[f"{domain}:HUMAN_REVIEWED"] += 1
        elif any(row.get("decision") == "changes_requested" for row in rows):
            counts[f"{domain}:CHANGES_REQUESTED"] += 1
        elif any(row.get("decision") == "reject" for row in rows):
            counts[f"{domain}:REJECTED"] += 1
        else:
            counts[f"{domain}:IN_REVIEW"] += 1
    by_domain = {
        domain: {
            "candidates": candidate_totals.get(domain, 0),
            "human_reviewed": counts.get(f"{domain}:HUMAN_REVIEWED", 0),
            "in_review": counts.get(f"{domain}:IN_REVIEW", 0),
            "changes_requested": counts.get(f"{domain}:CHANGES_REQUESTED", 0),
            "draft": max(0, candidate_totals.get(domain, 0) - sum(value for key, value in counts.items() if key.startswith(f"{domain}:"))),
            "eligible_for_pilot": 0,
        }
        for domain in candidate_totals
    }
    return {
        "reviewed_target_per_domain": 100,
        "by_domain": by_domain,
        "approval_events_by_domain": dict(approvals),
        "eligible_for_student_sessions": False,
        "note": "Two approvals create HUMAN_REVIEWED only. Pilot activation still requires licensing, calibration, and release review.",
    }
