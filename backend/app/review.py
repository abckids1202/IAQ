"""In-memory review workflow used by local admin mode.

The same record shape is persisted by migration 008 when PostgreSQL is
configured. A generated item cannot enter PILOT or ACTIVE from one review.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List
from uuid import uuid4


REQUIRED_CHECKS = (
    "one_correct_answer",
    "unambiguous",
    "instructions_clear",
    "reading_level_ok",
    "rendering_ok",
    "distractors_plausible",
    "bias_reviewed",
    "family_unique_in_form",
)

ITEM_REVIEWS: Dict[str, List[Dict[str, Any]]] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def reviews_for(item_id: str) -> List[Dict[str, Any]]:
    return list(ITEM_REVIEWS.get(item_id, []))


def _checks_complete(checks: Dict[str, bool]) -> bool:
    return all(checks.get(key) is True for key in REQUIRED_CHECKS)


def record_review(item: Dict[str, Any], reviewer_id: str, reviewer_role: str, decision: str, notes: str, checks: Dict[str, bool]) -> Dict[str, Any]:
    if decision not in {"approve", "reject", "changes_requested"}:
        raise ValueError("Review decision is not supported")
    if decision == "approve" and not _checks_complete(checks):
        raise ValueError("Every review checklist item must be confirmed before approval")
    existing = reviews_for(item["id"])
    if any(review["reviewer_id"] == reviewer_id and review["version"] == item.get("content_version", 1) for review in existing):
        raise ValueError("This reviewer already reviewed this item version")
    review = {
        "id": str(uuid4()),
        "item_id": item["id"],
        "version": item.get("content_version", 1),
        "reviewer_id": reviewer_id,
        "reviewer_role": reviewer_role,
        "decision": decision,
        "status": "HUMAN_REVIEWED" if decision == "approve" else decision.upper(),
        "notes": notes.strip()[:2000],
        "checks": checks,
        "created_at": now(),
    }
    ITEM_REVIEWS.setdefault(item["id"], []).append(review)
    item.setdefault("review_history", []).append({key: review[key] for key in ("id", "reviewer_id", "decision", "created_at")})
    if decision == "reject" or decision == "changes_requested":
        item["status"] = "DRAFT"
        item["lifecycle_status"] = "DRAFT"
    elif len([row for row in ITEM_REVIEWS[item["id"]] if row["decision"] == "approve" and row["version"] == item.get("content_version", 1)]) >= 2:
        item["status"] = "HUMAN_REVIEWED"
        item["lifecycle_status"] = "HUMAN_REVIEWED"
        item["reviewed_at"] = now()
    return review


def review_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    reviews = reviews_for(item["id"])
    approvals = len([review for review in reviews if review["decision"] == "approve"])
    return {
        "review_count": len(reviews),
        "approval_count": approvals,
        "required_approvals": 2,
        "review_ready": approvals >= 2,
        "reviews": reviews,
    }


def review_counts(items: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        if review_summary(item)["review_ready"]:
            counts[item["domain"]] = counts.get(item["domain"], 0) + 1
    return counts
