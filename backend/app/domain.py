"""Pure, versioned IAQ scoring and matching logic.

This module intentionally contains no database or web concerns. In production the
same functions can be called from a transaction after validating a response.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping

DOMAINS = (
    "abstract_reasoning",
    "deductive_logic",
    "numerical_reasoning",
    "verbal_reasoning",
    "visual_spatial_reasoning",
    "working_memory",
    "processing_speed",
)


@dataclass(frozen=True)
class ScoreResult:
    domain_scores: Dict[str, object]
    composite: object
    confidence: str
    quality_warnings: List[str]
    domain_metrics: Dict[str, Dict[str, object]] = field(default_factory=dict)
    score_version: str = "SCORING-V1"


def score_domains(responses: Iterable[Mapping[str, object]], item_domains: Mapping[str, str], item_keys: Mapping[str, str]) -> ScoreResult:
    """Return a provisional within-profile score from server-validated answers.

    Missing domains remain visible with a conservative baseline. This is not an
    IRT estimate and must not be presented as a population percentile.
    """
    totals = {domain: [0, 0] for domain in DOMAINS}
    response_times: Dict[str, List[int]] = {domain: [] for domain in DOMAINS}
    rapid = 0
    interruptions = 0
    for response in responses:
        item_id = str(response.get("item_id", ""))
        domain = item_domains.get(item_id)
        if domain not in totals:
            continue
        totals[domain][1] += 1
        if str(response.get("answer")) == item_keys.get(item_id):
            totals[domain][0] += 1
        if int(response.get("response_time_ms", 10000) or 10000) < 1500:
            rapid += 1
        response_times[domain].append(int(response.get("response_time_ms", 10000) or 10000))
    # A domain with too little evidence is explicitly unassessed. It must not
    # become a flattering or punitive ability-looking number by accident.
    minimum_items_for_interpretation = 4
    domain_scores = {
        domain: round(50 + ((correct / total) * 45)) if total >= minimum_items_for_interpretation else None
        for domain, (correct, total) in totals.items()
    }
    answered = sum(pair[1] for pair in totals.values())
    interpretable_scores = [value for value in domain_scores.values() if isinstance(value, int)]
    composite = round(sum(interpretable_scores) / len(interpretable_scores)) if len(interpretable_scores) >= 2 else None
    warnings: List[str] = []
    if answered < 7:
        warnings.append("incomplete_assessment")
    if rapid >= 2:
        warnings.append("rapid_guessing_possible")
    if interruptions:
        warnings.append("session_interrupted")
    confidence = "high" if answered >= 12 and not warnings else "moderate" if answered >= 7 else "low"
    domain_metrics = {}
    for domain, (correct, total) in totals.items():
        times = sorted(response_times[domain])
        midpoint = len(times) // 2
        median = None if not times else times[midpoint] if len(times) % 2 else round((times[midpoint - 1] + times[midpoint]) / 2)
        domain_metrics[domain] = {
            "answered": total,
            "correct": correct,
            "accuracy": round((correct / total) * 100) if total else None,
            "median_response_time_ms": median,
            "interpretation_eligible": total >= minimum_items_for_interpretation,
            "evidence_note": None if total >= minimum_items_for_interpretation else f"Only {total} scored item(s) completed in this area.",
        }
    return ScoreResult(domain_scores, composite, confidence, warnings, domain_metrics)


def score_riasec(responses: Mapping[str, int]) -> Dict[str, object]:
    ordered = sorted(responses.items(), key=lambda pair: pair[1], reverse=True)
    return {"scores": dict(responses), "code": "".join(code for code, _ in ordered[:3]), "version": "RIASEC-PROVISIONAL-1"}


def major_fit(cognitive: Mapping[str, int], interests: Mapping[str, int], academic_readiness: int, vector: Mapping[str, float]) -> Dict[str, int]:
    cognitive_average = sum(cognitive.get(domain, 50) * weight for domain, weight in vector.items()) / max(sum(vector.values()), 1)
    interest_fit = round((interests.get("I", 50) + interests.get("A", 50) + interests.get("C", 50)) / 3)
    fit = round((cognitive_average * 0.55) + (interest_fit * 0.45))
    readiness = max(0, min(100, int(academic_readiness)))
    feasibility = "ready_to_explore" if readiness >= 75 else "feasible_with_preparation" if readiness >= 60 else "needs_preparation"
    return {"interest_fit": interest_fit, "cognitive_fit": round(cognitive_average), "fit": fit, "readiness": readiness, "feasibility": feasibility}


def recommendation_confidence(completed_modules: int, measurement_uncertainty: float, evidence_count: int, profile_age_days: int) -> int:
    score = 45 + (completed_modules * 6) + min(evidence_count * 4, 20) - round(measurement_uncertainty * 15) - min(profile_age_days // 45, 15)
    return max(20, min(95, score))


def classify_session_quality(response_times_ms: Iterable[int], interruptions: int = 0, accessibility_adjustments: bool = False) -> Dict[str, object]:
    times = list(response_times_ms)
    rapid_count = sum(1 for value in times if value < 1500)
    fatigue = len(times) >= 8 and sum(times[-3:]) / 3 > (sum(times[:3]) / 3) * 1.7
    warnings: List[str] = []
    if rapid_count >= 2:
        warnings.append("rapid_guessing_possible")
    if interruptions:
        warnings.append("interruptions")
    if fatigue:
        warnings.append("possible_fatigue")
    if accessibility_adjustments:
        warnings.append("accessibility_adjustment_recorded")
    return {"status": "low" if len(warnings) >= 2 else "moderate" if warnings else "acceptable", "rapid_guessing_items": rapid_count, "fatigue_probability": 0.55 if fatigue else 0.12, "warnings": warnings}
