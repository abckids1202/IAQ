"""Pure, versioned IAQ scoring and matching logic.

This module intentionally contains no database or web concerns. In production the
same functions can be called from a transaction after validating a response.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional

DOMAINS = (
    "abstract_reasoning",
    "deductive_logic",
    "numerical_reasoning",
    "verbal_reasoning",
    "visual_spatial_reasoning",
    "processing_speed",
)
# Five item-based domains make up the 40-question form. Processing speed is
# retained as a sixth profile aspect and is inferred from response timing, not
# from a separate bank of speed questions.
ITEM_DOMAINS = tuple(domain for domain in DOMAINS if domain != "processing_speed")

# This is deliberately a separate score track from the observed domain signals.
# It maps observed performance into an arbitrary 70–130 display range,
# but it is not derived from population norms, IRT parameters, or a validated
# conversion table. Keep the label and method explicit anywhere it is shown.
EXPERIMENTAL_IQ_SCORE_VERSION = "IAQ-IQ-EXPERIMENTAL-2"
EXPERIMENTAL_IQ_SCORE_KIND = "experimental_iq_style_estimate"
EXPERIMENTAL_IQ_SCORE_LABEL = "IAQ IQ score — experimental"
EXPERIMENTAL_IQ_SCORE_SCALE = "70_130_uncalibrated_reference"
EXPERIMENTAL_IQ_SCORE_METHOD = "70 + (five_item_domain_mean_and_timing_speed * 0.60)"


@dataclass(frozen=True)
class ScoreResult:
    domain_scores: Dict[str, object]
    composite: object
    confidence: str
    quality_warnings: List[str]
    domain_metrics: Dict[str, Dict[str, object]] = field(default_factory=dict)
    # This is an observed within-profile signal, not a normed IQ score. Keep
    # the score kind explicit so a future normed model cannot be confused with
    # the pilot scorer in the API or report layer.
    score_version: str = "IAQ-PROVISIONAL-ACCURACY-1"
    score_kind: str = "provisional_domain_signal"
    norm_version: Optional[str] = None
    iq_score: Optional[int] = None
    iq_score_kind: str = EXPERIMENTAL_IQ_SCORE_KIND
    iq_score_scale: str = EXPERIMENTAL_IQ_SCORE_SCALE
    iq_score_method: str = EXPERIMENTAL_IQ_SCORE_METHOD


def score_domains(responses: Iterable[Mapping[str, object]], item_domains: Mapping[str, str], item_keys: Mapping[str, str]) -> ScoreResult:
    """Return a provisional within-profile score from server-validated answers.

    Missing domains remain visible with a conservative baseline. This is not an
    IRT estimate and must not be presented as a population percentile.
    """
    totals = {domain: [0, 0] for domain in ITEM_DOMAINS}
    response_times: Dict[str, List[int]] = {domain: [] for domain in DOMAINS}
    rapid = 0
    interruptions = 0
    seen = set()
    for response in responses:
        item_id = str(response.get("item_id", ""))
        domain = item_domains.get(item_id)
        if domain not in totals or item_id in seen or item_id not in item_keys:
            continue
        seen.add(item_id)
        if totals[domain][1] >= 8:
            raise ValueError("A scored form cannot contain more than eight responses per domain")
        # Every complete form reserves eight items per domain.  Responses are
        # counted here for evidence/quality, while the fixed denominator below
        # ensures omissions cannot inflate accuracy.
        totals[domain][1] += 1
        if str(response.get("answer")) == item_keys.get(item_id):
            totals[domain][0] += 1
        elapsed = response.get("response_time_ms")
        if isinstance(elapsed, (int, float)) and elapsed >= 0:
            if elapsed < 1500:
                rapid += 1
            response_times[domain].append(int(elapsed))
    # A domain with too little evidence is explicitly unassessed. It must not
    # become a flattering or punitive ability-looking number by accident.
    minimum_items_for_interpretation = 4
    domain_scores = {
        # Until item parameters and age norms exist, report observed accuracy
        # directly. A synthetic baseline (for example, 50 at zero correct)
        # would make the result look more scientific than the evidence allows.
        domain: round((correct / 8) * 100) if total >= minimum_items_for_interpretation else None
        for domain, (correct, total) in totals.items()
    }
    all_times = sorted(time for times in response_times.values() for time in times)
    speed_midpoint = len(all_times) // 2
    median_all_time = None if not all_times else all_times[speed_midpoint] if len(all_times) % 2 else round((all_times[speed_midpoint - 1] + all_times[speed_midpoint]) / 2)
    # Timing is a transparent pilot signal only. It is not calibrated against
    # a population and must not be described as a normed processing-speed score.
    speed_score = None if len(all_times) < minimum_items_for_interpretation else round(max(0, min(100, 100 - ((median_all_time - 1500) / 7500 * 100))))
    domain_scores["processing_speed"] = speed_score
    answered = sum(pair[1] for pair in totals.values())
    interpretable_scores = [value for value in domain_scores.values() if isinstance(value, int)]
    composite = round(sum(interpretable_scores) / len(interpretable_scores)) if len(interpretable_scores) == len(DOMAINS) else None
    # An IQ-style number is withheld unless all five item domains and timing
    # have enough
    # evidence. With no human calibration or age norms, this is only a
    # transparent reference transform of the complete profile mean.
    complete_profile = len(interpretable_scores) == len(DOMAINS)
    # Round once at the end; rounding each domain first biases the composite.
    exact_composite = (sum(correct / 8 * 100 for correct, _ in totals.values()) + (speed_score or 0)) / len(DOMAINS)
    iq_score = round(70 + (exact_composite * 0.60)) if complete_profile else None
    warnings: List[str] = []
    if answered < 40:
        warnings.append("incomplete_assessment")
    if rapid >= 2:
        warnings.append("rapid_guessing_possible")
    if interruptions:
        warnings.append("session_interrupted")
    # Completion is not reliability. No empirical precision estimate exists.
    confidence = "limited" if complete_profile and not warnings else "low"
    domain_metrics = {}
    for domain, (correct, total) in totals.items():
        times = sorted(response_times[domain])
        midpoint = len(times) // 2
        median = None if not times else times[midpoint] if len(times) % 2 else round((times[midpoint - 1] + times[midpoint]) / 2)
        domain_metrics[domain] = {
            "answered": total,
            "correct": correct,
            "omitted": 8 - total,
            "accuracy": round((correct / 8) * 100) if total else None,
            "median_response_time_ms": median,
            "interpretation_eligible": total >= minimum_items_for_interpretation,
            "evidence_note": None if total >= minimum_items_for_interpretation else f"Only {total} scored item(s) completed in this area.",
        }
    domain_metrics["processing_speed"] = {
        "answered": len(all_times),
        "correct": None,
        "omitted": max(0, 40 - len(all_times)),
        "accuracy": None,
        "median_response_time_ms": median_all_time,
        "interpretation_eligible": speed_score is not None,
        "evidence_note": None if speed_score is not None else "Not enough response-time evidence in this snapshot.",
    }
    return ScoreResult(
        domain_scores,
        composite,
        confidence,
        warnings,
        domain_metrics,
        score_version="IAQ-PROVISIONAL-ACCURACY-1",
        score_kind="provisional_domain_signal",
        norm_version=None,
        iq_score=iq_score,
        iq_score_kind=EXPERIMENTAL_IQ_SCORE_KIND,
        iq_score_scale=EXPERIMENTAL_IQ_SCORE_SCALE,
        iq_score_method=EXPERIMENTAL_IQ_SCORE_METHOD,
    )


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
    return {"status": "low" if len(warnings) >= 2 else "moderate" if warnings else "acceptable", "rapid_guessing_items": rapid_count, "possible_fatigue": fatigue, "warnings": warnings}
