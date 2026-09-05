"""FastAPI boundary for the IAQ V1.0 pilot baseline.

The default local store is intentionally small and dependency-light so the demo
can run without an external database. The migration in migrations/ is the
production persistence contract; swap the store behind these endpoints when
connecting PostgreSQL.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .domain import DOMAINS, classify_session_quality, score_domains, score_riasec, major_fit, recommendation_confidence

app = FastAPI(title="IAQ API", version="0.1.0", description="Experimental educational profile API")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

NOW = lambda: datetime.now(timezone.utc).isoformat()

ITEMS: Dict[str, Dict[str, Any]] = {
    "abs-01": {"id": "abs-01", "domain": "abstract_reasoning", "type": "choice", "prompt": "Each tile changes by the same rule. Which tile completes the sequence?", "options": ["A", "B", "C", "D"], "answer": "B", "status": "ACTIVE"},
    "logic-01": {"id": "logic-01", "domain": "deductive_logic", "type": "choice", "prompt": "All red notebooks are archived. This notebook is red. What must be true?", "options": ["It is archived", "It is new", "It is blue", "Nothing can be concluded"], "answer": "It is archived", "status": "ACTIVE"},
    "num-01": {"id": "num-01", "domain": "numerical_reasoning", "type": "sequence", "prompt": "Complete the sequence: 3, 6, 12, 24, __", "options": ["30", "36", "42", "48"], "answer": "48", "status": "ACTIVE"},
    "verbal-01": {"id": "verbal-01", "domain": "verbal_reasoning", "type": "choice", "prompt": "A map is to navigation as a score is to…", "options": ["Music", "Evaluation", "Paper", "Competition"], "answer": "Evaluation", "status": "ACTIVE"},
    "spatial-01": {"id": "spatial-01", "domain": "visual_spatial_reasoning", "type": "choice", "prompt": "Imagine the L-shape rotates 90° clockwise. Which direction does its short arm point?", "options": ["Up", "Down", "Left", "Right"], "answer": "Down", "status": "ACTIVE"},
    "memory-01": {"id": "memory-01", "domain": "working_memory", "type": "memory", "prompt": "Remember this sequence, then select it in the same order.", "options": ["7-2-9-4", "7-9-2-4", "2-7-4-9", "9-4-7-2"], "answer": "7-2-9-4", "status": "ACTIVE"},
    "speed-01": {"id": "speed-01", "domain": "processing_speed", "type": "speed", "prompt": "Find the only pair of matching symbols.", "options": ["A", "B", "C", "D"], "answer": "B", "status": "ACTIVE"},
}
SESSIONS: Dict[str, Dict[str, Any]] = {}
RESULTS: Dict[str, Dict[str, Any]] = {}
EVENTS: List[Dict[str, Any]] = []
SAVED_MAJORS: Dict[str, List[str]] = {}

MAJORS = [
    {"id": "cs", "slug": "computer-science", "name": "Computer Science", "family": "Technology & systems", "vector": {"abstract_reasoning": .9, "deductive_logic": .9, "numerical_reasoning": .8}},
    {"id": "arch", "slug": "architecture", "name": "Architecture", "family": "Design & built environment", "vector": {"visual_spatial_reasoning": .95, "abstract_reasoning": .7, "numerical_reasoning": .5}},
    {"id": "data", "slug": "data-science", "name": "Data Science", "family": "Technology & analysis", "vector": {"numerical_reasoning": .95, "deductive_logic": .8, "abstract_reasoning": .8}},
    {"id": "design", "slug": "industrial-design", "name": "Industrial Design", "family": "Design & making", "vector": {"visual_spatial_reasoning": .9, "abstract_reasoning": .6, "verbal_reasoning": .4}},
    {"id": "psych", "slug": "psychology", "name": "Psychology", "family": "People & behaviour", "vector": {"verbal_reasoning": .8, "deductive_logic": .7, "abstract_reasoning": .6}},
]


class SessionCreate(BaseModel):
    assessment_version: str = "IAQ-COG-0.3"
    mode: str = Field(default="quick", pattern="^(quick|complete)$")


class ResponseCreate(BaseModel):
    item_id: str
    answer: str
    response_time_ms: int = Field(default=10000, ge=0, le=3600000)
    presented_order: int = Field(default=0, ge=0)


class EventCreate(BaseModel):
    event_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConsentCreate(BaseModel):
    consent_version: str = "CONSENT-1.0"
    purpose: str = "assessment_and_direction"
    granted: bool


class RiaSecPayload(BaseModel):
    responses: Dict[str, int]


def public_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Never return answer keys to the browser."""
    return {key: value for key, value in item.items() if key not in {"answer"}}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "iaq-api", "mode": "development_demo"}


@app.get("/me")
def me() -> Dict[str, Any]:
    return {"id": "demo-student", "name": "Ari Pratama", "role": "student", "consented": True}


@app.get("/assessments")
def assessments() -> List[Dict[str, Any]]:
    return [{"id": "iaq-cognitive", "name": "IAQ Cognitive Profile", "version": "IAQ-COG-0.3", "status": "experimental", "domains": list(DOMAINS), "estimated_minutes": 12}]


@app.post("/assessments/{assessment_id}/sessions")
def create_session(assessment_id: str, payload: SessionCreate) -> Dict[str, Any]:
    if assessment_id != "iaq-cognitive":
        raise HTTPException(404, "Assessment version unavailable")
    session_id = str(uuid4())
    SESSIONS[session_id] = {"id": session_id, "assessment_id": assessment_id, "assessment_version": payload.assessment_version, "mode": payload.mode, "status": "created", "responses": {}, "created_at": NOW(), "user_id": "demo-student"}
    return {"id": session_id, "assessment_version": payload.assessment_version, "status": "created"}


@app.get("/sessions/{session_id}")
def get_session(session_id: str) -> Dict[str, Any]:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {key: value for key, value in session.items() if key != "responses"} | {"answered_count": len(session["responses"])}


@app.post("/sessions/{session_id}/start")
def start_session(session_id: str) -> Dict[str, Any]:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    session["status"] = "in_progress"
    session["started_at"] = NOW()
    return {"status": session["status"], "next_item": public_item(next(iter(ITEMS.values())))}


@app.get("/sessions/{session_id}/next-item")
def next_item(session_id: str) -> Dict[str, Any]:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    for item in ITEMS.values():
        if item["id"] not in session["responses"]:
            return public_item(item)
    return {"complete": True}


@app.post("/sessions/{session_id}/responses")
def submit_response(session_id: str, payload: ResponseCreate, idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key")) -> Dict[str, Any]:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    item = ITEMS.get(payload.item_id)
    if not item:
        raise HTTPException(422, "Item is unavailable")
    if payload.item_id in session["responses"]:
        return {"accepted": True, "duplicate": True, "item_id": payload.item_id}
    session["responses"][payload.item_id] = {"item_id": payload.item_id, "answer": payload.answer, "response_time_ms": payload.response_time_ms, "presented_order": payload.presented_order, "data_origin": "REAL_PILOT"}
    return {"accepted": True, "duplicate": False, "item_id": payload.item_id, "answered_count": len(session["responses"])}


@app.post("/sessions/{session_id}/events")
def record_event(session_id: str, payload: EventCreate) -> Dict[str, Any]:
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    event = {"id": str(uuid4()), "session_id": session_id, "event_type": payload.event_type, "metadata": payload.metadata, "created_at": NOW()}
    EVENTS.append(event)
    return {"accepted": True, "event_id": event["id"]}


@app.post("/sessions/{session_id}/pause")
def pause_session(session_id: str) -> Dict[str, str]:
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    SESSIONS[session_id]["status"] = "paused"
    return {"status": "paused"}


@app.post("/sessions/{session_id}/resume")
def resume_session(session_id: str) -> Dict[str, str]:
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    SESSIONS[session_id]["status"] = "in_progress"
    return {"status": "in_progress"}


@app.post("/sessions/{session_id}/submit")
def submit_session(session_id: str) -> Dict[str, Any]:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    item_domains = {key: value["domain"] for key, value in ITEMS.items()}
    item_keys = {key: value["answer"] for key, value in ITEMS.items()}
    score = score_domains(session["responses"].values(), item_domains, item_keys)
    quality = classify_session_quality([int(value["response_time_ms"]) for value in session["responses"].values()], sum(1 for event in EVENTS if event["session_id"] == session_id and event["event_type"] == "interruption"))
    result_id = str(uuid4())
    RESULTS[result_id] = {"id": result_id, "session_id": session_id, "assessment_version": session["assessment_version"], "score_version": score.score_version, "composite": score.composite, "domain_scores": score.domain_scores, "confidence": score.confidence, "quality": quality, "created_at": NOW(), "disclaimer": "This V1.0 result is an experimental educational profile, not a clinical diagnosis or officially normed IQ score."}
    session["status"] = "complete"
    session["result_id"] = result_id
    return RESULTS[result_id]


@app.get("/results/{result_id}")
def get_result(result_id: str) -> Dict[str, Any]:
    if result_id not in RESULTS:
        raise HTTPException(404, "Result not found")
    return RESULTS[result_id]


@app.get("/questionnaires")
def questionnaires() -> List[Dict[str, Any]]:
    return [{"id": "compass-v1", "name": "IAQ Compass", "version": "RIASEC-PROVISIONAL-1", "sections": ["interests", "subjects", "work_values", "environment", "evidence", "constraints"]}]


@app.post("/questionnaires/{questionnaire_id}/responses")
def questionnaire_responses(questionnaire_id: str, payload: RiaSecPayload) -> Dict[str, Any]:
    if questionnaire_id != "compass-v1":
        raise HTTPException(404, "Questionnaire not found")
    return score_riasec(payload.responses)


@app.post("/consents")
def create_consent(payload: ConsentCreate) -> Dict[str, Any]:
    return {"id": str(uuid4()), "version": payload.consent_version, "purpose": payload.purpose, "granted": payload.granted, "recorded_at": NOW()}


@app.get("/majors")
def majors() -> List[Dict[str, Any]]:
    return [{key: value for key, value in major.items() if key != "vector"} for major in MAJORS]


@app.get("/recommendations")
def recommendations() -> Dict[str, Any]:
    cognitive = {domain: 70 for domain in DOMAINS}
    interests = {"I": 92, "A": 78, "C": 65, "R": 42, "S": 35, "E": 28}
    return {"version": "MATCH-V1", "recommendations": [{**{key: value for key, value in major.items() if key != "vector"}, **major_fit(cognitive, interests, 72, major["vector"]), "confidence": recommendation_confidence(7, .34, 5, 24)} for major in MAJORS], "explanations": {"method": "weighted transparent fit with evidence and confidence; not destiny", "warnings": ["experimental_profile", "no_population_norms"]}}


@app.post("/majors/{major_id}/save")
def save_major(major_id: str) -> Dict[str, Any]:
    SAVED_MAJORS.setdefault("demo-student", [])
    if major_id not in SAVED_MAJORS["demo-student"]:
        SAVED_MAJORS["demo-student"].append(major_id)
    return {"saved": True, "major_id": major_id}


@app.delete("/majors/{major_id}/save")
def unsave_major(major_id: str) -> Dict[str, Any]:
    SAVED_MAJORS.setdefault("demo-student", [])
    SAVED_MAJORS["demo-student"] = [item for item in SAVED_MAJORS["demo-student"] if item != major_id]
    return {"saved": False, "major_id": major_id}


@app.get("/tracker")
def tracker() -> Dict[str, Any]:
    return {"student_id": "demo-student", "assessment_history": [{"date": "2026-08-12", "version": "IAQ-COG-0.3", "confidence": "moderate"}], "interest_evolution": [{"date": "2026-09-05", "code": "IAC"}], "readiness": {"evidence_count": 5, "projects": 2}, "saved_majors": SAVED_MAJORS.get("demo-student", [])}


@app.get("/counselor/students")
def counselor_students() -> Dict[str, Any]:
    return {"students": [{"id": "student-01", "name": "Lena Suryani", "consent": "granted", "assessment": "complete", "confidence": "high"}, {"id": "student-02", "name": "Fajar Kusuma", "consent": "granted", "assessment": "in_progress", "confidence": "pending"}]}


@app.get("/admin/items")
def admin_items(status: Optional[str] = Query(default=None), domain: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    items = list(ITEMS.values())
    if status:
        items = [item for item in items if item["status"] == status]
    if domain:
        items = [item for item in items if item["domain"] == domain]
    return {"items": [public_item(item) for item in items], "total": len(items)}
