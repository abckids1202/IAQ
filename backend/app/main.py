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
import hmac
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .domain import DOMAINS, classify_session_quality, score_domains, score_riasec, major_fit, recommendation_confidence
from .question_bank import MINIMUM_ITEMS_PER_DOMAIN, TARGET_ITEMS_PER_DOMAIN, QUESTION_BANK, bank_counts, bank_is_ready
from .persistence import PostgresAssessmentStore
from . import access

app = FastAPI(title="IAQ API", version="0.1.0", description="Experimental educational profile API")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"], allow_origin_regex=r"https?://(127\.0\.0\.1|localhost):517[0-9]$", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

NOW = lambda: datetime.now(timezone.utc).isoformat()
DURATION_SECONDS = 35 * 60
SCORE_DISCLAIMER = "This is an experimental educational profile, not a clinical diagnosis or officially normed IQ score. It shows relative signals within this assessment only."

ITEMS: Dict[str, Dict[str, Any]] = {
    "abs-01": {"id": "abs-01", "domain": "abstract_reasoning", "type": "choice", "prompt": "Each tile changes by the same rule. Which tile completes the sequence?", "options": ["A", "B", "C", "D"], "answer": "B", "status": "ACTIVE"},
    "logic-01": {"id": "logic-01", "domain": "deductive_logic", "type": "choice", "prompt": "All red notebooks are archived. This notebook is red. What must be true?", "options": ["It is archived", "It is new", "It is blue", "Nothing can be concluded"], "answer": "It is archived", "status": "ACTIVE"},
    "num-01": {"id": "num-01", "domain": "numerical_reasoning", "type": "sequence", "prompt": "Complete the sequence: 3, 6, 12, 24, __", "options": ["30", "36", "42", "48"], "answer": "48", "status": "ACTIVE"},
    "verbal-01": {"id": "verbal-01", "domain": "verbal_reasoning", "type": "choice", "prompt": "A map is to navigation as a score is to…", "options": ["Music", "Evaluation", "Paper", "Competition"], "answer": "Evaluation", "status": "ACTIVE"},
    "spatial-01": {"id": "spatial-01", "domain": "visual_spatial_reasoning", "type": "choice", "prompt": "Imagine the L-shape rotates 90° clockwise. Which direction does its short arm point?", "options": ["Up", "Down", "Left", "Right"], "answer": "Down", "status": "ACTIVE"},
    "memory-01": {"id": "memory-01", "domain": "working_memory", "type": "memory", "prompt": "Remember this sequence, then select it in the same order.", "options": ["7-2-9-4", "7-9-2-4", "2-7-4-9", "9-4-7-2"], "answer": "7-2-9-4", "status": "ACTIVE"},
    "speed-01": {"id": "speed-01", "domain": "processing_speed", "type": "speed", "prompt": "Find the only pair of matching symbols.", "options": ["A", "B", "C", "D"], "answer": "B", "status": "ACTIVE"},
}
# The reviewed bank is the source of truth. The small legacy entries above are
# retained as a migration note for the first demo build.
ITEMS = {item["id"]: item for item in QUESTION_BANK}
SESSIONS: Dict[str, Dict[str, Any]] = {}
RESULTS: Dict[str, Dict[str, Any]] = {}
EVENTS: List[Dict[str, Any]] = []
SAVED_MAJORS: Dict[str, List[str]] = {}
REPORT_DELIVERIES: Dict[str, Dict[str, Any]] = {}
FEEDBACK: List[Dict[str, Any]] = []
DATABASE_URL = os.getenv("IAQ_DATABASE_URL")
PERSISTENCE = PostgresAssessmentStore(DATABASE_URL) if DATABASE_URL else None

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
    assessment_version: str = "IAQ-COG-0.3"
    mode: str = Field(default="complete", pattern="^(quick|complete)$")


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


class ItemReviewCreate(BaseModel):
    status: str = Field(pattern="^(DRAFT|AUTO_VERIFIED|HUMAN_REVIEWED|PILOT|ACTIVE|SUSPENDED|RETIRED)$")
    notes: str = ""


class ReportDeliveryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    consent_version: str = Field(default="REPORT-DELIVERY-1.0", min_length=1, max_length=40)
    granted: bool = False
    age: Optional[int] = Field(default=None, ge=13, le=120)


class InterestResponseCreate(BaseModel):
    responses: Dict[str, int]


class CertificateCreate(BaseModel):
    result_id: str = Field(min_length=8, max_length=80)


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
    beneficiary_user_id: Optional[str] = Field(default=None, min_length=2, max_length=120)
    school_id: Optional[str] = Field(default=None, min_length=2, max_length=120)


class ConsentRecordCreate(BaseModel):
    consent_version: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=1, max_length=120)
    granted: bool


def _header_token(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("x-iaq-session")


def current_user(request: Optional[Request] = None) -> Dict[str, Any]:
    """Resolve the authenticated identity for local or provider-backed calls.

    Until Supabase is configured, no-token local requests intentionally resolve
    to the seeded student account so the existing assessment preview remains
    runnable. Production deployments must set IAQ_AUTH_MODE=supabase and reject
    this fallback in their auth middleware.
    """
    user = access.user_for_token(_header_token(request))
    if user:
        return user
    requested_user = request.headers.get("x-iaq-user") if request else None
    if requested_user and os.getenv("IAQ_AUTH_MODE", "development") == "development":
        return access.user_for_identifier(requested_user)
    return access.USERS["demo-student"]


def require_permission(user: Dict[str, Any], permission: str) -> None:
    if permission not in access.permissions_for(user):
        raise HTTPException(403, "You do not have permission to perform this action")


def serialize_order(order: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in order.items() if key not in {"payment_secret", "server_key"}}


def public_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Return a strict student payload; internal provenance never leaves the API."""
    allowed = {"id", "domain", "type", "prompt", "options", "helper", "visual", "render_type"}
    return {key: value for key, value in item.items() if key in allowed and value is not None}


def session_for(session_id: str) -> Optional[Dict[str, Any]]:
    if PERSISTENCE:
        return PERSISTENCE.get_session(session_id)
    return SESSIONS.get(session_id)


def persist_session(session: Dict[str, Any], values: Dict[str, Any]) -> None:
    if PERSISTENCE:
        PERSISTENCE.update_session(session["id"], values)
    else:
        session.update(values)


def create_randomized_form(mode: str) -> List[str]:
    """Create a balanced, no-repeat form from the reviewed question bank."""
    eligible_items = [item for item in ITEMS.values() if item.get("status") in {"PILOT", "ACTIVE"}]
    if not bank_is_ready(eligible_items):
        raise HTTPException(500, "Question bank is not ready")
    per_domain = 8 if mode == "complete" else 2
    pools: Dict[str, List[str]] = {domain: [] for domain in DOMAINS}
    for item in eligible_items:
        pools[item["domain"]].append(item["id"])
    rng = random.SystemRandom()
    selected: List[str] = []
    for domain in DOMAINS:
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


@app.get("/auth/config")
def auth_config() -> Dict[str, Any]:
    """Expose safe feature flags; provider secrets never leave the server."""
    return {
        "mode": os.getenv("IAQ_AUTH_MODE", "development"),
        "google_enabled": os.getenv("AUTH_GOOGLE_ENABLED", "false").lower() == "true",
        "email_otp_enabled": os.getenv("AUTH_EMAIL_OTP_ENABLED", "true").lower() == "true",
        "payments_enabled": os.getenv("PAYMENTS_ENABLED", "true").lower() == "true",
        "payment_provider": "midtrans" if os.getenv("MIDTRANS_SERVER_KEY") else "mock",
        "production_ready": False,
    }


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
    return {"entitlements": [item for item in access.ENTITLEMENTS.values() if item["owner_id"] == user["id"]]}


@app.get("/me/orders")
def me_orders(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    return {"orders": [serialize_order(order) for order in access.orders_for(user["id"])]}


@app.get("/products")
def products() -> Dict[str, Any]:
    return {"products": access.list_products(), "currency": "IDR", "payment_provider": "midtrans_sandbox" if os.getenv("MIDTRANS_SERVER_KEY") else "mock"}


@app.get("/products/{product_id}")
def product(product_id: str) -> Dict[str, Any]:
    product_record = access.PRODUCTS.get(product_id)
    if not product_record or not product_record["active"]:
        raise HTTPException(404, "Product not found")
    return {key: value for key, value in product_record.items() if key not in {"entitlement_code", "report_code"}}


@app.post("/orders")
def create_order(payload: OrderCreate, request: Request) -> Dict[str, Any]:
    user = current_user(request)
    require_permission(user, "order.self.create")
    try:
        order = access.create_order(user["id"], payload.product_id, payload.beneficiary_user_id, payload.school_id)
    except PermissionError as error:
        raise HTTPException(403, str(error))
    except ValueError as error:
        raise HTTPException(422, str(error))
    return serialize_order(order)


def _authorized_order(order: Dict[str, Any], user: Dict[str, Any]) -> None:
    if user["id"] not in {order["purchaser_user_id"], order["beneficiary_user_id"]} and "platform_admin" not in user["roles"]:
        raise HTTPException(404, "Order not found")


@app.get("/orders/{order_id}")
def get_order(order_id: str, request: Request) -> Dict[str, Any]:
    order = access.ORDERS.get(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    _authorized_order(order, current_user(request))
    return serialize_order(order)


@app.post("/orders/{order_id}/checkout")
def checkout_order(order_id: str, request: Request) -> Dict[str, Any]:
    user = current_user(request)
    order = access.ORDERS.get(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    _authorized_order(order, user)
    if order["status"] == "fulfilled":
        return {"order": serialize_order(order), "payment_attempt": None, "message": "Access is already active."}
    if os.getenv("PAYMENTS_ENABLED", "true").lower() != "true":
        raise HTTPException(503, "Payments are not enabled")
    return {"order": serialize_order(order), "payment_attempt": access.create_payment_attempt(order_id), "message": "Complete payment in the hosted checkout. The browser redirect does not grant access."}


@app.get("/orders/{order_id}/status")
def order_status(order_id: str, request: Request) -> Dict[str, Any]:
    order = access.ORDERS.get(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    _authorized_order(order, current_user(request))
    attempt = next((item for item in access.PAYMENT_ATTEMPTS.values() if item["order_id"] == order_id), None)
    return {"order": serialize_order(order), "payment_attempt": attempt, "entitlements": [item for item in access.ENTITLEMENTS.values() if item["owner_id"] == order["beneficiary_user_id"] and item["source_id"] == order_id]}


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
    """Verify a sandbox notification before it can fulfill an order.

    The payload follows Midtrans' notification fields. If no server key is
    configured, notifications are rejected rather than silently trusted.
    """
    server_key = os.getenv("MIDTRANS_SERVER_KEY")
    if not server_key:
        raise HTTPException(503, "Midtrans sandbox is not configured")
    payload = await request.json()
    order_number = str(payload.get("order_id", ""))
    status_code = str(payload.get("status_code", ""))
    gross_amount = str(payload.get("gross_amount", ""))
    signature = str(payload.get("signature_key", ""))
    expected = hashlib.sha512(f"{order_number}{status_code}{gross_amount}{server_key}".encode()).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected):
        raise HTTPException(400, "Invalid payment notification signature")
    order = next((item for item in access.ORDERS.values() if item["order_number"] == order_number), None)
    if not order:
        raise HTTPException(404, "Unknown order reference")
    if int(float(gross_amount)) != order["total_minor"] or payload.get("currency", order["currency"]) != order["currency"]:
        raise HTTPException(400, "Payment amount or currency does not match the order")
    event_key = f"midtrans:{payload.get('transaction_id', order_number)}:{payload.get('transaction_status', 'unknown')}"
    if event_key not in access.PAYMENT_EVENTS:
        access.PAYMENT_EVENTS[event_key] = {"id": event_key, "order_id": order["id"], "event_type": payload.get("transaction_status"), "signature_valid": True, "status": "processed", "received_at": NOW()}
        if payload.get("transaction_status") in {"settlement", "capture"} and payload.get("fraud_status", "accept") == "accept":
            access.fulfill_order(order["id"], "midtrans_payment")
    return {"received": True, "processed": True, "order_status": order["status"]}


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
    return {"id": user["id"], "name": user["display_name"], "email": user["email"], "roles": user["roles"], "role": user["roles"][0], "account_status": user["account_status"], "mfa_verified": user["mfa_verified"], "consented": True}


@app.get("/assessments")
def assessments() -> List[Dict[str, Any]]:
    return [{"id": "iaq-cognitive", "name": "IAQ Cognitive Profile", "version": "IAQ-COG-0.3", "status": "experimental", "domains": list(DOMAINS), "question_bank_count": len(ITEMS), "questions_per_complete_form": 56, "questions_per_quick_form": 14, "duration_seconds": DURATION_SECONDS, "estimated_minutes": 35, "domain_quota": 8}]


def create_session(assessment_id: str, payload: SessionCreate, request: Optional[Request] = None) -> Dict[str, Any]:
    if assessment_id != "iaq-cognitive":
        raise HTTPException(404, "Assessment version unavailable")
    user = current_user(request)
    if not access.has_entitlement(user["id"], "assessment.complete.start"):
        raise HTTPException(402, "An IAQ Complete entitlement is required to start this assessment")
    session_id = str(uuid4())
    created_at = datetime.now(timezone.utc)
    deadline_at = created_at + timedelta(seconds=DURATION_SECONDS)
    item_order = create_randomized_form(payload.mode)
    session = {"id": session_id, "assessment_id": assessment_id, "assessment_version": payload.assessment_version, "mode": payload.mode, "status": "created", "responses": {}, "item_order": item_order, "created_at": created_at.isoformat(), "deadline_at": deadline_at.isoformat(), "duration_seconds": DURATION_SECONDS, "user_id": user["id"]}
    if PERSISTENCE:
        PERSISTENCE.create_session(session)
    else:
        SESSIONS[session_id] = session
    return {"id": session_id, "assessment_version": payload.assessment_version, "status": "created", "deadline_at": deadline_at.isoformat(), "duration_seconds": DURATION_SECONDS, "question_count": len(item_order), "domain_quota": 8 if payload.mode == "complete" else 2}


@app.post("/assessments/{assessment_id}/sessions")
def create_session_endpoint(assessment_id: str, payload: SessionCreate, request: Request) -> Dict[str, Any]:
    return create_session(assessment_id, payload, request)


@app.get("/sessions/{session_id}")
def get_session(session_id: str) -> Dict[str, Any]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {key: value for key, value in session.items() if key not in {"responses", "item_order"}} | {"answered_count": len(session["responses"]), "question_count": len(session["item_order"])}


@app.post("/sessions/{session_id}/start")
def start_session(session_id: str) -> Dict[str, Any]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
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
    return {"status": session["status"], "next_item": public_item(ITEMS[session["item_order"][0]])}


def session_expired(session: Dict[str, Any]) -> bool:
    return datetime.now(timezone.utc) >= datetime.fromisoformat(session["deadline_at"])


@app.get("/sessions/{session_id}/next-item")
def next_item(session_id: str) -> Dict[str, Any]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session["status"] == "in_progress" and session_expired(session):
        persist_session(session, {"status": "timed_out"})
        session["status"] = "timed_out"
        return {"complete": True, "expired": True}
    for item_id in session["item_order"]:
        if item_id not in session["responses"]:
            return public_item(ITEMS[item_id])
    return {"complete": True}


@app.post("/sessions/{session_id}/responses")
def submit_response(session_id: str, payload: ResponseCreate, idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key")) -> Dict[str, Any]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
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
    if payload.answer not in item["options"]:
        raise HTTPException(422, "Answer option is unavailable")
    if payload.item_id in session["responses"]:
        return {"accepted": True, "duplicate": True, "item_id": payload.item_id}
    response = {"item_id": payload.item_id, "answer": payload.answer, "response_time_ms": payload.response_time_ms, "presented_order": payload.presented_order, "idempotency_key": idempotency_key, "data_origin": "REAL_PILOT"}
    if PERSISTENCE:
        accepted = PERSISTENCE.insert_response(session_id, payload.item_id, payload.answer, payload.response_time_ms, payload.presented_order, idempotency_key)
        if not accepted:
            return {"accepted": True, "duplicate": True, "item_id": payload.item_id}
    else:
        session["responses"][payload.item_id] = response
    answered_count = len(session["responses"]) if not PERSISTENCE else len(session["responses"]) + 1
    return {"accepted": True, "duplicate": False, "item_id": payload.item_id, "answered_count": answered_count}


@app.post("/sessions/{session_id}/events")
def record_event(session_id: str, payload: EventCreate) -> Dict[str, Any]:
    if not session_for(session_id):
        raise HTTPException(404, "Session not found")
    event = {"id": str(uuid4()), "session_id": session_id, "event_type": payload.event_type, "metadata": payload.metadata, "created_at": NOW()}
    if PERSISTENCE:
        PERSISTENCE.insert_event(session_id, event["id"], payload.event_type, payload.metadata)
    else:
        EVENTS.append(event)
    return {"accepted": True, "event_id": event["id"]}


@app.post("/sessions/{session_id}/pause")
def pause_session(session_id: str) -> Dict[str, str]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    persist_session(session, {"status": "paused"})
    session["status"] = "paused"
    return {"status": "paused"}


@app.post("/sessions/{session_id}/resume")
def resume_session(session_id: str) -> Dict[str, str]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session_expired(session):
        raise HTTPException(409, "Assessment time has ended")
    persist_session(session, {"status": "in_progress"})
    session["status"] = "in_progress"
    return {"status": "in_progress"}


@app.post("/sessions/{session_id}/submit")
def submit_session(session_id: str) -> Dict[str, Any]:
    session = session_for(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.get("result_id"):
        if PERSISTENCE:
            existing = PERSISTENCE.get_result(session["result_id"])
            if existing:
                return existing
        if session["result_id"] in RESULTS:
            return RESULTS[session["result_id"]]
    item_domains = {key: value["domain"] for key, value in ITEMS.items()}
    item_keys = {key: value["answer"] for key, value in ITEMS.items()}
    score = score_domains(session["responses"].values(), item_domains, item_keys)
    quality = classify_session_quality([int(value["response_time_ms"]) for value in session["responses"].values()], sum(1 for event in EVENTS if event["session_id"] == session_id and event["event_type"] == "interruption"))
    result_id = str(uuid4())
    domain_metrics = {}
    for domain, metric in score.domain_metrics.items():
        value = score.domain_scores[domain]
        relative = "insufficient evidence" if value is None or score.composite is None else "stronger than your average" if value > score.composite + 3 else "lower than your average" if value < score.composite - 3 else "close to your average"
        domain_metrics[domain] = {**metric, "score": value, "relative": relative}
    RESULTS[result_id] = {"id": result_id, "session_id": session_id, "assessment_version": session["assessment_version"], "score_version": score.score_version, "composite": score.composite, "domain_scores": score.domain_scores, "domain_metrics": domain_metrics, "confidence": score.confidence, "quality": quality, "answered_count": len(session["responses"]), "question_count": len(session["item_order"]), "duration_seconds": session["duration_seconds"], "completed_at": NOW(), "created_at": NOW(), "disclaimer": SCORE_DISCLAIMER}
    if PERSISTENCE:
        PERSISTENCE.store_result(session_id, RESULTS[result_id])
        PERSISTENCE.update_session(session_id, {"status": "complete", "result_id": result_id})
    else:
        session["status"] = "complete"
        session["result_id"] = result_id
    return RESULTS[result_id]


def get_result(result_id: str, request: Optional[Request] = None) -> Dict[str, Any]:
    if result_id in RESULTS:
        result = RESULTS[result_id]
        if request:
            session = session_for(result["session_id"])
            if session and session.get("user_id") != current_user(request)["id"] and "platform_admin" not in current_user(request)["roles"]:
                raise HTTPException(404, "Result not found")
        return result
    if PERSISTENCE:
        result = PERSISTENCE.get_result(result_id)
        if result:
            if request and "platform_admin" not in current_user(request)["roles"] and result.get("user_id") not in {None, current_user(request)["id"]}:
                raise HTTPException(404, "Result not found")
            return result
    raise HTTPException(404, "Result not found")


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
    if set(payload.responses) - {item["id"] for item in INTEREST_ITEMS}:
        raise HTTPException(422, "Unknown interest dimension")
    if any(value < 0 or value > 100 for value in payload.responses.values()):
        raise HTTPException(422, "Interest ratings must be between 0 and 100")
    return access.store_interest_attempt(current_user(request)["id"], payload.responses)


@app.get("/me/interests")
def my_interests(request: Request) -> Dict[str, Any]:
    return access.INTEREST_ATTEMPTS.get(current_user(request)["id"], {"status": "not_started", "scores": {}, "code": None})


@app.post("/consents")
def create_consent(payload: ConsentCreate) -> Dict[str, Any]:
    return {"id": str(uuid4()), "version": payload.consent_version, "purpose": payload.purpose, "granted": payload.granted, "recorded_at": NOW()}


@app.get("/majors")
def majors() -> List[Dict[str, Any]]:
    return [{key: value for key, value in major.items() if key != "vector"} for major in MAJORS]


@app.get("/recommendations")
def recommendations(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    user_results = [result for result in RESULTS.values() if session_for(result["session_id"]) and session_for(result["session_id"]).get("user_id") == user["id"]]
    latest = max(user_results, key=lambda result: result.get("completed_at", ""), default=None)
    cognitive = ({domain: value if isinstance(value, int) else 50 for domain, value in latest["domain_scores"].items()} if latest else {domain: 50 for domain in DOMAINS})
    interests = access.INTEREST_ATTEMPTS.get(user["id"], {}).get("scores", {"I": 50, "A": 50, "C": 50, "R": 50, "S": 50, "E": 50})
    return {"version": "MATCH-V2", "recommendations": [{**{key: value for key, value in major.items() if key != "vector"}, **major_fit(cognitive, interests, latest["answered_count"] if latest else 0, major["vector"]), "confidence": recommendation_confidence(latest["answered_count"] if latest else 0, .34, 5, 24)} for major in MAJORS], "explanations": {"method": "weighted transparent fit using the latest persisted cognitive result and optional stated interests; not destiny", "warnings": ["experimental_profile", "no_population_norms", "try_real_experiences_before_deciding"]}}


@app.post("/results/{result_id}/delivery")
def request_report_delivery(result_id: str, payload: ReportDeliveryCreate, request: Request) -> Dict[str, Any]:
    """Queue an optional private report delivery after the score is visible."""
    result = get_result(result_id, request)
    if not payload.granted:
        raise HTTPException(400, "Report delivery consent is required")
    if payload.age is not None and payload.age < 18:
        raise HTTPException(403, "Report delivery for minors requires guardian consent workflow")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", payload.email):
        raise HTTPException(422, "Enter a valid email address")
    key = f"{result_id}:{payload.email.strip().lower()}"
    existing = REPORT_DELIVERIES.get(key)
    if not existing and PERSISTENCE:
        existing = PERSISTENCE.get_report_delivery(result_id, payload.email.strip().lower())
    if existing:
        REPORT_DELIVERIES[key] = existing
        return existing
    delivery = {"id": str(uuid4()), "result_id": result_id, "name": payload.name.strip(), "email": payload.email.strip().lower(), "consent_version": payload.consent_version, "status": "QUEUED_DEV", "provider": "development_log", "requested_at": NOW(), "sent_at": None, "message": "Delivery recorded in development mode; no real email was sent."}
    REPORT_DELIVERIES[key] = delivery
    if PERSISTENCE:
        PERSISTENCE.store_report_delivery(delivery)
    return delivery


@app.post("/certificates")
def create_certificate(payload: CertificateCreate, request: Request) -> Dict[str, Any]:
    result = get_result(payload.result_id, request)
    if result.get("answered_count", 0) < 1:
        raise HTTPException(409, "A certificate needs a submitted assessment")
    return access.issue_certificate(current_user(request)["id"], result)


@app.get("/certificates")
def list_certificates(request: Request) -> Dict[str, Any]:
    user_id = current_user(request)["id"]
    return {"certificates": [item for item in access.CERTIFICATES.values() if item["user_id"] == user_id]}


@app.get("/certificates/{certificate_id}")
def get_certificate(certificate_id: str, request: Request) -> Dict[str, Any]:
    certificate = access.CERTIFICATES.get(certificate_id)
    if not certificate or (certificate["user_id"] != current_user(request)["id"] and "platform_admin" not in current_user(request)["roles"]):
        raise HTTPException(404, "Certificate not found")
    return certificate


@app.get("/certificates/verify/{identifier}")
def verify_certificate(identifier: str) -> Dict[str, Any]:
    certificate = access.certificate_for_identifier(identifier)
    if not certificate:
        return {"valid": False, "status": "not_found", "certificate_identifier": identifier}
    return {"valid": certificate["status"] == "issued", "status": certificate["status"], "certificate_identifier": certificate["certificate_identifier"], "title": certificate["title"], "assessment_version": certificate["assessment_version"], "issued_at": certificate["issued_at"]}


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
    return {"items": [public_item(item) for item in items], "total": len(items), "filters": {"status": status, "domain": domain}}


@app.get("/admin/items/{item_id}")
def admin_item(item_id: str, request: Request) -> Dict[str, Any]:
    require_permission(current_user(request), "content.items.read")
    item = ITEMS.get(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return public_item(item)


@app.post("/admin/items/{item_id}/review")
def review_item(item_id: str, payload: ItemReviewCreate, request: Request) -> Dict[str, Any]:
    require_permission(current_user(request), "content.items.review")
    item = ITEMS.get(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    item["status"] = payload.status
    item["lifecycle_status"] = payload.status
    item["last_review_notes"] = payload.notes
    item["last_reviewed_at"] = NOW()
    return {"accepted": True, "item": public_item(item)}


def update_item_status(item_id: str, status: str, request: Optional[Request] = None) -> Dict[str, Any]:
    if request:
        require_permission(current_user(request), "content.items.review")
    item = ITEMS.get(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    item["status"] = status
    item["lifecycle_status"] = status
    return {"accepted": True, "item": public_item(item)}


@app.post("/admin/items/{item_id}/activate")
def activate_item(item_id: str, request: Request) -> Dict[str, Any]:
    return update_item_status(item_id, "ACTIVE", request)


@app.post("/admin/items/{item_id}/suspend")
def suspend_item(item_id: str, request: Request) -> Dict[str, Any]:
    return update_item_status(item_id, "SUSPENDED", request)


@app.post("/admin/items/{item_id}/retire")
def retire_item(item_id: str, request: Request) -> Dict[str, Any]:
    return update_item_status(item_id, "RETIRED", request)


def question_bank_summary(request: Optional[Request] = None) -> Dict[str, Any]:
    """Expose safe operational metadata for the question-studio dashboard."""
    if request:
        require_permission(current_user(request), "content.health.read")
    lifecycle_counts: Dict[str, int] = {}
    origin_counts: Dict[str, int] = {}
    family_counts: Dict[str, int] = {}
    for item in ITEMS.values():
        lifecycle_counts[item.get("lifecycle_status", item.get("status", "UNKNOWN"))] = lifecycle_counts.get(item.get("lifecycle_status", item.get("status", "UNKNOWN")), 0) + 1
        origin_counts[item.get("data_origin", "UNKNOWN")] = origin_counts.get(item.get("data_origin", "UNKNOWN"), 0) + 1
        family_counts[item.get("item_family_id", item["id"])] = family_counts.get(item.get("item_family_id", item["id"]), 0) + 1
    eligible = [item for item in ITEMS.values() if item.get("status") in {"PILOT", "ACTIVE"}]
    return {
        "total": len(ITEMS),
        "minimum_per_domain": MINIMUM_ITEMS_PER_DOMAIN,
        "target_per_domain": TARGET_ITEMS_PER_DOMAIN,
        "counts": bank_counts(),
        "ready": bank_is_ready(),
        "form_sizes": {"quick": 14, "complete": 56},
        "difficulty_label": "medium_hard",
        "lifecycle": "PILOT",
        "generated_count": sum(1 for item in ITEMS.values() if item.get("data_origin") == "ORIGINAL_GENERATED"),
        "reviewed_count": sum(1 for item in ITEMS.values() if item.get("data_origin") == "REVIEWED_CONTENT"),
        "eligible_counts": bank_counts(eligible),
        "lifecycle_counts": lifecycle_counts,
        "origin_counts": origin_counts,
        "unique_family_count": len(family_counts),
        "review_gate": "Generated candidates remain PILOT until human review and real pilot data support activation.",
    }


@app.get("/admin/question-bank/summary")
def question_bank_summary_endpoint(request: Request) -> Dict[str, Any]:
    return question_bank_summary(request)
