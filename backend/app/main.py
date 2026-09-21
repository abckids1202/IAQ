"""FastAPI boundary for the IAQ V1.0 pilot baseline.

The default local store is intentionally small and dependency-light so the demo
can run without an external database. The migration in migrations/ is the
production persistence contract; swap the store behind these endpoints when
connecting PostgreSQL.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import random
import re
import hashlib
import json
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4
from functools import wraps
from threading import RLock

# Serialize read/check/write transitions in the single-process local pilot.
# This is not a replacement for transactional database locks in production.
FLOW_LOCK = RLock()


def serialized_flow(function):
    @wraps(function)
    def locked(*args, **kwargs):
        with FLOW_LOCK:
            return function(*args, **kwargs)
    return locked

from fastapi import FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .domain import (
    DOMAINS,
    ITEM_DOMAINS,
    EXPERIMENTAL_IQ_SCORE_KIND,
    EXPERIMENTAL_IQ_SCORE_LABEL,
    EXPERIMENTAL_IQ_SCORE_METHOD,
    EXPERIMENTAL_IQ_SCORE_SCALE,
    EXPERIMENTAL_IQ_SCORE_VERSION,
    classify_session_quality,
    score_domains,
    score_riasec,
    major_fit,
    recommendation_confidence,
)
from .question_bank import MINIMUM_ITEMS_PER_DOMAIN, TARGET_ITEMS_PER_DOMAIN, REVIEWED_ITEMS_PER_DOMAIN, QUESTION_BANK, bank_counts, bank_is_ready, reviewed_counts, review_gate_ready
from .persistence import PostgresAssessmentStore
from . import access, ai, dataset_audit, email_delivery, evaluation, external_data, payments, review, supabase_auth
from . import staged_assessment
from .question_presentation import render_matrix_svg

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

app = FastAPI(title="IAQ API", version="0.1.0", description="Experimental educational profile API")
_configured_origins = [origin.strip() for origin in os.getenv("IAQ_ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_configured_origins, allow_origin_regex=None if os.getenv("IAQ_ENV", "development").lower() == "production" else r"https?://(127\.0\.0\.1|localhost):517[0-9]$", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

NOW = lambda: datetime.now(timezone.utc).isoformat()
DURATION_SECONDS = 35 * 60
QUESTION_COUNT = 40
DOMAIN_QUOTA = 8
SCORE_DISCLAIMER = "This IAQ IQ score is an experimental, non-normed reference estimate, not an official, clinical, diagnostic, or population IQ score. It uses a transparent transform of your complete six-domain profile; no percentile or age norm is used. Timing is shown as context and does not change the score."
VISUAL_PROMPTS = {
    "abstract_reasoning": "Which panel completes the pattern?",
    "deductive_logic": "Which conclusion must be true?",
    "numerical_reasoning": "Which option completes the sequence?",
    "visual_spatial_reasoning": "Which arrangement matches after rotation?",
}

ITEMS: Dict[str, Dict[str, Any]] = {
    "abs-01": {"id": "abs-01", "domain": "abstract_reasoning", "type": "choice", "prompt": "Each tile changes by the same rule. Which tile completes the sequence?", "options": ["A", "B", "C", "D"], "answer": "B", "status": "ACTIVE"},
    "logic-01": {"id": "logic-01", "domain": "deductive_logic", "type": "choice", "prompt": "All red notebooks are archived. This notebook is red. What must be true?", "options": ["It is archived", "It is new", "It is blue", "Nothing can be concluded"], "answer": "It is archived", "status": "ACTIVE"},
    "num-01": {"id": "num-01", "domain": "numerical_reasoning", "type": "sequence", "prompt": "Complete the sequence: 3, 6, 12, 24, __", "options": ["30", "36", "42", "48"], "answer": "48", "status": "ACTIVE"},
    "verbal-01": {"id": "verbal-01", "domain": "verbal_reasoning", "type": "choice", "prompt": "A map is to navigation as a score is to…", "options": ["Music", "Evaluation", "Paper", "Competition"], "answer": "Evaluation", "status": "ACTIVE"},
    "spatial-01": {"id": "spatial-01", "domain": "visual_spatial_reasoning", "type": "choice", "prompt": "Imagine the L-shape rotates 90° clockwise. Which direction does its short arm point?", "options": ["Up", "Down", "Left", "Right"], "answer": "Down", "status": "ACTIVE"},
    "speed-01": {"id": "speed-01", "domain": "processing_speed", "type": "speed", "prompt": "Find the only pair of matching symbols.", "options": ["A", "B", "C", "D"], "answer": "B", "status": "ACTIVE"},
}
# Local development uses the imported Dataset Lab catalog by default so the
# main application exercises the same records and visual assets as the lab.
# Production defaults to the authored bank and must pass the review gate.
ITEMS = {item["id"]: item for item in QUESTION_BANK}
ASSESSMENT_SOURCE = os.getenv("IAQ_ASSESSMENT_SOURCE", "staged" if os.getenv("IAQ_ENV", "development").lower() != "production" else "authored").lower()
if ASSESSMENT_SOURCE == "staged":
    staged_items = staged_assessment.load_items()
    if staged_items:
        ITEMS = staged_items
SESSIONS: Dict[str, Dict[str, Any]] = {}
RESULTS: Dict[str, Dict[str, Any]] = {}
EVENTS: List[Dict[str, Any]] = []
SAVED_MAJORS: Dict[str, List[str]] = {}
REPORT_DELIVERIES: Dict[str, Dict[str, Any]] = {}
PAYMENT_PROOFS: Dict[str, Dict[str, Any]] = {}
QRIS_SETTINGS: Dict[str, Any] = {"merchant_name": os.getenv("QRIS_MERCHANT_NAME", "IAQ"), "instructions": "Scan the QRIS, pay the exact amount, then upload your receipt.", "image_filename": None, "image_bytes": None, "image_content_type": None}
RESULT_IDENTITIES: Dict[str, Dict[str, Any]] = {}
MEMORY_RECALL_STARTED: Dict[str, bool] = {}
FEEDBACK: List[Dict[str, Any]] = []
AI_INSIGHTS: Dict[str, Dict[str, Any]] = {}
AI_OUTPUTS: Dict[str, Dict[str, Any]] = {}
DATABASE_URL = os.getenv("IAQ_DATABASE_URL")
PERSISTENCE = PostgresAssessmentStore(DATABASE_URL) if DATABASE_URL else None
# Imported research records use external item IDs that are not present in the
# authored Postgres item tables. Keep staged QA sessions/results in process
# memory until an external-catalog persistence adapter is implemented.
ASSESSMENT_PERSISTENCE = bool(PERSISTENCE) and ASSESSMENT_SOURCE != "staged"
if PERSISTENCE:
    try:
        persisted_qris = PERSISTENCE.get_qris_settings()
        if persisted_qris:
            QRIS_SETTINGS.update(persisted_qris)
    except Exception:
        # An old local database may not have migration 013 yet. Keep startup
        # usable and let the readiness endpoint expose the missing gate.
        pass

MAJORS = [
    {"id": "cs", "slug": "computer-science", "name": "Computer Science", "family": "Technology & systems", "vector": {"abstract_reasoning": .9, "deductive_logic": .9, "numerical_reasoning": .8}},
    {"id": "arch", "slug": "architecture", "name": "Architecture", "family": "Design & built environment", "vector": {"visual_spatial_reasoning": .95, "abstract_reasoning": .7, "numerical_reasoning": .5}},
    {"id": "data", "slug": "data-science", "name": "Data Science", "family": "Technology & analysis", "vector": {"numerical_reasoning": .95, "deductive_logic": .8, "abstract_reasoning": .8}},
    {"id": "design", "slug": "industrial-design", "name": "Industrial Design", "family": "Design & making", "vector": {"visual_spatial_reasoning": .9, "abstract_reasoning": .6, "verbal_reasoning": .4}},
    {"id": "psych", "slug": "psychology", "name": "Psychology", "family": "People & behaviour", "vector": {"verbal_reasoning": .8, "deductive_logic": .7, "abstract_reasoning": .6}},
]

INTEREST_ITEMS = [
    {"id": "R", "label": "I like building, fixing, or working with materials.", "dimension": "Realistic"},
    {"id": "I", "label": "I like investigating why something works.", "dimension": "Investigative"},
    {"id": "A", "label": "I like creating, designing, or expressing an idea.", "dimension": "Artistic"},
    {"id": "S", "label": "I like helping people learn or solve problems.", "dimension": "Social"},
    {"id": "E", "label": "I like persuading people or leading a project.", "dimension": "Enterprising"},
    {"id": "C", "label": "I like organising information and making a plan work.", "dimension": "Conventional"},
]


class SessionCreate(BaseModel):
    assessment_version: str = "IAQ-COG-0.4"
    mode: str = Field(default="complete", pattern="^(quick|complete|practice)$")
    # The language is locked into the session. The current production bank is
    # English-only; Indonesian sessions stay blocked until a separately
    # authored and reviewed item version is available.
    language: str = Field(default="en", pattern="^(en|id)$")
    age_band: str = Field(default="18-22", pattern="^(15-17|18-22|adult|unknown)$")


class ResponseCreate(BaseModel):
    item_id: str
    answer: Optional[str] = None
    answer_index: Optional[int] = Field(default=None, ge=0, le=3)
    response_type: Optional[str] = Field(default=None, pattern="^(ordered_sequence|cell_set)$")
    response: Optional[List[int]] = None
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


class ItemReviewCreate(BaseModel):
    status: str = Field(default="HUMAN_REVIEWED", pattern="^(DRAFT|AUTO_VERIFIED|HUMAN_REVIEWED|PILOT|ACTIVE|SUSPENDED|RETIRED)$")
    notes: str = ""
    decision: str = Field(default="approve", pattern="^(approve|reject|changes_requested)$")
    checks: Dict[str, bool] = Field(default_factory=dict)


class ReportDeliveryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    consent_version: str = Field(default="REPORT-DELIVERY-1.0", min_length=1, max_length=40)
    granted: bool = False
    age: Optional[int] = Field(default=None, ge=13, le=120)
    guardian_consent_id: Optional[str] = None


class InterestResponseCreate(BaseModel):
    responses: Dict[str, int]
    result_id: Optional[str] = None


class CertificateCreate(BaseModel):
    result_id: str = Field(min_length=8, max_length=80)


class AIDirectionsCreate(BaseModel):
    result_id: Optional[str] = Field(default=None, min_length=8, max_length=80)


class FeedbackCreate(BaseModel):
    message: str = Field(min_length=4, max_length=2000)
    page: str = Field(default="/", min_length=1, max_length=200)
    email: Optional[str] = Field(default=None, max_length=254)


class DevLoginCreate(BaseModel):
    user: str = Field(default="demo-student", min_length=2, max_length=120)


class OtpRequestCreate(BaseModel):
    email: str = Field(min_length=5, max_length=254)


class OtpVerifyCreate(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    code: str = Field(min_length=6, max_length=6)


class OrderCreate(BaseModel):
    product_id: str = Field(min_length=2, max_length=80)
    result_id: Optional[str] = Field(default=None, min_length=8, max_length=80)
    beneficiary_user_id: Optional[str] = Field(default=None, min_length=2, max_length=120)
    school_id: Optional[str] = Field(default=None, min_length=2, max_length=120)


class PaymentProofDecision(BaseModel):
    note: str = Field(default="", max_length=1000)


class ConsentRecordCreate(BaseModel):
    consent_version: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=1, max_length=120)
    granted: bool


class IdentityCaptureCreate(BaseModel):
    result_id: Optional[str] = Field(default=None, min_length=8, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    display_name: str = Field(min_length=2, max_length=120)
    age_band: str = Field(pattern="^(15-17|18-22|adult|unknown)$")
    consent_version: str = Field(default="PILOT-DATA-1.0", min_length=1, max_length=80)
    granted: bool = True
    guardian_email: Optional[str] = Field(default=None, max_length=254)


class GuardianConsentCreate(BaseModel):
    guardian_email: str = Field(min_length=5, max_length=254)
    consent_version: str = Field(default="GUARDIAN-PILOT-1.0", min_length=1, max_length=80)


class GuardianConsentGrant(BaseModel):
    token: str = Field(min_length=12, max_length=120)


def _header_token(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("x-iaq-session")


def current_user(request: Optional[Request] = None) -> Dict[str, Any]:
    """Resolve the authenticated identity for local or provider-backed calls.

    Unsigned-in local visitors resolve to a limited guest identity, never to a
    seeded student. Production still requires a validated Supabase token for
    saved accounts; guest assessment access is an explicit private-pilot flag.
    """
    auth_mode = os.getenv("IAQ_AUTH_MODE", "development").lower()
    if os.getenv("IAQ_ENV", "development").lower() == "production" and auth_mode != "supabase":
        raise HTTPException(503, "Production authentication is not configured")
    # A few dependency-light service/unit helpers call endpoint functions
    # without an HTTP request object. Keep that internal development context
    # deterministic for existing tests; real browser requests always have a
    # path and therefore use the guest branch below.
    if auth_mode == "development" and (request is None or not request.scope.get("path")):
        return access.USERS["demo-student"]
    token = _header_token(request)
    # Guest tokens are issued by this API and are intentionally separate from
    # Supabase JWTs. This allows a first visit to start without an account while
    # keeping staff and paid access behind the normal provider auth boundary.
    guest_user = access.user_for_token(token)
    if guest_user and guest_user.get("is_guest"):
        return guest_user
    if token and token.startswith("iaq-guest-") and PERSISTENCE:
        try:
            persisted_guest = PERSISTENCE.get_guest_user(token)
        except Exception:
            # A missing/unapplied production migration must fail closed rather
            # than silently treating an unknown token as an account.
            persisted_guest = None
        if persisted_guest:
            return persisted_guest
    if auth_mode == "supabase":
        try:
            user = supabase_auth.user_from_token(token or "")
            if PERSISTENCE:
                try:
                    roles = user.get("roles") or ["student"]
                    PERSISTENCE.ensure_user(user["id"], user.get("email", ""), user.get("display_name", "IAQ student"), user.get("age_band", "unknown"), roles[0])
                except Exception as error:
                    # A valid provider token without an application profile
                    # must not reach durable result or commerce endpoints.
                    raise HTTPException(503, "Account provisioning is temporarily unavailable") from error
            return user
        except supabase_auth.SupabaseAuthError as error:
            raise HTTPException(401, str(error)) from error
    user = access.user_for_token(token)
    if user:
        return user
    requested_user = request.headers.get("x-iaq-user") if request else None
    if requested_user and os.getenv("IAQ_AUTH_MODE", "development") == "development":
        return access.user_for_identifier(requested_user)
    return access.DEFAULT_GUEST_USER


def require_permission(user: Dict[str, Any], permission: str) -> None:
    if permission not in access.permissions_for(user):
        raise HTTPException(403, "You do not have permission to perform this action")
    staff_permissions = permission.startswith(("admin.", "content.", "school."))
    if os.getenv("IAQ_ENV", "development").lower() == "production" and staff_permissions and not user.get("mfa_verified"):
        raise HTTPException(403, "Multi-factor authentication is required for staff access")


def serialize_order(order: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in order.items() if key not in {"payment_secret", "server_key"}}


def public_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Return a strict student payload; internal provenance never leaves the API."""
    allowed = {"id", "domain", "type", "prompt", "options", "helper", "visual", "render_type", "image_url", "memory_response_type", "memory_input_length", "memory_grid_size", "memory_recall_started", "presentation_mode"}
    payload = {key: value for key, value in item.items() if key in allowed and value is not None}
    if item.get("domain") in VISUAL_PROMPTS:
        payload["prompt"] = VISUAL_PROMPTS[item["domain"]]
        payload["options"] = ["A", "B", "C", "D"]
        payload["presentation_mode"] = "visual_labels"
    if item.get("type") == "memory":
        # The transient stimulus is necessary to run delayed recall. It is
        # not the answer key and is never returned as `answer`/`answer_index`.
        payload["visual"] = item.get("memory_stimulus") or payload.get("visual")
    return {key: value for key, value in payload.items() if value is not None}


def admin_item_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    """Protected reviewer payload; answer keys never enter student routes."""
    return {
        key: item.get(key)
        for key in (
            "id", "item_family_id", "construct_id", "domain", "type", "prompt", "options", "answer",
            "explanation", "difficulty_label", "difficulty_estimate", "lifecycle_status", "status",
            "content_version", "generation_run_id", "generation_parameters", "provenance", "language",
            "render_type", "render_parameters", "data_origin", "review_required", "reviewed_at", "review_history",
        )
        if item.get(key) is not None
    } | {"review": review.review_summary(item)}


def session_for(session_id: str) -> Optional[Dict[str, Any]]:
    # Ephemeral practice sessions intentionally bypass the database even when
    # the production assessment store is configured.
    if session_id in SESSIONS:
        return SESSIONS[session_id]
    if ASSESSMENT_PERSISTENCE:
        return PERSISTENCE.get_session(session_id)
    return SESSIONS.get(session_id)


def persist_session(session: Dict[str, Any], values: Dict[str, Any]) -> None:
    if session.get("ephemeral"):
        session.update(values)
    elif ASSESSMENT_PERSISTENCE:
        PERSISTENCE.update_session(session["id"], values)
    else:
        session.update(values)


def create_randomized_form(mode: str, language: str = "en") -> List[str]:
    """Create a balanced, no-repeat form from the reviewed question bank."""
    if os.getenv("IAQ_ENV", "development").lower() == "production" and not ASSESSMENT_PERSISTENCE and mode != "practice":
        raise HTTPException(503, "Production assessments require PostgreSQL persistence")
    if os.getenv("IAQ_ENV", "development").lower() == "production" and mode != "practice" and os.getenv("IAQ_REQUIRE_REVIEWED_ITEMS", "false").lower() != "true":
        raise HTTPException(503, "Production assessments require the reviewed-item release gate")
    # Every assessment-shaped flow uses the same complete six-domain form.
    # Practice is ephemeral and unscored, but it still contains all 40 items
    # so participants never see a misleading 12-question test.
    per_domain = 8
    staged_default = "true" if os.getenv("IAQ_ENV", "development").lower() != "production" else "false"
    allow_staged = ASSESSMENT_SOURCE == "staged" and os.getenv("IAQ_ALLOW_STAGED_ITEMS", staged_default).lower() == "true" and os.getenv("IAQ_ENV", "development").lower() != "production"
    def structurally_valid(item: Dict[str, Any]) -> bool:
        domain = item.get("domain")
        if domain not in DOMAINS or not item.get("id") or not item.get("answer") or item.get("memory_protocol_incomplete"):
            return False
        if domain in VISUAL_PROMPTS:
            has_four_options = isinstance(item.get("options"), list) and len(item["options"]) == 4
            # The imported Dataset Lab and any production release must carry
            # a complete visual stimulus. The small original authored bank is
            # retained only as a local API smoke-test fallback; it predates
            # image-backed visual records and may use text options instead.
            legacy_smoke_item = (
                ASSESSMENT_SOURCE != "staged"
                and item.get("data_origin") in {"REVIEWED_CONTENT", "ORIGINAL_GENERATED"}
                and not item.get("image_url")
            )
            return has_four_options and (bool(item.get("image_url")) or legacy_smoke_item)
        if item.get("type") == "memory":
            if item.get("memory_protocol_incomplete"):
                return False
            response_type = item.get("memory_response_type")
            answer = item.get("answer")
            return response_type in {"ordered_sequence", "cell_set"} and bool(item.get("memory_input_length")) and answer not in {None, "", "[]"}
        return isinstance(item.get("options"), list) and len(item["options"]) == 4

    eligible_items = [item for item in ITEMS.values() if structurally_valid(item) and item.get("language", "en") == language and (item.get("lifecycle_status", item.get("status")) in {"PILOT", "ACTIVE"} or (allow_staged and item.get("data_origin") in {"IAQ_GENERATED_RESEARCH_DATA", "EXTERNAL_RESEARCH_DATA"}))]
    # The local development preview can still exercise the full assessment
    # contract while the generated reserve is awaiting human review. This
    # fallback is deliberately disabled whenever the pilot review gate is on.
    family_ready = all(len({item.get("item_family_id", item["id"]) for item in eligible_items if item["domain"] == domain}) >= per_domain for domain in ITEM_DOMAINS)
    if (not eligible_items or not family_ready) and os.getenv("IAQ_REQUIRE_REVIEWED_ITEMS", "false").lower() != "true" and not allow_staged:
        eligible_items = [item for item in ITEMS.values() if structurally_valid(item) and item.get("language", "en") == language and item.get("status") in {"PILOT", "ACTIVE"}]
    if os.getenv("IAQ_REQUIRE_REVIEWED_ITEMS", "false").lower() == "true" and mode != "practice":
        eligible_items = [item for item in eligible_items if review.review_summary(item)["review_ready"]]
        if not review_gate_ready(eligible_items):
            raise HTTPException(503, "The question-bank review gate requires 100 eligible reviewed items per domain")
        if not all(len({item.get("item_family_id", item["id"]) for item in eligible_items if item["domain"] == domain}) >= per_domain for domain in ITEM_DOMAINS):
            raise HTTPException(503, "The reviewed question bank does not yet contain enough distinct item families for a form")
    if not bank_is_ready(eligible_items, minimum_per_domain=per_domain):
        raise HTTPException(503, "The reviewed question bank has not reached the pilot gate yet")
    pools: Dict[str, List[str]] = {domain: [] for domain in ITEM_DOMAINS}
    for item in eligible_items:
        pools[item["domain"]].append(item["id"])
    if any(len(pools[domain]) < per_domain for domain in ITEM_DOMAINS):
        raise HTTPException(503, f"The eligible question bank does not contain {per_domain} valid items in every scored domain")
    rng = random.SystemRandom()
    selected: List[str] = []
    for domain in ITEM_DOMAINS:
        domain_items = [ITEMS[item_id] for item_id in pools[domain]]
        rng.shuffle(domain_items)
        by_family: Dict[str, List[Dict[str, Any]]] = {}
        for item in domain_items:
            by_family.setdefault(item.get("item_family_id", item["id"]), []).append(item)
        family_items = list(by_family.values())
        rng.shuffle(family_items)
        chosen: List[Dict[str, Any]] = [items[0] for items in family_items[:per_domain]]
        if len(chosen) < per_domain:
            remaining = [item for item in domain_items if item["id"] not in {chosen_item["id"] for chosen_item in chosen}]
            chosen.extend(remaining[: per_domain - len(chosen)])
        selected.extend(item["id"] for item in chosen)
    rng.shuffle(selected)
    return selected


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "iaq-api", "mode": "postgres" if PERSISTENCE else "development_demo"}


def runtime_readiness() -> Dict[str, Any]:
    """Report configuration blockers without exposing provider secrets."""
    environment = os.getenv("IAQ_ENV", "development").lower()
    production = environment == "production"
    auth_mode = os.getenv("IAQ_AUTH_MODE", "development").lower()
    payments_enabled = os.getenv("PAYMENTS_ENABLED", "true").lower() == "true"
    require_reviewed_items = os.getenv("IAQ_REQUIRE_REVIEWED_ITEMS", "false").lower() == "true"
    guardian_consent_required = os.getenv("GUARDIAN_CONSENT_REQUIRED", "true").lower() == "true"
    checks = {
        "database": bool(PERSISTENCE) if production or os.getenv("IAQ_REQUIRE_PERSISTENCE", "false").lower() == "true" else True,
        "commerce_persistence": bool(PERSISTENCE) and access.POSTGRES_ACCESS_STORE_READY and os.getenv("IAQ_ACCESS_STORE", "memory").lower() == "postgres" if production else True,
        "supabase_auth": auth_mode == "supabase" and bool(os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_JWKS_URL")) if production else True,
        "verified_age_policy": os.getenv("IAQ_REQUIRE_VERIFIED_AGE", "false").lower() == "true" if production else True,
        "guardian_consent_persistence": (not guardian_consent_required) or (bool(PERSISTENCE) and access.POSTGRES_ACCESS_STORE_READY) if production else True,
        "review_persistence": bool(PERSISTENCE) and review.POSTGRES_REVIEW_STORE_READY if production else True,
        # Use the same two-approval calculation as session creation. The old
        # lifecycle-only check could report ready while no reviewer approvals
        # existed.
        "review_gate": (bool(review.review_counts(ITEMS.values())) and review_gate_ready()) if production or require_reviewed_items else True,
        "payments": (not payments_enabled) or (bool(QRIS_SETTINGS["image_bytes"]) and os.getenv("IAQ_FULL_REPORT_PRICE_IDR", "50000").isdigit()) if production else True,
        "email": bool(os.getenv("RESEND_API_KEY")) if production else True,
        "app_base_url": bool(os.getenv("APP_BASE_URL")) if production else True,
    }
    blockers = [name for name, passed in checks.items() if not passed]
    return {
        "environment": environment,
        "status": "ready" if not blockers else "needs_configuration",
        "checks": checks,
        "blockers": blockers,
        "payment_provider": "manual_qris",
        "auth_mode": auth_mode,
        "student_sessions": "reviewed_bank_only" if require_reviewed_items else "development_pilot_bank",
        "note": "A ready response means configuration checks passed; it does not replace merchant, privacy, psychometric, or security approval.",
    }


@app.get("/ready")
def ready() -> JSONResponse:
    readiness = runtime_readiness()
    # Keep the diagnostic payload available to deploy tooling, but make an
    # unsafe production configuration fail an actual readiness probe.
    status_code = 200 if readiness["status"] == "ready" else 503
    return JSONResponse(status_code=status_code, content=readiness)


@app.get("/auth/config")
def auth_config() -> Dict[str, Any]:
    """Expose safe feature flags; provider secrets never leave the server."""
    return {
        "mode": os.getenv("IAQ_AUTH_MODE", "development"),
        "google_enabled": os.getenv("AUTH_GOOGLE_ENABLED", "false").lower() == "true",
        "email_otp_enabled": os.getenv("AUTH_EMAIL_OTP_ENABLED", "true").lower() == "true",
        "payments_enabled": os.getenv("PAYMENTS_ENABLED", "true").lower() == "true",
        "guest_enabled": os.getenv("IAQ_GUEST_ASSESSMENT_ENABLED", "true" if os.getenv("IAQ_ENV", "development").lower() != "production" else "false").lower() == "true",
        "guest_requires_account_for_saved_reports": True,
        "payment_provider": "manual_qris",
        "production_ready": runtime_readiness()["status"] == "ready" and os.getenv("IAQ_ENV", "development").lower() == "production",
        "readiness": runtime_readiness(),
    }


@app.post("/auth/guest")
def guest_login() -> Dict[str, Any]:
    """Start an unsigned-in browser session for the free pilot assessment."""
    enabled_default = "true" if os.getenv("IAQ_ENV", "development").lower() != "production" else "false"
    if os.getenv("IAQ_GUEST_ASSESSMENT_ENABLED", enabled_default).lower() != "true":
        raise HTTPException(403, "Guest assessment access is disabled. Sign in or create an account to continue.")
    token, user = access.issue_guest_session()
    if PERSISTENCE:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        PERSISTENCE.store_guest_session(user["id"], token, expires_at, user["email"], user["display_name"])
    return {"session_token": token, "user": access.public_user(user), "permissions": access.permissions_for(user), "provider": "guest"}


@app.post("/auth/dev/login")
def dev_login(payload: DevLoginCreate) -> Dict[str, Any]:
    if os.getenv("IAQ_AUTH_MODE", "development") != "development":
        raise HTTPException(404, "Development authentication is disabled")
    user = access.user_for_identifier(payload.user)
    if user["account_status"] != "active":
        raise HTTPException(403, "This account is not active")
    if "student" in user["roles"]:
        access.add_entitlement(user["id"], "assessment.free.start", "development_seed", f"free:{user['id']}", quantity=99, granted_by="system")
        access.add_entitlement(user["id"], "assessment.complete.start", "development_seed", f"complete:{user['id']}", quantity=99, granted_by="system")
        access.add_entitlement(user["id"], "assessment.complete.report", "development_seed", f"report:{user['id']}", quantity=99, granted_by="system")
    token = access.issue_dev_session(user["id"])
    return {"session_token": token, "user": access.public_user(user), "permissions": access.permissions_for(user), "provider": "development"}


@app.post("/auth/otp/request")
def request_otp(payload: OtpRequestCreate) -> Dict[str, Any]:
    if os.getenv("IAQ_AUTH_MODE", "development") != "development":
        raise HTTPException(404, "Use the configured authentication provider")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", payload.email):
        raise HTTPException(422, "Enter a valid email address")
    # The local provider uses a fixed test code and never sends real email.
    access.OTP_CODES[payload.email.lower()] = {"code": "123456", "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)}
    response: Dict[str, Any] = {"accepted": True, "delivery": "development_log", "expires_in_seconds": 600}
    if os.getenv("IAQ_AUTH_MODE", "development") == "development":
        response["development_code"] = "123456"
    return response


@app.post("/auth/otp/verify")
def verify_otp(payload: OtpVerifyCreate) -> Dict[str, Any]:
    if os.getenv("IAQ_AUTH_MODE", "development") != "development":
        raise HTTPException(404, "Use the configured authentication provider")
    record = access.OTP_CODES.get(payload.email.lower())
    if not record or record["expires_at"] <= datetime.now(timezone.utc) or payload.code != record["code"]:
        raise HTTPException(401, "That sign-in code is invalid or expired")
    user = access.get_or_create_student(payload.email)
    token = access.issue_dev_session(user["id"])
    access.OTP_CODES.pop(payload.email.lower(), None)
    return {"session_token": token, "user": access.public_user(user), "permissions": access.permissions_for(user), "provider": "development"}


@app.post("/auth/logout")
def logout(request: Request) -> Dict[str, bool]:
    token = _header_token(request)
    if token:
        access.SESSIONS.pop(token, None)
    return {"signed_out": True}


@app.get("/me/roles")
def me_roles(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    return {"user_id": user["id"], "roles": user["roles"], "active_role": user["roles"][0], "mfa_verified": user["mfa_verified"]}


@app.get("/me/permissions")
def me_permissions(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    return {"user_id": user["id"], "permissions": access.permissions_for(user)}


@app.get("/me/entitlements")
def me_entitlements(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    entitlements = [item for item in access.ENTITLEMENTS.values() if item["owner_id"] == user["id"]]
    if PERSISTENCE:
        try:
            persisted = PERSISTENCE.list_entitlements_for_user(user["id"])
        except Exception:
            persisted = []
        known = {item["id"] for item in entitlements}
        entitlements.extend(item for item in persisted if item["id"] not in known)
    return {"entitlements": entitlements}


@app.get("/me/orders")
def me_orders(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    orders = access.orders_for(user["id"])
    if PERSISTENCE:
        try:
            persisted = PERSISTENCE.list_orders_for_user(user["id"])
        except Exception:
            persisted = []
        known = {item["id"] for item in orders}
        orders.extend(item for item in persisted if item["id"] not in known)
    return {"orders": [serialize_order(order) for order in orders]}


@app.get("/products")
def products() -> Dict[str, Any]:
    return {"products": access.list_products(), "currency": "IDR", "payment_provider": "manual_qris"}


@app.get("/products/{product_id}")
def product(product_id: str) -> Dict[str, Any]:
    product_record = access.PRODUCTS.get(product_id)
    if not product_record or not product_record["active"]:
        raise HTTPException(404, "Product not found")
    return {key: value for key, value in product_record.items() if key not in {"entitlement_code", "report_code"}}


@app.post("/orders")
@serialized_flow
def create_order(payload: OrderCreate, request: Request) -> Dict[str, Any]:
    user = current_user(request)
    guest_identity = guest_identity_for(payload.result_id)
    guest_identity_active = bool(guest_identity and datetime.now(timezone.utc) < datetime.fromisoformat(guest_identity["expires_at"]))
    if not (user.get("is_guest") and guest_identity_active and guest_identity.get("user_id") == user["id"]):
        require_permission(user, "order.self.create")
    if payload.product_id == "iaq-complete":
        if not payload.result_id:
            raise HTTPException(422, "Choose a completed test to unlock")
        result = _result_record(payload.result_id, request)
        if result.get("user_id") != user["id"] or payload.beneficiary_user_id not in {None, user["id"]}:
            raise HTTPException(404, "Result not found")
        if result.get("iq_score") is None:
            raise HTTPException(409, "This result has insufficient scoring evidence; do not pay for an incomplete report")
        if has_full_report_access(user["id"], payload.result_id):
            raise HTTPException(409, "This report is already unlocked")
        if PERSISTENCE:
            try:
                existing = PERSISTENCE.get_order_for_result(user["id"], payload.result_id)
            except Exception:
                existing = None
            if existing:
                access.ORDERS[existing["id"]] = existing
                return serialize_order(existing)
        for existing in access.ORDERS.values():
            if existing.get("result_id") == payload.result_id and existing.get("purchaser_user_id") == user["id"] and existing["status"] in {"awaiting_payment", "proof_submitted", "payment_proof_rejected"}:
                return serialize_order(existing)
    try:
        order = access.create_order(user["id"], payload.product_id, payload.beneficiary_user_id, payload.school_id, payload.result_id)
    except PermissionError as error:
        raise HTTPException(403, str(error))
    except ValueError as error:
        raise HTTPException(422, str(error))
    persist_order(order)
    return serialize_order(order)


def _authorized_order(order: Dict[str, Any], user: Dict[str, Any]) -> None:
    if user["id"] not in {order["purchaser_user_id"], order["beneficiary_user_id"]} and "platform_admin" not in user["roles"]:
        raise HTTPException(404, "Order not found")


def order_for(order_id: str) -> Optional[Dict[str, Any]]:
    order = access.ORDERS.get(order_id)
    if order or not PERSISTENCE:
        return order
    try:
        order = PERSISTENCE.get_order(order_id)
    except Exception:
        order = None
    if order:
        access.ORDERS[order_id] = order
    return order


def persist_order(order: Dict[str, Any]) -> None:
    if PERSISTENCE:
        PERSISTENCE.store_order(order)


@app.get("/orders/{order_id}")
def get_order(order_id: str, request: Request) -> Dict[str, Any]:
    order = order_for(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    _authorized_order(order, current_user(request))
    return serialize_order(order)


@app.post("/orders/{order_id}/checkout")
def checkout_order(order_id: str, request: Request) -> Dict[str, Any]:
    user = current_user(request)
    order = order_for(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    _authorized_order(order, user)
    if order["status"] == "fulfilled":
        return {"order": serialize_order(order), "payment_attempt": None, "message": "Access is already active."}
    if os.getenv("PAYMENTS_ENABLED", "true").lower() != "true":
        raise HTTPException(503, "Payments are not enabled")
    attempt = access.create_payment_attempt(order_id)
    attempt["provider"] = "manual_qris"
    attempt["updated_at"] = NOW()
    persist_order(order)
    return {"order": serialize_order(order), "payment_attempt": attempt, "qris": {"merchant_name": QRIS_SETTINGS["merchant_name"], "instructions": QRIS_SETTINGS["instructions"], "image_available": bool(QRIS_SETTINGS["image_bytes"]), "image_url": "/payment-settings/qris/image" if QRIS_SETTINGS["image_bytes"] else None}, "message": "Scan the QRIS, pay the exact amount, then upload your receipt. Access is unlocked only after admin verification."}


@app.get("/payment-settings/qris")
def qris_settings() -> Dict[str, Any]:
    return {"merchant_name": QRIS_SETTINGS["merchant_name"], "instructions": QRIS_SETTINGS["instructions"], "image_available": bool(QRIS_SETTINGS["image_bytes"]), "image_url": "/payment-settings/qris/image" if QRIS_SETTINGS["image_bytes"] else None}


@app.get("/payment-settings/qris/image")
def qris_image() -> Response:
    if not QRIS_SETTINGS["image_bytes"]:
        raise HTTPException(404, "QRIS image is not configured")
    return Response(content=QRIS_SETTINGS["image_bytes"], media_type=QRIS_SETTINGS["image_content_type"] or "image/png", headers={"Cache-Control": "private, max-age=300"})


@app.post("/orders/{order_id}/payment-proof")
async def submit_payment_proof(order_id: str, receipt: UploadFile = File(...), transaction_ref: Optional[str] = None, idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"), request: Request = None) -> Dict[str, Any]:
    order = order_for(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    user = current_user(request)
    _authorized_order(order, user)
    if order["purchaser_user_id"] != user["id"] and "platform_admin" not in user.get("roles", []):
        raise HTTPException(403, "Only the purchaser can submit payment proof")
    if order["status"] == "fulfilled":
        return {"accepted": True, "status": "fulfilled", "order_id": order_id}
    if order["status"] == "proof_submitted":
        raise HTTPException(409, "A payment proof for this order is already under review")
    if order["status"] not in {"awaiting_payment", "payment_proof_rejected"}:
        raise HTTPException(409, "This order cannot accept payment proof in its current state")
    if receipt.content_type not in {"image/png", "image/jpeg", "image/webp", "application/pdf"}:
        raise HTTPException(415, "Upload a PNG, JPG, WEBP, or PDF receipt")
    if idempotency_key and idempotency_key in PAYMENT_PROOFS:
        previous = PAYMENT_PROOFS[idempotency_key]
        if previous["order_id"] != order_id or previous["user_id"] != user["id"]:
            raise HTTPException(409, "This idempotency key belongs to another payment request")
        return {"accepted": True, **{key: value for key, value in previous.items() if key != "content"}}
    if idempotency_key and PERSISTENCE:
        previous = PERSISTENCE.get_payment_proof_by_idempotency(idempotency_key)
        if previous:
            if previous["order_id"] != order_id or previous["user_id"] not in {user["id"], PERSISTENCE._db_user_id(user["id"])}:
                raise HTTPException(409, "This idempotency key belongs to another payment request")
            PAYMENT_PROOFS[idempotency_key] = previous
            return {"accepted": True, **{key: value for key, value in previous.items() if key != "content"}}
    content = await receipt.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "Payment receipts must be 5 MB or smaller")
    proof_id = str(uuid4())
    proof = {"id": proof_id, "order_id": order_id, "user_id": user["id"], "filename": receipt.filename or "receipt", "content_type": receipt.content_type, "size": len(content), "transaction_ref": (transaction_ref or "").strip()[:120] or None, "status": "under_review", "note": "", "created_at": NOW(), "updated_at": NOW(), "content": content}
    PAYMENT_PROOFS[idempotency_key or f"proof:{proof_id}"] = proof
    order["status"] = "proof_submitted"
    order["updated_at"] = NOW()
    persist_order(order)
    if PERSISTENCE:
        PERSISTENCE.store_payment_proof(proof, content, idempotency_key or f"proof:{proof_id}")
    access.record_audit(user["id"], "payment.proof_submitted", "order", order_id, {"proof_id": proof_id})
    return {"accepted": True, "id": proof_id, "order_id": order_id, "status": proof["status"], "created_at": proof["created_at"]}


@app.get("/admin/payment-proofs")
def admin_payment_proofs(request: Request) -> Dict[str, Any]:
    require_permission(current_user(request), "admin.payments.read")
    proofs = list(PAYMENT_PROOFS.values())
    if PERSISTENCE:
        persisted = [proof for proof in PERSISTENCE.list_payment_proofs() if proof]
        known = {proof["id"] for proof in proofs}
        proofs.extend(proof for proof in persisted if proof["id"] not in known)
    return {"proofs": [{key: value for key, value in proof.items() if key != "content"} for proof in proofs]}


@app.post("/admin/payment-proofs/{proof_id}/approve")
@serialized_flow
def approve_payment_proof(proof_id: str, payload: PaymentProofDecision, request: Request) -> Dict[str, Any]:
    admin = current_user(request)
    require_permission(admin, "admin.entitlements.manage")
    proof = next((value for value in PAYMENT_PROOFS.values() if value["id"] == proof_id), None)
    if not proof and PERSISTENCE:
        proof = PERSISTENCE.get_payment_proof(proof_id)
        if proof:
            PAYMENT_PROOFS[f"persisted:{proof_id}"] = proof
    if not proof:
        raise HTTPException(404, "Payment proof not found")
    if proof["status"] == "approved":
        order = order_for(proof["order_id"])
        return {"approved": True, "order": serialize_order(order)} if order else {"approved": True, "status": "approved"}
    if proof["status"] != "under_review":
        raise HTTPException(409, "This payment proof is no longer awaiting review")
    order = order_for(proof["order_id"])
    if not order:
        raise HTTPException(404, "Order not found")
    proof.update({"status": "approved", "note": payload.note, "reviewed_by": admin["id"], "updated_at": NOW()})
    access.fulfill_order(order["id"], "manual_qris_admin_verified")
    persist_order(order)
    if PERSISTENCE:
        product = access.PRODUCTS[order["product_id"]]
        PERSISTENCE.store_entitlements_for_order(order, [product["entitlement_code"], product["report_code"]], admin["id"])
        PERSISTENCE.update_payment_proof(proof_id, "approved", proof["note"], admin["id"])
    access.record_audit(admin["id"], "payment.proof_approved", "payment_proof", proof_id, {"order_id": order["id"]})
    return {"approved": True, "order": serialize_order(order)}


@app.post("/admin/payment-proofs/{proof_id}/reject")
@serialized_flow
def reject_payment_proof(proof_id: str, payload: PaymentProofDecision, request: Request) -> Dict[str, Any]:
    admin = current_user(request)
    require_permission(admin, "admin.entitlements.manage")
    proof = next((value for value in PAYMENT_PROOFS.values() if value["id"] == proof_id), None)
    if not proof and PERSISTENCE:
        proof = PERSISTENCE.get_payment_proof(proof_id)
        if proof:
            PAYMENT_PROOFS[f"persisted:{proof_id}"] = proof
    if not proof:
        raise HTTPException(404, "Payment proof not found")
    if proof["status"] == "rejected":
        return {"rejected": True, "status": proof["status"]}
    if proof["status"] != "under_review":
        raise HTTPException(409, "This payment proof is no longer awaiting review")
    proof.update({"status": "rejected", "note": payload.note, "reviewed_by": admin["id"], "updated_at": NOW()})
    order = order_for(proof["order_id"])
    if not order:
        raise HTTPException(404, "Order not found")
    order["status"] = "payment_proof_rejected"
    order["updated_at"] = NOW()
    persist_order(order)
    if PERSISTENCE:
        PERSISTENCE.update_payment_proof(proof_id, "rejected", proof["note"], admin["id"])
    access.record_audit(admin["id"], "payment.proof_rejected", "payment_proof", proof_id, {"order_id": proof["order_id"]})
    return {"rejected": True, "status": proof["status"], "note": proof["note"]}


@app.post("/admin/payment-settings/qris")
async def update_qris_settings(merchant_name: str, instructions: str, image: UploadFile = File(...), request: Request = None) -> Dict[str, Any]:
    admin = current_user(request)
    require_permission(admin, "admin.products.manage")
    if image.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(415, "QRIS must be a PNG, JPG, or WEBP image")
    content = await image.read(2 * 1024 * 1024 + 1)
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(413, "QRIS images must be 2 MB or smaller")
    QRIS_SETTINGS.update({"merchant_name": merchant_name.strip()[:120] or "IAQ", "instructions": instructions.strip()[:500] or "Scan the QRIS, pay the exact amount, then upload your receipt.", "image_filename": image.filename, "image_bytes": content, "image_content_type": image.content_type})
    if PERSISTENCE:
        PERSISTENCE.store_qris_settings(QRIS_SETTINGS, admin["id"])
    access.record_audit(admin["id"], "payment.qris_updated", "payment_settings", "qris", {})
    return qris_settings()


@app.get("/orders/{order_id}/status")
def order_status(order_id: str, request: Request) -> Dict[str, Any]:
    order = order_for(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    _authorized_order(order, current_user(request))
    attempt = next((item for item in access.PAYMENT_ATTEMPTS.values() if item["order_id"] == order_id), None)
    entitlements = [item for item in access.ENTITLEMENTS.values() if item["owner_id"] == order["beneficiary_user_id"] and item["source_id"] == order_id]
    if PERSISTENCE:
        try:
            persisted = [item for item in PERSISTENCE.list_entitlements_for_user(order["beneficiary_user_id"]) if item.get("source_id") == order_id]
        except Exception:
            persisted = []
        known = {item["id"] for item in entitlements}
        entitlements.extend(item for item in persisted if item["id"] not in known)
    return {"order": serialize_order(order), "payment_attempt": attempt, "entitlements": entitlements}


@app.post("/payments/mock/{order_id}/settle")
def settle_mock_payment(order_id: str, request: Request) -> Dict[str, Any]:
    if os.getenv("IAQ_AUTH_MODE", "development") != "development":
        raise HTTPException(404, "Mock payment is disabled")
    user = current_user(request)
    try:
        order = access.settle_mock_payment(order_id, user["id"])
    except KeyError as error:
        raise HTTPException(404, str(error))
    except PermissionError as error:
        raise HTTPException(403, str(error))
    return {"order": serialize_order(order), "verified": True, "entitlement_created": order["status"] == "fulfilled"}


@app.post("/payments/midtrans/notification")
async def midtrans_notification(request: Request) -> Dict[str, Any]:
    # This route remains only as an explicit migration response. IAQ uses
    # manually reviewed BCA QRIS proofs; no third-party webhook may grant an
    # entitlement in this release.
    raise HTTPException(410, "Midtrans notifications are disabled; submit a manual QRIS proof instead")


@app.get("/schools/{school_id}/seats")
def school_seats(school_id: str, request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if user.get("school_id") != school_id and "platform_admin" not in user["roles"]:
        raise HTTPException(404, "School not found")
    if not any(permission in access.permissions_for(user) for permission in ("school.seats.read", "admin.schools.manage")):
        raise HTTPException(403, "School seat access is not allowed")
    return access.school_seats(school_id)


class SeatAllocateCreate(BaseModel):
    student_id: str = Field(min_length=2, max_length=120)


@app.post("/schools/{school_id}/seats/allocate")
def allocate_school_seat(school_id: str, payload: SeatAllocateCreate, request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if user.get("school_id") != school_id and "platform_admin" not in user["roles"]:
        raise HTTPException(404, "School not found")
    require_permission(user, "school.seats.allocate")
    if payload.student_id not in access.USERS or "student" not in access.USERS[payload.student_id]["roles"]:
        raise HTTPException(422, "The beneficiary must be a known student account")
    try:
        return access.allocate_school_seat(school_id, payload.student_id, user["id"])
    except ValueError as error:
        raise HTTPException(409, str(error))


@app.post("/feedback")
def create_feedback(payload: FeedbackCreate) -> Dict[str, Any]:
    feedback = {"id": str(uuid4()), "message": payload.message.strip(), "page": payload.page, "email": payload.email.strip().lower() if payload.email else None, "created_at": NOW()}
    FEEDBACK.append(feedback)
    if PERSISTENCE:
        PERSISTENCE.store_feedback(feedback)
    return {"accepted": True, "id": feedback["id"]}


@app.get("/me")
def me(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    return {"id": user["id"], "name": user["display_name"], "display_name": user["display_name"], "email": user["email"], "roles": user["roles"], "role": user["roles"][0], "account_status": user["account_status"], "age_band": user.get("age_band", "unknown"), "mfa_verified": user["mfa_verified"], "is_guest": bool(user.get("is_guest", False)), "consented": True}


@app.get("/assessments")
def assessments() -> List[Dict[str, Any]]:
    available_languages = sorted({item.get("language", "en") for item in ITEMS.values() if item.get("language")})
    return [{"id": "iaq-cognitive", "name": "IAQ Cognitive Profile", "version": "IAQ-COG-0.4", "status": "experimental", "domains": list(DOMAINS), "question_bank_count": len(ITEMS), "questions_per_complete_form": QUESTION_COUNT, "questions_per_quick_form": len(DOMAINS) * 2, "duration_seconds": DURATION_SECONDS, "estimated_minutes": 35, "domain_quota": DOMAIN_QUOTA, "available_languages": available_languages, "default_language": "id", "scored_language": "en", "score_kind": "provisional_domain_signal", "iq_score_kind": EXPERIMENTAL_IQ_SCORE_KIND, "iq_score_label": EXPERIMENTAL_IQ_SCORE_LABEL, "iq_score_version": EXPERIMENTAL_IQ_SCORE_VERSION, "iq_score_scale": EXPERIMENTAL_IQ_SCORE_SCALE, "iq_score_method": EXPERIMENTAL_IQ_SCORE_METHOD, "official_iq_enabled": False}]


def create_session(assessment_id: str, payload: SessionCreate, request: Request = None) -> Dict[str, Any]:
    if assessment_id != "iaq-cognitive":
        raise HTTPException(404, "Assessment version unavailable")
    user = current_user(request)
    trusted_age_band = str(user.get("age_band", "unknown"))
    # Local previews intentionally use the seeded demo identity. Until the
    # Supabase profile-provisioning flow is enabled, let the local age gate
    # exercise its self-reported branch without treating demo metadata as a
    # production identity claim.
    if os.getenv("IAQ_AUTH_MODE", "development").lower() == "development" and os.getenv("IAQ_REQUIRE_VERIFIED_AGE", "false").lower() != "true":
        trusted_age_band = payload.age_band
    if (payload.age_band == "15-17" or trusted_age_band == "15-17") and payload.mode != "practice":
        raise HTTPException(403, "People aged 15–17 can use practice mode until guardian consent is available")
    if payload.mode != "practice" and payload.age_band != "18-22":
        raise HTTPException(403, "The scored pilot is currently available only for ages 18–22")
    if payload.language == "id" and not any(item.get("language", "en") == "id" for item in ITEMS.values()):
        raise HTTPException(503, "The Indonesian assessment version is not released yet; choose English for this pilot")

    def has_start_credit(code: str) -> bool:
        if access.has_entitlement(user["id"], code):
            return True
        if PERSISTENCE:
            try:
                return any(item["code"] == code and item["status"] == "active" and item["remaining_quantity"] > 0 for item in PERSISTENCE.list_entitlements_for_user(user["id"]))
            except Exception:
                return False
        return False

    def owned_results() -> List[Dict[str, Any]]:
        memory = [item for item in RESULTS.values() if item.get("user_id") == user["id"]]
        if not PERSISTENCE:
            return memory
        try:
            persisted = PERSISTENCE.list_results_for_user(user["id"])
        except Exception:
            persisted = []
        known = {item["id"] for item in memory}
        return memory + [item for item in persisted if item["id"] not in known]

    # A normal account receives one free scored attempt. A paid start credit
    # (created by an approved report/reassessment purchase) explicitly allows
    # another attempt. This rule is server-side and survives browser resets.
    paid_start = has_start_credit("assessment.complete.start")
    if payload.mode != "practice" and not user.get("is_guest") and owned_results() and not paid_start:
        raise HTTPException(409, "This account has already completed its free assessment. Unlock another attempt to continue.")

    access_code = "assessment.complete.start" if paid_start else "assessment.free.start"
    if payload.mode != "practice" and not has_start_credit(access_code):
        raise HTTPException(402, "A free assessment start entitlement is required")
    session_id = str(uuid4())
    created_at = datetime.now(timezone.utc)
    deadline_at = created_at + timedelta(seconds=DURATION_SECONDS)
    item_order = create_randomized_form(payload.mode, payload.language)
    if payload.mode != "practice":
        consumed = access.consume_entitlement(user["id"], access_code, session_id)
        if not consumed and PERSISTENCE:
            try:
                consumed = PERSISTENCE.consume_entitlement(user["id"], access_code, session_id)
            except Exception:
                consumed = False
        if not consumed:
            raise HTTPException(409, "Assessment access could not be reserved. Please try again.")
    session = {"id": session_id, "assessment_id": assessment_id, "assessment_version": payload.assessment_version, "mode": payload.mode, "language": payload.language, "age_band": payload.age_band, "status": "created", "responses": {}, "item_order": item_order, "created_at": created_at.isoformat(), "deadline_at": deadline_at.isoformat(), "duration_seconds": DURATION_SECONDS, "user_id": user["id"], "access_code": access_code if payload.mode != "practice" else None, "consent_snapshot": {}, "ephemeral": payload.mode == "practice", "data_origin": "PRACTICE" if payload.mode == "practice" else "REAL_PILOT"}
    # Practice is intentionally held in process memory and never written to
    # the assessment/results tables.
    if ASSESSMENT_PERSISTENCE and not session["ephemeral"]:
        PERSISTENCE.create_session(session)
    else:
        SESSIONS[session_id] = session
    return {"id": session_id, "assessment_version": payload.assessment_version, "language": payload.language, "age_band": payload.age_band, "mode": payload.mode, "status": "created", "deadline_at": deadline_at.isoformat(), "duration_seconds": DURATION_SECONDS, "question_count": len(item_order), "domain_quota": DOMAIN_QUOTA, "practice": session["ephemeral"]}


@app.post("/assessments/{assessment_id}/sessions")
def create_session_endpoint(assessment_id: str, payload: SessionCreate, request: Request) -> Dict[str, Any]:
    return create_session(assessment_id, payload, request)


@app.get("/sessions/{session_id}")
def get_session(session_id: str, request: Request) -> Dict[str, Any]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    require_session_owner(session, request)
    return {key: value for key, value in session.items() if key not in {"responses", "item_order"}} | {"answered_count": len(session["responses"]), "question_count": len(session["item_order"])}


@app.post("/sessions/{session_id}/start")
def start_session(session_id: str, request: Request = None) -> Dict[str, Any]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    require_session_owner(session, request)
    if session["status"] == "complete":
        raise HTTPException(409, "Assessment is already complete")
    if session["status"] == "timed_out":
        raise HTTPException(409, "Assessment time has ended")
    if session_expired(session):
        persist_session(session, {"status": "timed_out"})
        raise HTTPException(409, "Assessment time has ended")
    started_at = session.get("started_at") or NOW()
    persist_session(session, {"status": "in_progress", "started_at": started_at})
    session["status"] = "in_progress"
    session["started_at"] = started_at
    return {"status": session["status"], "next_item": next_item(session_id, request)}


def session_expired(session: Dict[str, Any]) -> bool:
    return datetime.now(timezone.utc) >= datetime.fromisoformat(session["deadline_at"])


def require_session_owner(session: Dict[str, Any], request: Optional[Request]) -> None:
    if not request:
        return
    user = current_user(request)
    if session.get("user_id") != user.get("id") and "platform_admin" not in user.get("roles", []):
        raise HTTPException(404, "Session not found")


@app.get("/sessions/{session_id}/next-item")
def next_item(session_id: str, request: Request = None) -> Dict[str, Any]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    require_session_owner(session, request)
    if session["status"] == "complete":
        return {"complete": True}
    if session["status"] == "in_progress" and session_expired(session):
        persist_session(session, {"status": "timed_out"})
        session["status"] = "timed_out"
        return {"complete": True, "expired": True}
    for item_id in session["item_order"]:
        if item_id not in session["responses"]:
            safe = public_item(ITEMS[item_id])
            if MEMORY_RECALL_STARTED.get(f"{session_id}:{item_id}") or f"recall_started:{item_id}" in session.get("events", {}):
                safe.pop("visual", None)
                safe.pop("image_url", None)
                safe["memory_recall_started"] = True
            return safe
    return {"complete": True}


@app.post("/sessions/{session_id}/items/{item_id}/begin-recall")
def begin_memory_recall(session_id: str, item_id: str, request: Request = None) -> Dict[str, Any]:
    """Advance a memory item to recall without exposing its answer.

    The Dataset Lab and the student assessment use the same one-way protocol:
    once recall begins, the study stimulus is never returned again for that
    item. The server records the transition so a refresh cannot replay it.
    """
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    require_session_owner(session, request)
    if session.get("status") in {"complete", "timed_out"} or session_expired(session):
        raise HTTPException(409, "Assessment time has ended")
    item = ITEMS.get(item_id)
    if not item or item_id not in session.get("item_order", []):
        raise HTTPException(404, "Memory item not found")
    if item_id != next((key for key in session["item_order"] if key not in session["responses"]), None):
        raise HTTPException(409, "Complete the current item first")
    response_type = item.get("memory_response_type")
    if item.get("type") != "memory" or response_type not in {"ordered_sequence", "cell_set"}:
        raise HTTPException(422, "This item does not use a memory recall protocol")
    recall_key = f"recall_started:{item_id}"
    if recall_key not in session.setdefault("events", {}):
        session["events"][recall_key] = NOW()
        MEMORY_RECALL_STARTED[f"{session_id}:{item_id}"] = True
        if ASSESSMENT_PERSISTENCE and not session.get("ephemeral"):
            PERSISTENCE.insert_event(session_id, str(uuid4()), "memory_recall_started", {"item_id": item_id})
    return {"item_id": item_id, "response_type": response_type, "input_length": item.get("memory_input_length"), "grid_size": item.get("memory_grid_size"), "labels": {"begin": "Begin recall", "submit": "Check recall"}}


@app.post("/sessions/{session_id}/responses")
@serialized_flow
def submit_response(session_id: str, payload: ResponseCreate, idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"), request: Request = None) -> Dict[str, Any]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    require_session_owner(session, request)
    if session["status"] in {"complete", "timed_out"}:
        raise HTTPException(409, "This assessment can no longer accept answers")
    if session_expired(session):
        persist_session(session, {"status": "timed_out"})
        session["status"] = "timed_out"
        raise HTTPException(409, "Assessment time has ended")
    item = ITEMS.get(payload.item_id)
    if not item:
        raise HTTPException(422, "Item is unavailable")
    if payload.item_id not in session["item_order"]:
        raise HTTPException(422, "Item is not part of this randomized form")
    expected_order = session["item_order"].index(payload.item_id)
    if payload.presented_order != expected_order:
        raise HTTPException(422, "The item order does not match this assessment session")
    if payload.item_id in session["responses"]:
        return {"accepted": True, "duplicate": True, "item_id": payload.item_id}
    if payload.item_id != next((key for key in session["item_order"] if key not in session["responses"]), None):
        raise HTTPException(409, "Complete the current item first")
    stored_answer = payload.answer
    if item.get("memory_response_type") in {"ordered_sequence", "cell_set"}:
        if not MEMORY_RECALL_STARTED.get(f"{session_id}:{payload.item_id}") and f"recall_started:{payload.item_id}" not in session.get("events", {}):
            raise HTTPException(409, "Begin recall before submitting a memory response")
        if payload.response_type and payload.response_type != item.get("memory_response_type"):
            raise HTTPException(422, "Memory response type does not match this item")
        try:
            memory_response = payload.response if payload.response is not None else json.loads(payload.answer or "")
        except (TypeError, json.JSONDecodeError) as error:
            raise HTTPException(422, "Memory response is not valid JSON") from error
        if not isinstance(memory_response, list) or any(not isinstance(value, int) or isinstance(value, bool) for value in memory_response):
            raise HTTPException(422, "Memory response is unavailable")
        if item["memory_response_type"] == "ordered_sequence":
            valid_memory_response = len(memory_response) == item.get("memory_input_length") and all(-99999 <= value <= 99999 for value in memory_response)
        else:
            grid_size = item.get("memory_grid_size") or 0
            max_cell = grid_size * grid_size
            valid_memory_response = len(memory_response) == len(set(memory_response)) and all(0 <= value < max_cell for value in memory_response)
        if not valid_memory_response:
            raise HTTPException(422, "Memory response is outside the allowed format")
        stored_answer = json.dumps(sorted(memory_response) if item["memory_response_type"] == "cell_set" else memory_response, separators=(",", ":"))
    elif payload.answer not in item["options"]:
        if payload.answer_index is None or payload.answer_index >= len(item["options"]):
            raise HTTPException(422, "Answer option is unavailable")
        stored_answer = item["options"][payload.answer_index]
    elif payload.answer_index is not None:
        if payload.answer_index >= len(item["options"]):
            raise HTTPException(422, "Answer option is unavailable")
        stored_answer = item["options"][payload.answer_index]
    if payload.item_id in session["responses"]:
        return {"accepted": True, "duplicate": True, "item_id": payload.item_id}
    effective_idempotency_key = idempotency_key or f"response:{session_id}:{payload.item_id}"
    response = {"item_id": payload.item_id, "answer": stored_answer, "response_time_ms": payload.response_time_ms, "presented_order": payload.presented_order, "idempotency_key": effective_idempotency_key, "data_origin": "PRACTICE" if session.get("ephemeral") else "REAL_PILOT"}
    if ASSESSMENT_PERSISTENCE and not session.get("ephemeral"):
        accepted = PERSISTENCE.insert_response(session_id, payload.item_id, stored_answer or "", payload.response_time_ms, payload.presented_order, effective_idempotency_key)
        if not accepted:
            return {"accepted": True, "duplicate": True, "item_id": payload.item_id}
    else:
        session["responses"][payload.item_id] = response
    answered_count = len(session["responses"]) if not ASSESSMENT_PERSISTENCE or session.get("ephemeral") else len(session["responses"]) + 1
    return {"accepted": True, "duplicate": False, "item_id": payload.item_id, "answered_count": answered_count}


@app.post("/sessions/{session_id}/events")
def record_event(session_id: str, payload: EventCreate, request: Request = None) -> Dict[str, Any]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    require_session_owner(session, request)
    event = {"id": str(uuid4()), "session_id": session_id, "event_type": payload.event_type, "metadata": payload.metadata, "created_at": NOW()}
    if ASSESSMENT_PERSISTENCE and not session.get("ephemeral"):
        PERSISTENCE.insert_event(session_id, event["id"], payload.event_type, payload.metadata)
    else:
        EVENTS.append(event)
    return {"accepted": True, "event_id": event["id"]}


@app.post("/sessions/{session_id}/pause")
def pause_session(session_id: str, request: Request = None) -> Dict[str, str]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    require_session_owner(session, request)
    persist_session(session, {"status": "paused"})
    session["status"] = "paused"
    return {"status": "paused"}


@app.post("/sessions/{session_id}/resume")
def resume_session(session_id: str, request: Request = None) -> Dict[str, str]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    require_session_owner(session, request)
    if session.get("result_id") or session["status"] == "complete":
        raise HTTPException(409, "Assessment is already complete")
    if session_expired(session):
        raise HTTPException(409, "Assessment time has ended")
    persist_session(session, {"status": "in_progress"})
    session["status"] = "in_progress"
    return {"status": "in_progress"}


def has_full_report_access(user_id: str, result_id: Optional[str] = None) -> bool:
    """A payment grants one result, never every past or future report."""
    if not result_id:
        return False
    if PERSISTENCE:
        try:
            if PERSISTENCE.has_result_entitlement(user_id, result_id):
                return True
        except Exception:
            # Fail closed if the commerce migration is missing or unavailable.
            return False
    return any(
        grant.get("owner_id") == user_id and grant.get("status") == "active"
        and grant.get("code") in {"assessment.complete.report", "report.download"}
        and access.ORDERS.get(grant.get("source_id"), {}).get("result_id") == result_id
        and access.ORDERS.get(grant.get("source_id"), {}).get("status") == "fulfilled"
        for grant in access.ENTITLEMENTS.values()
    )


def interest_attempt_for(user_id: str, result_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Read one result-scoped interest attempt from memory, then Postgres."""
    key = f"{user_id}:{result_id}" if result_id else user_id
    attempt = access.INTEREST_ATTEMPTS.get(key)
    if attempt:
        return attempt
    if PERSISTENCE:
        try:
            attempt = PERSISTENCE.get_interest_attempt(user_id, result_id)
        except Exception:
            attempt = None
        if attempt:
            access.INTEREST_ATTEMPTS[key] = attempt
            return attempt
    return None


def guest_identity_for(result_id: str) -> Optional[Dict[str, Any]]:
    if not result_id:
        return None
    identity = RESULT_IDENTITIES.get(result_id)
    if identity or not PERSISTENCE:
        return identity
    try:
        identity = PERSISTENCE.get_guest_identity(result_id)
    except Exception:
        identity = None
    if identity:
        RESULT_IDENTITIES[result_id] = identity
    return identity


def result_projection(result: Dict[str, Any], request: Optional[Request] = None, force_full: bool = False) -> Dict[str, Any]:
    if force_full or not request:
        return {**result, "full_access": True}
    user = current_user(request)
    identity = guest_identity_for(result["id"])
    if identity and datetime.now(timezone.utc) >= datetime.fromisoformat(identity["expires_at"]):
        RESULT_IDENTITIES.pop(result["id"], None)
        identity = None
    if user.get("is_guest") and (not identity or identity.get("user_id") != user.get("id")):
        # The free score is the immediate outcome of the test. Identity is
        # still requested for ownership, saving, and payment, but it must not
        # block a guest from seeing the score they just earned.
        allowed_guest = {"id", "session_id", "assessment_version", "score_version", "score_kind", "norm_version", "iq_score", "iq_score_kind", "iq_score_label", "iq_score_version", "iq_score_scale", "iq_score_method", "completed_at", "disclaimer", "official_iq_enabled", "confidence", "answered_count", "question_count", "duration_seconds"}
        return {**{key: value for key, value in result.items() if key in allowed_guest}, "full_access": False, "identity_required": True, "paid_features_unlocked": False, "domain_scores": {}, "domain_metrics": {}}
    unlocked = has_full_report_access(user["id"], result["id"]) or "platform_admin" in user.get("roles", [])
    if unlocked:
        return {**result, "full_access": True, "paid_features_unlocked": True}
    allowed = {"id", "session_id", "assessment_version", "score_version", "score_kind", "norm_version", "iq_score", "iq_score_kind", "iq_score_label", "iq_score_version", "iq_score_scale", "iq_score_method", "completed_at", "disclaimer", "official_iq_enabled"}
    return {**{key: value for key, value in result.items() if key in allowed}, "full_access": False, "paid_features_unlocked": False, "domain_scores": {}, "domain_metrics": {}}


def _result_record(result_id: str, request: Optional[Request] = None) -> Dict[str, Any]:
    if result_id in RESULTS:
        result = RESULTS[result_id]
        if request:
            session = session_for(result["session_id"])
            user = current_user(request)
            identity = guest_identity_for(result_id)
            if user.get("is_guest") and identity and datetime.now(timezone.utc) >= datetime.fromisoformat(identity["expires_at"]):
                raise HTTPException(410, "This guest result has expired. Start a new assessment.")
            if result.get("user_id") != user["id"] and "platform_admin" not in user.get("roles", []):
                raise HTTPException(404, "Result not found")
        return result
    if ASSESSMENT_PERSISTENCE:
        result = PERSISTENCE.get_result(result_id)
        if result:
            if request:
                user = current_user(request)
                if "platform_admin" not in user.get("roles", []) and result.get("user_id") != user["id"]:
                    raise HTTPException(404, "Result not found")
            return result
    raise HTTPException(404, "Result not found")


@app.post("/sessions/{session_id}/submit")
@serialized_flow
def submit_session(session_id: str, request: Request = None) -> Dict[str, Any]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    require_session_owner(session, request)
    if session.get("ephemeral"):
        # Practice confirms that the interaction works but deliberately does
        # not create a score, result record, entitlement, or saved response.
        SESSIONS.pop(session_id, None)
        return {"practice": True, "status": "complete", "answered_count": len(session.get("responses", {})), "question_count": len(session.get("item_order", [])), "message": "Practice complete. No score or answers were saved."}
    if session.get("result_id"):
        if ASSESSMENT_PERSISTENCE:
            existing = PERSISTENCE.get_result(session["result_id"])
            if existing:
                return result_projection(existing, request)
        if session["result_id"] in RESULTS:
            return result_projection(RESULTS[session["result_id"]], request)
    item_domains = {key: ITEMS[key]["domain"] for key in session["item_order"]}
    item_keys = {key: json.dumps(sorted(json.loads(ITEMS[key]["answer"])), separators=(",", ":")) if ITEMS[key].get("memory_response_type") == "cell_set" else ITEMS[key]["answer"] for key in session["item_order"]}
    score = score_domains(session["responses"].values(), item_domains, item_keys)
    interruption_count = PERSISTENCE.count_events(session_id, "interruption") if ASSESSMENT_PERSISTENCE else sum(1 for event in EVENTS if event["session_id"] == session_id and event["event_type"] == "interruption")
    quality = classify_session_quality([int(value["response_time_ms"]) for value in session["responses"].values()], interruption_count)
    result_id = str(uuid4())
    domain_metrics = {}
    for domain, metric in score.domain_metrics.items():
        value = score.domain_scores[domain]
        relative = "insufficient evidence" if value is None or score.composite is None else "stronger than your average" if value > score.composite + 3 else "lower than your average" if value < score.composite - 3 else "close to your average"
        domain_metrics[domain] = {**metric, "score": value, "relative": relative}
    RESULTS[result_id] = {"id": result_id, "session_id": session_id, "user_id": session.get("user_id"), "assessment_version": session["assessment_version"], "score_version": score.score_version, "score_kind": score.score_kind, "norm_version": score.norm_version, "composite": score.composite, "iq_score": score.iq_score, "iq_score_kind": score.iq_score_kind, "iq_score_label": EXPERIMENTAL_IQ_SCORE_LABEL, "iq_score_version": EXPERIMENTAL_IQ_SCORE_VERSION, "iq_score_scale": score.iq_score_scale, "iq_score_method": score.iq_score_method, "official_iq_enabled": False, "domain_scores": score.domain_scores, "domain_metrics": domain_metrics, "confidence": score.confidence, "quality": quality, "answered_count": len(session["responses"]), "question_count": len(session["item_order"]), "duration_seconds": session["duration_seconds"], "completed_at": NOW(), "created_at": NOW(), "disclaimer": SCORE_DISCLAIMER, "access_tier": "summary"}
    if ASSESSMENT_PERSISTENCE:
        PERSISTENCE.store_result_and_complete_session(session_id, RESULTS[result_id])
    else:
        session["status"] = "complete"
        session["result_id"] = result_id
    return result_projection(RESULTS[result_id], request)


def get_result(result_id: str, request: Optional[Request] = None) -> Dict[str, Any]:
    return result_projection(_result_record(result_id, request), request)


@app.get("/results")
def list_results(request: Request) -> Dict[str, Any]:
    """List only the signed-in user's results; guests use an opaque result URL."""
    user = current_user(request)
    if user.get("is_guest"):
        return {"results": []}
    results = [item for item in RESULTS.values() if item.get("user_id") == user["id"]]
    if PERSISTENCE:
        try:
            persisted = PERSISTENCE.list_results_for_user(user["id"])
        except Exception:
            persisted = []
        known = {item["id"] for item in results}
        results.extend(item for item in persisted if item["id"] not in known)
    results.sort(key=lambda item: item.get("completed_at", ""), reverse=True)
    return {"results": [result_projection(item, request) for item in results]}


@app.get("/results/{result_id}")
def get_result_endpoint(result_id: str, request: Request) -> Dict[str, Any]:
    return get_result(result_id, request)


@app.get("/questionnaires")
def questionnaires() -> List[Dict[str, Any]]:
    return [{"id": "compass-v1", "name": "IAQ Compass", "version": "RIASEC-PROVISIONAL-1", "sections": ["interests", "subjects", "work_values", "environment", "evidence", "constraints"]}]


@app.get("/questionnaires/{questionnaire_id}")
def questionnaire(questionnaire_id: str) -> Dict[str, Any]:
    if questionnaire_id != "compass-v1":
        raise HTTPException(404, "Questionnaire not found")
    return {"id": "compass-v1", "name": "Your interests", "version": "RIASEC-EXPLORATORY-0.1", "instructions": "Rate each statement from 0 (not like me) to 100 (very much like me). This is context, not a test.", "items": INTEREST_ITEMS}


@app.post("/questionnaires/{questionnaire_id}/responses")
def questionnaire_responses(questionnaire_id: str, payload: InterestResponseCreate, request: Request) -> Dict[str, Any]:
    if questionnaire_id != "compass-v1":
        raise HTTPException(404, "Questionnaire not found")
    user = current_user(request)
    if not has_full_report_access(user["id"], payload.result_id):
        raise HTTPException(402, "Unlock the full report before completing the interest check-in")
    _result_record(payload.result_id, request)
    if set(payload.responses) != {item["id"] for item in INTEREST_ITEMS}:
        raise HTTPException(422, "Complete all six interest dimensions")
    if any(value < 0 or value > 100 for value in payload.responses.values()):
        raise HTTPException(422, "Interest ratings must be between 0 and 100")
    attempt = access.store_interest_attempt(user["id"], payload.responses, payload.result_id)
    if PERSISTENCE:
        try:
            PERSISTENCE.store_interest_attempt(attempt)
        except Exception as error:
            raise HTTPException(503, "Interest response could not be saved") from error
    return attempt


@app.get("/me/interests")
def my_interests(request: Request, result_id: Optional[str] = None) -> Dict[str, Any]:
    user = current_user(request)
    if not has_full_report_access(user["id"], result_id):
        raise HTTPException(402, "Open an unlocked report before completing the interest check-in")
    _result_record(result_id, request)
    return interest_attempt_for(user["id"], result_id) or {"status": "not_started", "scores": {}, "code": None}


@app.post("/consents")
def create_consent(payload: ConsentCreate, request: Request) -> Dict[str, Any]:
    user = current_user(request)
    record = {"id": str(uuid4()), "user_id": user["id"], "version": payload.consent_version, "purpose": payload.purpose, "granted": payload.granted, "recorded_at": NOW()}
    access.record_audit(user["id"], "consent.recorded", "user_consent", record["id"], {"purpose": payload.purpose, "granted": payload.granted})
    return record


@app.post("/me/identity")
def capture_identity(payload: IdentityCaptureCreate, request: Request) -> Dict[str, Any]:
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", payload.email):
        raise HTTPException(422, "Enter a valid email address")
    if not payload.granted:
        raise HTTPException(400, "Pilot data consent is required before releasing the result")
    if payload.age_band != "18-22":
        raise HTTPException(403, "Only the 18–22 scored pilot flow can release a saved result")
    user = current_user(request)
    was_guest = bool(user.get("is_guest"))
    if payload.result_id:
        _result_record(payload.result_id, request)
    if was_guest:
        access.promote_guest_to_student(user, payload.email, payload.display_name, payload.age_band)
    else:
        user["email"] = payload.email.strip().lower()
        user["display_name"] = payload.display_name.strip()
        user["age_band"] = payload.age_band
    if PERSISTENCE:
        PERSISTENCE.store_identity(user["id"], user["email"], user["display_name"], user["age_band"], payload.consent_version, payload.granted)
    if payload.result_id:
        result = _result_record(payload.result_id, request=None)
        if result.get("user_id") != user["id"]:
            raise HTTPException(404, "Result not found")
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        identity = {"user_id": user["id"], "email": user["email"], "display_name": user["display_name"], "age_band": user["age_band"], "consent_version": payload.consent_version, "captured_at": NOW(), "expires_at": expires_at}
        RESULT_IDENTITIES[payload.result_id] = identity
        if PERSISTENCE and was_guest:
            token = _header_token(request)
            if token:
                PERSISTENCE.store_guest_identity(payload.result_id, user["id"], token, user["email"], user["display_name"], user["age_band"], payload.consent_version, expires_at)
    access.record_audit(user["id"], "pilot.identity_captured", "profile", user["id"], {"age_band": payload.age_band, "consent_version": payload.consent_version})
    guardian = None
    if payload.age_band == "15-17":
        if not payload.guardian_email or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", payload.guardian_email):
            raise HTTPException(422, "A guardian email is required for ages 15–17")
        guardian = create_guardian_consent(GuardianConsentCreate(guardian_email=payload.guardian_email, consent_version=payload.consent_version), request)
    # Supplying an email is not authentication. Keep the opaque guest token
    # until verified sign-in explicitly claims this result.
    promoted_token = None
    return {"user": access.public_user(user), "consent_version": payload.consent_version, "guardian_consent": guardian, "session_token": promoted_token, "provider": "development" if promoted_token else None, "result_id": payload.result_id}


class GuestResultClaim(BaseModel):
    result_id: str
    guest_token: str = Field(min_length=20, max_length=300)


@app.post("/results/claim")
@serialized_flow
def claim_guest_result(payload: GuestResultClaim, request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if user.get("is_guest"):
        raise HTTPException(401, "Verify your email before saving a guest result")
    guest = access.user_for_token(payload.guest_token)
    if not guest and PERSISTENCE:
        guest = PERSISTENCE.get_guest_user(payload.guest_token)
    result = RESULTS.get(payload.result_id)
    if not result and PERSISTENCE:
        result = PERSISTENCE.get_result(payload.result_id)
    identity = guest_identity_for(payload.result_id)
    if not guest or not identity or not result or identity["user_id"] != guest["id"]:
        raise HTTPException(404, "Guest result not found")
    if datetime.now(timezone.utc) >= datetime.fromisoformat(identity["expires_at"]):
        raise HTTPException(410, "Guest result has expired")
    if identity["email"].lower() != user.get("email", "").lower():
        raise HTTPException(403, "Sign in using the email entered for this result")
    if result["user_id"] == user["id"]:
        return {"claimed": True, "result_id": result["id"]}
    if result["user_id"] != guest["id"]:
        raise HTTPException(404, "Guest result not found")
    if ASSESSMENT_PERSISTENCE:
        if not PERSISTENCE.claim_guest_result(payload.result_id, guest["id"], user["id"], user.get("email", ""), user.get("display_name", "IAQ student"), user.get("age_band", "unknown")):
            raise HTTPException(409, "This guest result was already claimed or is no longer available")
        if result:
            result["user_id"] = user["id"]
        RESULT_IDENTITIES.pop(payload.result_id, None)
        access.record_audit(user["id"], "result.claimed", "result", payload.result_id, {})
        return {"claimed": True, "result_id": payload.result_id}
    result["user_id"] = user["id"]
    SESSIONS[result["session_id"]]["user_id"] = user["id"]
    for order in access.ORDERS.values():
        if order.get("result_id") == result["id"] and order["purchaser_user_id"] == guest["id"]:
            order["purchaser_user_id"] = user["id"]
            order["beneficiary_user_id"] = user["id"]
            for grant in access.ENTITLEMENTS.values():
                if grant.get("source_id") == order["id"]:
                    grant["owner_id"] = user["id"]
    interest = access.INTEREST_ATTEMPTS.pop(f"{guest['id']}:{result['id']}", None)
    if interest:
        interest["user_id"] = user["id"]
        access.INTEREST_ATTEMPTS[f"{user['id']}:{result['id']}"] = interest
    access.record_audit(user["id"], "result.claimed", "result", result["id"], {})
    return {"claimed": True, "result_id": result["id"]}


@app.post("/guardian-consents")
def create_guardian_consent(payload: GuardianConsentCreate, request: Request) -> Dict[str, Any]:
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", payload.guardian_email):
        raise HTTPException(422, "Enter a valid guardian email address")
    user = current_user(request)
    consent_id = str(uuid4())
    token = secrets.token_urlsafe(24)
    record = {"id": consent_id, "student_user_id": user["id"], "guardian_email": payload.guardian_email.strip().lower(), "consent_version": payload.consent_version, "status": "pending", "token": token, "requested_at": NOW(), "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()}
    access.GUARDIAN_CONSENTS[consent_id] = record
    access.record_audit(user["id"], "guardian_consent.requested", "guardian_consent", consent_id, {"consent_version": payload.consent_version})
    response = {key: value for key, value in record.items() if key != "token"}
    if os.getenv("IAQ_AUTH_MODE", "development") == "development":
        response["development_token"] = token
    return response


@app.post("/guardian-consents/{consent_id}/grant")
def grant_guardian_consent(consent_id: str, payload: GuardianConsentGrant, request: Request) -> Dict[str, Any]:
    record = access.GUARDIAN_CONSENTS.get(consent_id)
    if not record or record.get("token") != payload.token:
        raise HTTPException(404, "Guardian consent request not found")
    if datetime.now(timezone.utc) >= datetime.fromisoformat(record["expires_at"]):
        record["status"] = "expired"
        raise HTTPException(410, "This guardian consent request has expired")
    record["status"] = "granted"
    record["granted_at"] = NOW()
    access.record_audit(current_user(request)["id"], "guardian_consent.granted", "guardian_consent", consent_id, {})
    return {key: value for key, value in record.items() if key != "token"}


@app.get("/majors")
def majors() -> List[Dict[str, Any]]:
    return [{key: value for key, value in major.items() if key != "vector"} for major in MAJORS]


@app.get("/recommendations")
def recommendations(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    user_results = [result for result in RESULTS.values() if session_for(result["session_id"]) and session_for(result["session_id"]).get("user_id") == user["id"]]
    latest = max(user_results, key=lambda result: result.get("completed_at", ""), default=None)
    cognitive = ({domain: value if isinstance(value, int) else 50 for domain, value in latest["domain_scores"].items()} if latest else {domain: 50 for domain in DOMAINS})
    interest = interest_attempt_for(user["id"], latest["id"] if latest else None)
    interests = (interest or {}).get("scores", {"I": 50, "A": 50, "C": 50, "R": 50, "S": 50, "E": 50})
    return {"version": "MATCH-V2", "recommendations": [{**{key: value for key, value in major.items() if key != "vector"}, **major_fit(cognitive, interests, latest["answered_count"] if latest else 0, major["vector"]), "confidence": recommendation_confidence(latest["answered_count"] if latest else 0, .34, 5, 24)} for major in MAJORS], "explanations": {"method": "weighted transparent fit using the latest persisted cognitive result and optional stated interests; not destiny", "warnings": ["experimental_profile", "no_population_norms", "try_real_experiences_before_deciding"]}}


@app.get("/ai/status")
def ai_status() -> Dict[str, Any]:
    """Expose safe capability status without ever exposing the API key."""
    return ai.public_status()


def _latest_result_for_user(user_id: str) -> Optional[Dict[str, Any]]:
    owned = []
    for result in RESULTS.values():
        session = session_for(result["session_id"])
        if session and session.get("user_id") == user_id:
            owned.append(result)
    return max(owned, key=lambda result: result.get("completed_at", ""), default=None)


def _ai_input_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _cached_ai_output(result_id: str, kind: str, input_hash: str, user_id: str) -> Optional[Dict[str, Any]]:
    cache_key = f"{user_id}:{result_id}:{kind}:{input_hash}"
    if cache_key in AI_INSIGHTS:
        return AI_INSIGHTS[cache_key]
    if PERSISTENCE:
        cached = PERSISTENCE.get_ai_output(result_id, kind, input_hash)
        if cached:
            AI_INSIGHTS[cache_key] = cached
            return cached
    return None


def _store_ai_output(response: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    AI_INSIGHTS[f"{user_id}:{response['result_id']}:{response['kind']}:{response['input_hash']}"] = response
    if PERSISTENCE:
        PERSISTENCE.store_ai_output({**response, "user_id": user_id})
    return response


@app.post("/ai/results/{result_id}/interpretation")
def ai_result_interpretation(result_id: str, request: Request) -> Dict[str, Any]:
    """Create a bounded plain-language explanation for an existing result.

    The score is already calculated by IAQ's deterministic scorer. OpenAI only
    receives aggregate result evidence and cannot write back score fields.
    """
    user_id = current_user(request)["id"]
    if not has_full_report_access(user_id, result_id):
        raise HTTPException(402, "Unlock the full report before requesting an AI evaluation")
    result = _result_record(result_id, request)
    labels = {domain: domain.replace("_", " ").title() for domain in DOMAINS}
    input_hash = _ai_input_hash({"result": {key: result.get(key) for key in ("composite", "domain_scores", "domain_metrics", "confidence", "quality", "answered_count", "question_count")}, "labels": labels})
    cached = _cached_ai_output(result_id, "result_interpretation", input_hash, user_id)
    if cached:
        return cached
    try:
        narrative, metadata = ai.interpret_result(result, labels)
    except (ai.AIUnavailable, ai.AIOutputError):
        ranked = sorted(((name, value) for name, value in result["domain_scores"].items() if value is not None), key=lambda pair: pair[1], reverse=True)
        narrative = {"what_stands_out": [f"{labels[name]} was among your strongest observed areas on this form." for name, value in ranked[:2]], "where_more_evidence": ["Different questions and another occasion may produce a different profile. These items have not been calibrated against population norms."], "timing_context": "Response times describe this session only and do not change your score.", "next_step": "Complete the interest check-in, then try a small project in a suggested area."}
        metadata = {"provider": "deterministic_fallback", "model": "PROFILE-1", "prompt_version": "PROFILE-1", "fallback_used": True}
    response = {"id": str(uuid4()), "result_id": result_id, "kind": "result_interpretation", "status": "generated", "data_origin": "DETERMINISTIC_FALLBACK" if metadata.get("fallback_used") else "AI_ASSISTED", "created_at": NOW(), "input_hash": input_hash, **metadata, "narrative": narrative}
    return _store_ai_output(response, user_id)


@app.post("/ai/directions")
def ai_directions(payload: AIDirectionsCreate, request: Request) -> Dict[str, Any]:
    """Generate a paid, cached direction evaluation from aggregate evidence."""
    user = current_user(request)
    if not has_full_report_access(user["id"], payload.result_id):
        raise HTTPException(402, "Unlock the full report before exploring directions")
    result = _result_record(payload.result_id, request) if payload.result_id else _latest_result_for_user(user["id"])
    if not result:
        raise HTTPException(404, "Complete an assessment before requesting direction context")
    interest = interest_attempt_for(user["id"], result["id"]) or {"status": "not_started", "scores": {}, "code": None}
    if interest.get("status") in {"not_started", None}:
        raise HTTPException(409, "Complete the interest check-in before exploring directions")
    candidates = [{key: value for key, value in major.items() if key != "vector"} | major_fit({domain: value if isinstance(value, int) else 50 for domain, value in result.get("domain_scores", {}).items()}, interest.get("scores", {}), result.get("answered_count", 0), major["vector"]) for major in MAJORS]
    input_hash = _ai_input_hash({"result": {key: result.get(key) for key in ("composite", "domain_scores", "confidence", "answered_count")}, "interest": {"code": interest.get("code"), "scores": interest.get("scores", {})}, "candidates": candidates})
    cached = _cached_ai_output(result["id"], "direction_context", input_hash, user["id"])
    if cached:
        return cached
    try:
        narrative, metadata = ai.suggest_directions(result, interest, candidates)
        status = "generated"
        data_origin = "AI_ASSISTED"
        fallback_used = False
    except (ai.AIUnavailable, ai.AIOutputError) as error:
        ranked = sorted(candidates, key=lambda item: (item.get("fit", 0), item.get("confidence", 0)), reverse=True)[:3]
        narrative = {"directions": [{"slug": item["slug"], "name": item["name"], "why_this_may_fit": "Your current profile and interests show some evidence worth exploring here.", "try_next": "Try a small project, course preview, or conversation in this area.", "caution": "This is a provisional direction to investigate, not a prediction."} for item in ranked]}
        metadata = {"provider": "deterministic_fallback", "model": "MATCH-V2", "prompt_version": "MATCH-V2-FALLBACK", "error": str(error)[:500]}
        status = "fallback"
        data_origin = "DETERMINISTIC_FALLBACK"
        fallback_used = True
    response = {"id": str(uuid4()), "result_id": result["id"], "interest_attempt_id": interest.get("id"), "kind": "direction_context", "status": status, "data_origin": data_origin, "fallback_used": fallback_used, "created_at": NOW(), "input_hash": input_hash, **metadata, **narrative}
    return _store_ai_output(response, user["id"])


@app.post("/results/{result_id}/delivery")
def request_report_delivery(result_id: str, payload: ReportDeliveryCreate, request: Request) -> Dict[str, Any]:
    """Send or queue a private full report through the configured adapter."""
    user = current_user(request)
    if os.getenv("IAQ_ENV", "development").lower() == "production" and not email_delivery.configured():
        raise HTTPException(503, "Production report delivery is not configured")
    if not has_full_report_access(user["id"], result_id):
        raise HTTPException(402, "Unlock the full report before requesting report delivery")
    result = _result_record(result_id, request)
    if not payload.granted:
        raise HTTPException(400, "Report delivery consent is required")
    if payload.age is not None and payload.age < 18:
        if not payload.guardian_consent_id or payload.guardian_consent_id not in access.GUARDIAN_CONSENTS or access.GUARDIAN_CONSENTS[payload.guardian_consent_id].get("status") != "granted":
            raise HTTPException(403, "Report delivery for minors requires guardian consent workflow")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", payload.email):
        raise HTTPException(422, "Enter a valid email address")
    key = f"{result_id}:{payload.email.strip().lower()}"
    existing = REPORT_DELIVERIES.get(key)
    if not existing and PERSISTENCE:
        existing = PERSISTENCE.get_report_delivery(result_id, payload.email.strip().lower())
    if existing and existing.get("status") not in {"FAILED_RETRYABLE", "FAILED"}:
        REPORT_DELIVERIES[key] = existing
        return existing
    delivery = {"id": existing.get("id") if existing else str(uuid4()), "result_id": result_id, "name": payload.name.strip(), "email": payload.email.strip().lower(), "consent_version": payload.consent_version, "status": "QUEUED", "provider": "development_log", "requested_at": existing.get("requested_at") if existing else NOW(), "sent_at": None}
    delivery.update(email_delivery.send_report(delivery, f"{os.getenv('APP_BASE_URL', 'http://127.0.0.1:5173')}/results?result={result_id}"))
    if delivery.get("status") == "SENT":
        delivery["sent_at"] = NOW()
    REPORT_DELIVERIES[key] = delivery
    if PERSISTENCE:
        PERSISTENCE.store_report_delivery(delivery)
    return delivery


@app.post("/certificates")
def create_certificate(payload: CertificateCreate, request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if not has_full_report_access(user["id"], payload.result_id):
        raise HTTPException(402, "Unlock the full report before requesting a completion certificate")
    result = _result_record(payload.result_id, request)
    if result.get("answered_count", 0) < 1:
        raise HTTPException(409, "A certificate needs a submitted assessment")
    if PERSISTENCE:
        try:
            existing = PERSISTENCE.get_certificate_for_result(user["id"], payload.result_id)
        except Exception:
            existing = None
        if existing:
            access.CERTIFICATES[existing["id"]] = existing
            return existing
    certificate = access.issue_certificate(user["id"], result)
    if PERSISTENCE:
        try:
            PERSISTENCE.store_certificate(certificate)
        except Exception as error:
            raise HTTPException(503, "Certificate could not be saved") from error
    return certificate


@app.get("/certificates")
def list_certificates(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    certificates = [item for item in access.CERTIFICATES.values() if item["user_id"] == user["id"]]
    if PERSISTENCE:
        try:
            persisted = PERSISTENCE.list_certificates(user["id"])
        except Exception:
            persisted = []
        known = {item["id"] for item in certificates}
        certificates.extend(item for item in persisted if item["id"] not in known)
    return {"certificates": certificates}


@app.get("/certificates/{certificate_id}")
def get_certificate(certificate_id: str, request: Request) -> Dict[str, Any]:
    user = current_user(request)
    certificate = access.CERTIFICATES.get(certificate_id)
    if not certificate and PERSISTENCE:
        try:
            certificate = PERSISTENCE.get_certificate(certificate_id)
        except Exception:
            certificate = None
    owned = certificate and (certificate["user_id"] == user["id"] or (PERSISTENCE and certificate["user_id"] == PERSISTENCE._db_user_id(user["id"])))
    if not certificate or (not owned and "platform_admin" not in user["roles"]):
        raise HTTPException(404, "Certificate not found")
    return certificate


@app.get("/certificates/verify/{identifier}")
def verify_certificate(identifier: str) -> Dict[str, Any]:
    certificate = access.certificate_for_identifier(identifier)
    if not certificate and PERSISTENCE:
        try:
            certificate = PERSISTENCE.certificate_for_identifier(identifier)
        except Exception:
            certificate = None
    if not certificate:
        return {"valid": False, "status": "not_found", "certificate_identifier": identifier}
    return {"valid": certificate["status"] == "issued", "status": certificate["status"], "certificate_identifier": certificate["certificate_identifier"], "title": certificate["title"], "assessment_version": certificate["assessment_version"], "issued_at": certificate["issued_at"]}


@app.post("/majors/{major_id}/save")
def save_major(major_id: str, request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if not any(major["id"] == major_id for major in MAJORS):
        raise HTTPException(404, "Direction not found")
    SAVED_MAJORS.setdefault(user["id"], [])
    if major_id not in SAVED_MAJORS[user["id"]]:
        SAVED_MAJORS[user["id"]].append(major_id)
    return {"saved": True, "major_id": major_id}


@app.delete("/majors/{major_id}/save")
def unsave_major(major_id: str, request: Request) -> Dict[str, Any]:
    user = current_user(request)
    SAVED_MAJORS.setdefault(user["id"], [])
    SAVED_MAJORS[user["id"]] = [item for item in SAVED_MAJORS[user["id"]] if item != major_id]
    return {"saved": False, "major_id": major_id}


@app.get("/tracker")
def tracker(request: Request) -> Dict[str, Any]:
    user_id = current_user(request)["id"]
    user_results = [result for result in RESULTS.values() if session_for(result["session_id"]) and session_for(result["session_id"]).get("user_id") == user_id]
    history = [{"date": result.get("completed_at"), "version": result.get("assessment_version"), "confidence": result.get("confidence")} for result in sorted(user_results, key=lambda result: result.get("completed_at", ""))]
    interest = access.INTEREST_ATTEMPTS.get(user_id)
    return {"student_id": user_id, "assessment_history": history, "interest_evolution": [{"date": interest.get("created_at"), "code": interest.get("code")} ] if interest else [], "readiness": {"evidence_count": 0, "projects": 0}, "saved_majors": SAVED_MAJORS.get(user_id, [])}


@app.get("/counselor/students")
def counselor_students(request: Request) -> Dict[str, Any]:
    require_permission(current_user(request), "school.students.read")
    return {"students": [{"id": "student-01", "name": "Lena Suryani", "consent": "granted", "assessment": "complete", "confidence": "high"}, {"id": "student-02", "name": "Fajar Kusuma", "consent": "granted", "assessment": "in_progress", "confidence": "pending"}]}


@app.get("/admin/items")
def admin_items(request: Request, status: Optional[str] = Query(default=None), domain: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    require_permission(current_user(request), "content.items.read")
    items = list(ITEMS.values())
    if status:
        items = [item for item in items if item["status"] == status]
    if domain:
        items = [item for item in items if item["domain"] == domain]
    return {"items": [admin_item_payload(item) for item in items], "total": len(items), "filters": {"status": status, "domain": domain}}


@app.get("/admin/items/{item_id}")
def admin_item(item_id: str, request: Request) -> Dict[str, Any]:
    require_permission(current_user(request), "content.items.read")
    item = ITEMS.get(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return admin_item_payload(item)


@app.post("/admin/items/{item_id}/review")
def review_item(item_id: str, payload: ItemReviewCreate, request: Request) -> Dict[str, Any]:
    require_permission(current_user(request), "content.items.review")
    item = ITEMS.get(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    reviewer = current_user(request)
    try:
        review_record = review.record_review(item, reviewer["id"], reviewer["roles"][0], payload.decision, payload.notes, payload.checks)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    if payload.status in {"PILOT", "ACTIVE"} and not review.review_summary(item)["review_ready"]:
        raise HTTPException(409, "Two independent approvals are required before pilot or active use")
    if payload.status in {"PILOT", "ACTIVE"}:
        item["status"] = payload.status
        item["lifecycle_status"] = payload.status
    return {"accepted": True, "review": review_record, "item": admin_item_payload(item)}


def update_item_status(item_id: str, status: str, request: Request = None) -> Dict[str, Any]:
    if request:
        require_permission(current_user(request), "content.items.review")
    item = ITEMS.get(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    if status in {"PILOT", "ACTIVE"} and not review.review_summary(item)["review_ready"]:
        raise HTTPException(409, "Two independent human approvals are required before student use")
    item["status"] = status
    item["lifecycle_status"] = status
    return {"accepted": True, "item": admin_item_payload(item)}


@app.post("/admin/items/{item_id}/activate")
def activate_item(item_id: str, request: Request) -> Dict[str, Any]:
    return update_item_status(item_id, "ACTIVE", request)


@app.post("/admin/items/{item_id}/suspend")
def suspend_item(item_id: str, request: Request) -> Dict[str, Any]:
    return update_item_status(item_id, "SUSPENDED", request)


@app.post("/admin/items/{item_id}/retire")
def retire_item(item_id: str, request: Request) -> Dict[str, Any]:
    return update_item_status(item_id, "RETIRED", request)


@app.get("/admin/review-queue")
def review_queue(request: Request, domain: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    require_permission(current_user(request), "content.items.read")
    items = [item for item in ITEMS.values() if item.get("lifecycle_status", item.get("status")) in {"DRAFT", "AUTO_VERIFIED", "HUMAN_REVIEWED"}]
    if domain:
        items = [item for item in items if item.get("domain") == domain]
    return {"items": [admin_item_payload(item) for item in items], "total": len(items), "filters": {"domain": domain}}


@app.get("/admin/items/{item_id}/reviews")
def item_reviews(item_id: str, request: Request) -> Dict[str, Any]:
    require_permission(current_user(request), "content.items.read")
    item = ITEMS.get(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return review.review_summary(item)


@app.get("/admin/item-health")
def item_health(request: Request, domain: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    require_permission(current_user(request), "content.health.read")
    items = list(ITEMS.values())
    if domain:
        items = [item for item in items if item.get("domain") == domain]
    rows = [response for session in SESSIONS.values() for response in session.get("responses", {}).values()]
    return evaluation.bank_health(items, rows)


@app.get("/admin/dataset/summary")
def external_dataset_summary(request: Request) -> Dict[str, Any]:
    """Return safe inventory metadata for the staged research datasets."""
    require_permission(current_user(request), "content.items.read")
    return external_data.dataset_summary()


@app.get("/admin/dataset/preview")
def external_dataset_preview(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    domain: Optional[str] = Query(default=None),
    dataset: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Protected reviewer preview; answer keys are deliberately admin-only."""
    require_permission(current_user(request), "content.items.read")
    items = external_data.preview_items(limit=limit, domain=domain, dataset=dataset)
    return {
        "items": items,
        "total": len(items),
        "filters": {"limit": limit, "domain": domain, "dataset": dataset, "language": "en"},
        "warning": "Research candidates only. Every item is unreviewed and excluded from student scoring.",
    }


@app.get("/admin/dataset/items/{item_id}")
def external_dataset_item(item_id: str, request: Request) -> Dict[str, Any]:
    """Return one quarantined candidate for reviewer preview."""
    require_permission(current_user(request), "content.items.read")
    item = external_data.find_external_item(item_id)
    if not item:
        raise HTTPException(404, "Dataset candidate not found")
    return item


@app.post("/admin/dataset/items/{item_id}/review")
def review_external_dataset_item(item_id: str, payload: ItemReviewCreate, request: Request) -> Dict[str, Any]:
    """Record a review decision; staged candidates never activate from this endpoint."""
    require_permission(current_user(request), "content.items.review")
    reviewer = current_user(request)
    try:
        return external_data.review_external_item(item_id, reviewer["id"], reviewer["roles"][0], payload.decision, payload.notes, payload.checks)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error


@app.get("/admin/dataset/review-summary")
def external_dataset_review_summary(request: Request) -> Dict[str, Any]:
    require_permission(current_user(request), "content.health.read")
    return external_data.review_summary()


@app.get("/admin/dataset/audit")
def external_dataset_audit(request: Request) -> Dict[str, Any]:
    require_permission(current_user(request), "content.health.read")
    return dataset_audit.audit_catalog()


@app.get("/admin/dataset/assets/{dataset}/{asset_path:path}")
def external_dataset_asset(dataset: str, asset_path: str, request: Request) -> FileResponse:
    """Serve staged preview images only to authorised reviewers."""
    require_permission(current_user(request), "content.items.read")
    asset = external_data.resolve_asset_path(dataset, asset_path)
    if not asset:
        raise HTTPException(404, "Dataset asset not found")
    return FileResponse(asset)


@app.get("/assessment-stimuli/{item_id}.svg")
def staged_matrix_stimulus(item_id: str) -> Response:
    if ASSESSMENT_SOURCE != "staged":
        raise HTTPException(404, "Assessment stimulus not found")
    visual = ITEMS.get(item_id, {}).get("matrix_visual")
    if not visual:
        raise HTTPException(404, "Assessment stimulus not found")
    try:
        svg = render_matrix_svg(visual.get("stimulus"), visual.get("options"))
    except ValueError:
        raise HTTPException(422, "Assessment stimulus is incomplete")
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"})


@app.get("/assessment-assets/{asset_path:path}")
def staged_assessment_asset(asset_path: str) -> FileResponse:
    """Serve only the image stimulus for the explicitly enabled staged source."""
    if ASSESSMENT_SOURCE != "staged":
        raise HTTPException(404, "Assessment asset not found")
    asset = external_data.resolve_asset_path("five_domains", asset_path)
    if not asset:
        raise HTTPException(404, "Assessment asset not found")
    return FileResponse(asset)


def question_bank_summary(request: Request = None) -> Dict[str, Any]:
    """Expose safe operational metadata for the question-studio dashboard."""
    if request:
        require_permission(current_user(request), "content.health.read")
    lifecycle_counts: Dict[str, int] = {}
    origin_counts: Dict[str, int] = {}
    family_counts: Dict[str, int] = {}
    form_family_counts: Dict[str, int] = {}
    for item in ITEMS.values():
        lifecycle_counts[item.get("lifecycle_status", item.get("status", "UNKNOWN"))] = lifecycle_counts.get(item.get("lifecycle_status", item.get("status", "UNKNOWN")), 0) + 1
        origin_counts[item.get("data_origin", "UNKNOWN")] = origin_counts.get(item.get("data_origin", "UNKNOWN"), 0) + 1
        source_family = item.get("source_family_id", item.get("item_family_id", item["id"]))
        form_family = item.get("item_family_id", item["id"])
        family_counts[source_family] = family_counts.get(source_family, 0) + 1
        form_family_counts[form_family] = form_family_counts.get(form_family, 0) + 1
    eligible = [item for item in ITEMS.values() if item.get("lifecycle_status", item.get("status")) in {"PILOT", "ACTIVE"}]
    reviewed = reviewed_counts()
    independently_approved = review.review_counts(ITEMS.values())
    return {
        "total": len(ITEMS),
        "minimum_per_domain": MINIMUM_ITEMS_PER_DOMAIN,
        "target_per_domain": TARGET_ITEMS_PER_DOMAIN,
        "reviewed_target_per_domain": REVIEWED_ITEMS_PER_DOMAIN,
        "counts": bank_counts(),
        "ready": bank_is_ready(),
        "review_gate_ready": review_gate_ready(),
        "review_gate_enforced": os.getenv("IAQ_REQUIRE_REVIEWED_ITEMS", "false").lower() == "true",
        "form_sizes": {"quick": 12, "complete": 40},
        "difficulty_label": "medium_hard",
        "lifecycle": "MIXED_CANDIDATES_AND_PILOT",
        "generated_count": sum(1 for item in ITEMS.values() if item.get("data_origin") == "ORIGINAL_GENERATED"),
        "reviewed_count": sum(1 for item in ITEMS.values() if item.get("data_origin") == "REVIEWED_CONTENT"),
        "reviewed_counts": reviewed,
        "two_reviewer_counts": independently_approved,
        "reviewed_shortfall": {domain: max(0, REVIEWED_ITEMS_PER_DOMAIN - reviewed.get(domain, 0)) for domain in DOMAINS},
        "eligible_counts": bank_counts(eligible),
        "lifecycle_counts": lifecycle_counts,
        "origin_counts": origin_counts,
        "unique_family_count": len(family_counts),
        "unique_form_family_count": len(form_family_counts),
        "review_gate": "Generated candidates remain AUTO_VERIFIED until two independent human approvals move them into HUMAN_REVIEWED, then PILOT or ACTIVE.",
    }


@app.get("/admin/question-bank/summary")
def question_bank_summary_endpoint(request: Request) -> Dict[str, Any]:
    return question_bank_summary(request)
