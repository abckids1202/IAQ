"""Pilot item-health calculations.

These metrics are descriptive pilot signals, not norming or automatic item
activation. Synthetic response rows must be filtered before calling these
functions in production.
"""
from __future__ import annotations

from statistics import median
from typing import Any, Dict, Iterable, Mapping


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def item_health(item_id: str, answer_key: str, responses: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = [row for row in responses if row.get("item_id") == item_id and row.get("data_origin", "REAL_PILOT") == "REAL_PILOT"]
    answered = [row for row in rows if row.get("answer") not in (None, "")]
    correct = [1 if str(row.get("answer")) == answer_key else 0 for row in answered]
    times = [int(row.get("response_time_ms", 0)) for row in answered if int(row.get("response_time_ms", 0)) > 0]
    omissions = sum(1 for row in rows if row.get("answer") in (None, ""))
    timeouts = sum(1 for row in rows if row.get("timed_out") is True)
    p_correct = _mean([float(value) for value in correct]) if correct else None

    # A lightweight point-biserial-style signal: compare total scores for
    # respondents who got this item right versus those who did not.
    total_scores = [float(row["total_score"]) for row in answered if row.get("total_score") is not None]
    right_scores = [float(row["total_score"]) for row, value in zip(answered, correct) if value and row.get("total_score") is not None]
    wrong_scores = [float(row["total_score"]) for row, value in zip(answered, correct) if not value and row.get("total_score") is not None]
    discrimination = None
    if right_scores and wrong_scores and total_scores:
        spread = max(total_scores) - min(total_scores)
        discrimination = round((_mean(right_scores) - _mean(wrong_scores)) / spread, 3) if spread else 0.0

    flags: list[str] = []
    if p_correct is not None and p_correct >= 0.95:
        flags.append("nearly_universally_correct")
    if p_correct is not None and p_correct <= 0.05:
        flags.append("nearly_universally_wrong")
    if discrimination is not None and discrimination < 0.10:
        flags.append("low_discrimination")
    if not answered:
        flags.append("unused")
    if times and median(times) > 120000:
        flags.append("unusually_slow")

    return {
        "item_id": item_id,
        "data_origin": "REAL_PILOT",
        "sample_size": len(rows),
        "answered_count": len(answered),
        "correct_rate": round(p_correct, 4) if p_correct is not None else None,
        "discrimination": discrimination,
        "median_response_time_ms": int(median(times)) if times else None,
        "response_time_p25_ms": int(sorted(times)[max(0, int(len(times) * 0.25) - 1)]) if times else None,
        "response_time_p75_ms": int(sorted(times)[max(0, int(len(times) * 0.75) - 1)]) if times else None,
        "omission_rate": round(omissions / len(rows), 4) if rows else None,
        "timeout_rate": round(timeouts / len(rows), 4) if rows else None,
        "flags": flags,
    }


def bank_health(items: Iterable[Mapping[str, Any]], responses: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    response_rows = list(responses)
    metrics = [item_health(str(item["id"]), str(item["answer"]), response_rows) for item in items]
    flagged = [metric for metric in metrics if metric["flags"]]
    return {"data_origin": "REAL_PILOT", "items": metrics, "flagged_count": len(flagged), "sample_size": len(response_rows)}
