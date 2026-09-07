"""Provider boundary for optional OpenAI-assisted IAQ explanations.

The assessment score and direction fit remain deterministic server logic. This
module is deliberately limited to plain-language interpretation and next-step
ideas after a result exists. It never receives answer keys and never has a
method to change a score, item lifecycle, entitlement, or recommendation fit.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple


PROMPT_VERSION = "IAQ-AI-INTERPRETATION-1.0"


class AIUnavailable(RuntimeError):
    """Raised when the optional provider is not configured or cannot be used."""


class AIOutputError(RuntimeError):
    """Raised when a provider response cannot be safely parsed or validated."""


@dataclass(frozen=True)
class AIConfig:
    enabled: bool
    model: str
    timeout_seconds: float
    api_key_present: bool
    organization: Optional[str] = None
    project: Optional[str] = None


def get_config() -> AIConfig:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    explicitly_disabled = os.getenv("IAQ_AI_ENABLED", "").strip().lower() in {"0", "false", "no", "off"}
    try:
        timeout = max(5.0, min(120.0, float(os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS", "25"))))
    except ValueError:
        timeout = 25.0
    return AIConfig(
        enabled=bool(key) and not explicitly_disabled,
        model=os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini",
        timeout_seconds=timeout,
        api_key_present=bool(key),
        organization=os.getenv("OPENAI_ORGANIZATION") or None,
        project=os.getenv("OPENAI_PROJECT") or None,
    )


def public_status() -> Dict[str, Any]:
    config = get_config()
    return {
        "enabled": config.enabled,
        "configured": config.api_key_present,
        "model": config.model if config.enabled else None,
        "prompt_version": PROMPT_VERSION,
        "capabilities": ["result_interpretation", "direction_context"],
        "boundaries": ["deterministic_scoring", "no_norms", "no_question_activation", "no_diagnosis"],
    }


def _client():
    config = get_config()
    if not config.enabled:
        raise AIUnavailable("OpenAI is not configured. Add OPENAI_API_KEY to the server environment and restart the API.")
    try:
        from openai import OpenAI
    except ImportError as error:
        raise AIUnavailable("The OpenAI Python SDK is not installed. Run pip install -r backend/requirements.txt.") from error
    kwargs: Dict[str, Any] = {"timeout": config.timeout_seconds, "max_retries": 2}
    if config.organization:
        kwargs["organization"] = config.organization
    if config.project:
        kwargs["project"] = config.project
    return OpenAI(**kwargs), config


def _parse_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise AIOutputError("The AI response was not valid JSON")
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError as error:
            raise AIOutputError("The AI response was not valid JSON") from error
    if not isinstance(value, dict):
        raise AIOutputError("The AI response must be a JSON object")
    return value


def _call(instructions: str, payload: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    client, config = _client()
    try:
        response = client.responses.create(
            model=config.model,
            instructions=instructions,
            input=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            store=False,
        )
    except Exception as error:  # provider-specific exceptions vary by SDK version
        raise AIUnavailable(f"OpenAI request failed: {error}") from error
    output_text = getattr(response, "output_text", "") or ""
    parsed = _parse_json(output_text)
    metadata = {
        "provider": "openai",
        "model": config.model,
        "prompt_version": PROMPT_VERSION,
        "request_id": getattr(response, "_request_id", None),
    }
    return parsed, metadata


def _strings(value: Any, maximum: int = 4) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:500] for item in value[:maximum] if str(item).strip()]


def interpret_result(result: Mapping[str, Any], domain_labels: Mapping[str, str]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Generate cautious report copy from already-scored, persisted evidence."""
    domain_scores = result.get("domain_scores", {})
    metrics = result.get("domain_metrics", {})
    payload = {
        "profile_score": result.get("composite"),
        "confidence": result.get("confidence"),
        "quality": result.get("quality", {}),
        "answered_count": result.get("answered_count"),
        "question_count": result.get("question_count"),
        "domains": [
            {"domain": domain_labels.get(code, code), "score": score, "metrics": metrics.get(code, {})}
            for code, score in domain_scores.items()
        ],
    }
    instructions = """You are IAQ's cautious educational report editor. Return JSON only with exactly these keys:
what_stands_out (array of at most 3 short strings), where_more_evidence (array of at most 3 short strings), timing_context (one short string), next_step (one short string).
Use only the supplied evidence. If a score is null or a domain has too little evidence, say that more evidence is needed. Never call this an IQ score, diagnosis, percentile, intelligence level, or fixed trait. Do not infer age, gender, culture, disability, or career destiny. Do not invent numbers. Keep language clear for a student aged 15–22. Mention that this is a provisional within-profile snapshot when relevant."""
    output, metadata = _call(instructions, payload)
    normalized = {
        "what_stands_out": _strings(output.get("what_stands_out")),
        "where_more_evidence": _strings(output.get("where_more_evidence")),
        "timing_context": str(output.get("timing_context", "Timing is context, not a verdict."))[:700],
        "next_step": str(output.get("next_step", "Try one small learning activity and reflect on what you notice."))[:700],
    }
    if not normalized["what_stands_out"] and not normalized["where_more_evidence"]:
        raise AIOutputError("The AI response did not contain usable report observations")
    return normalized, metadata


def suggest_directions(result: Mapping[str, Any], interests: Mapping[str, Any], candidates: List[Mapping[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Add bounded narrative to deterministic direction candidates."""
    payload = {
        "cognitive_profile": {"composite": result.get("composite"), "domain_scores": result.get("domain_scores", {}), "confidence": result.get("confidence")},
        "interests": {"code": interests.get("code"), "scores": interests.get("scores", {})},
        "candidate_directions": [{key: item.get(key) for key in ("slug", "name", "family", "fit", "readiness", "confidence")} for item in candidates],
    }
    instructions = """You are IAQ's direction-exploration assistant. Return JSON only with key directions, an array of at most 5 objects. Each object must have slug, why_this_may_fit, try_next, and caution. Use only candidate slugs provided. Keep every explanation practical and tentative. Do not say a student is suited, destined, gifted, unsuitable, or guaranteed to succeed. Do not invent labour-market facts, admissions requirements, or scores. State that real projects, conversations, and course research are needed."""
    output, metadata = _call(instructions, payload)
    allowed = {str(item.get("slug")): item for item in candidates}
    directions: List[Dict[str, Any]] = []
    for item in output.get("directions", []) if isinstance(output.get("directions"), list) else []:
        if not isinstance(item, dict) or item.get("slug") not in allowed:
            continue
        directions.append({
            "slug": item["slug"],
            "name": allowed[item["slug"]].get("name"),
            "why_this_may_fit": str(item.get("why_this_may_fit", "A possible direction to explore."))[:700],
            "try_next": str(item.get("try_next", "Try a small project or talk to someone in this area."))[:700],
            "caution": str(item.get("caution", "This is an exploration prompt, not a prediction."))[:700],
        })
    if not directions:
        raise AIOutputError("The AI response did not contain an allowed direction")
    return {"directions": directions}, metadata
