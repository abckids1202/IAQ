"""Local, provider-neutral identity and commerce boundary for IAQ.

The development provider is deliberately explicit. It gives the frontend a
complete workflow without pretending that a browser-only demo is production
authentication or payment. Production adapters can replace these repositories
without changing the API contracts.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
import secrets
from typing import Any, Dict, List, Optional
from uuid import uuid4

# The local repository below is intentionally useful for previews and tests,
# but it is not a durable production access store. Keep this explicit so a
# deployment cannot become "ready" merely because an environment variable
# says postgres while orders, entitlements, and consent still use dictionaries.
POSTGRES_ACCESS_STORE_READY = False


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "student": [
        "profile.read", "profile.update", "assessment.start", "result.self.read",
        "direction.self.read", "entitlement.self.read", "order.self.create",
    ],
    "guardian": [
        "profile.read", "profile.update", "order.self.create", "order.dependent.create",
        "relationship.read", "consent.manage", "entitlement.self.read",
    ],
    "counselor": [
        "profile.read", "school.students.read", "school.reports.read",
        "school.notes.write", "school.followups.write",
    ],
    "school_admin": [
        "profile.read", "school.members.manage", "school.seats.read",
        "school.seats.allocate", "school.billing.read",
    ],
    "content_reviewer": [
        "profile.read", "content.items.read", "content.items.review", "content.health.read",
    ],
    "platform_admin": [
        "profile.read", "admin.users.read", "admin.schools.manage", "admin.products.manage",
        "admin.orders.read", "admin.payments.read", "admin.entitlements.manage",
        "admin.audit.read", "content.items.review",
    ],
}


USERS: Dict[str, Dict[str, Any]] = {
    "demo-student": {
        "id": "demo-student", "email": "student@iaq.local", "display_name": "Ari Pratama",
        "roles": ["student"], "account_status": "active", "age_band": "15-17",
        "school_id": "school-demo", "mfa_verified": True,
    },
    "demo-guardian": {
        "id": "demo-guardian", "email": "guardian@iaq.local", "display_name": "Sari Pratama",
        "roles": ["guardian"], "account_status": "active", "age_band": "adult",
        "school_id": None, "mfa_verified": True,
    },
    "demo-counselor": {
        "id": "demo-counselor", "email": "counselor@iaq.local", "display_name": "Maya Putri",
        "roles": ["counselor"], "account_status": "active", "age_band": "adult",
        "school_id": "school-demo", "mfa_verified": True,
    },
    "demo-school-admin": {
        "id": "demo-school-admin", "email": "school-admin@iaq.local", "display_name": "Bima Santoso",
        "roles": ["school_admin"], "account_status": "active", "age_band": "adult",
        "school_id": "school-demo", "mfa_verified": True,
    },
    "demo-admin": {
        "id": "demo-admin", "email": "admin@iaq.local", "display_name": "IAQ Platform Admin",
        "roles": ["platform_admin", "content_reviewer"], "account_status": "active", "age_band": "adult",
        "school_id": None, "mfa_verified": True,
    },
}

SESSIONS: Dict[str, Dict[str, Any]] = {}
GUARDIAN_RELATIONSHIPS: Dict[str, Dict[str, Any]] = {
    "demo-guardian:demo-student": {
        "guardian_id": "demo-guardian", "student_id": "demo-student", "status": "verified",
        "consent_scope": "purchase_and_report", "created_at": now(),
    }
}
COUNSELOR_ASSIGNMENTS = {"demo-counselor:demo-student"}

PRODUCTS: Dict[str, Dict[str, Any]] = {
    "iaq-free": {
        "id": "iaq-free", "code": "IAQ_FREE", "name": "Free IAQ",
        "description": "A guided IAQ preview with a concise within-profile result.",
        "entitlement_code": "assessment.free.start", "report_code": "report.preview",
        "price_id": "price-free-idr", "amount_minor": 0, "currency": "IDR", "active": True,
    },
    "iaq-complete": {
        "id": "iaq-complete", "code": "IAQ_COMPLETE", "name": "IAQ Complete",
        "description": "The full 56-question assessment, visual report, and direction exploration.",
        "entitlement_code": "assessment.complete.start", "report_code": "assessment.complete.report",
        "price_id": "price-complete-idr", "amount_minor": 14900000, "currency": "IDR", "active": True,
    },
    "iaq-reassessment": {
        "id": "iaq-reassessment", "code": "IAQ_REASSESSMENT", "name": "IAQ Reassessment Credit",
        "description": "One additional assessment attempt after your first profile.",
        "entitlement_code": "assessment.retake", "report_code": "assessment.complete.report",
        "price_id": "price-reassessment-idr", "amount_minor": 7900000, "currency": "IDR", "active": True,
    },
    "school-package": {
        "id": "school-package", "code": "SCHOOL_PACKAGE", "name": "School Package",
        "description": "A school seat package recorded through an approved invoice workflow.",
        "entitlement_code": "school.seat.complete", "report_code": "assessment.complete.report",
        "price_id": "price-school-idr", "amount_minor": 0, "currency": "IDR", "active": False,
    },
}

ORDERS: Dict[str, Dict[str, Any]] = {}
PAYMENT_ATTEMPTS: Dict[str, Dict[str, Any]] = {}
PAYMENT_EVENTS: Dict[str, Dict[str, Any]] = {}
ENTITLEMENTS: Dict[str, Dict[str, Any]] = {}
AUDIT_LOGS: List[Dict[str, Any]] = []
OTP_CODES: Dict[str, Dict[str, Any]] = {}
SCHOOL_LICENCES: Dict[str, Dict[str, Any]] = {
    "licence-demo": {"id": "licence-demo", "school_id": "school-demo", "seat_quantity": 25, "used_seats": 4, "status": "active", "source": "development_seed"}
}
SEAT_ALLOCATIONS: Dict[str, Dict[str, Any]] = {
    "seat-demo-1": {"id": "seat-demo-1", "licence_id": "licence-demo", "school_id": "school-demo", "student_id": "demo-student", "status": "active", "created_at": now()}
}
INTEREST_ATTEMPTS: Dict[str, Dict[str, Any]] = {}
CERTIFICATES: Dict[str, Dict[str, Any]] = {}
GUARDIAN_CONSENTS: Dict[str, Dict[str, Any]] = {}


def public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {key: user[key] for key in ("id", "email", "display_name", "roles", "account_status", "age_band", "school_id", "mfa_verified")}


def permissions_for(user: Dict[str, Any]) -> List[str]:
    return sorted({permission for role in user["roles"] for permission in ROLE_PERMISSIONS.get(role, [])})


def issue_dev_session(user_id: str) -> str:
    token = f"iaq-dev-{uuid4()}"
    SESSIONS[token] = {"user_id": user_id, "created_at": now(), "provider": "development"}
    return token


def user_for_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    session = SESSIONS.get(token)
    if not session:
        return None
    return USERS.get(session["user_id"])


def user_for_identifier(identifier: Optional[str]) -> Dict[str, Any]:
    if identifier in USERS:
        return USERS[identifier]  # type: ignore[index]
    for user in USERS.values():
        if user["email"].lower() == (identifier or "").lower():
            return user
    return USERS["demo-student"]


def get_or_create_student(email: str) -> Dict[str, Any]:
    for user in USERS.values():
        if user["email"].lower() == email.lower():
            return user
    user_id = f"student-{uuid4().hex[:12]}"
    user = {"id": user_id, "email": email.lower(), "display_name": email.split("@")[0].replace(".", " ").title(), "roles": ["student"], "account_status": "onboarding_incomplete", "age_band": "unknown", "school_id": None, "mfa_verified": True}
    USERS[user_id] = user
    add_entitlement(user_id, "assessment.free.start", "account_creation", f"free:{user_id}", quantity=1, granted_by="system")
    return user


def record_audit(actor_id: str, action: str, resource_type: str, resource_id: Optional[str], metadata: Optional[Dict[str, Any]] = None) -> None:
    AUDIT_LOGS.append({"id": str(uuid4()), "actor_id": actor_id, "action": action, "resource_type": resource_type, "resource_id": resource_id, "metadata": metadata or {}, "created_at": now()})


def list_products() -> List[Dict[str, Any]]:
    products: List[Dict[str, Any]] = []
    for product in PRODUCTS.values():
        if not product["active"]:
            continue
        public = {key: value for key, value in product.items() if key not in {"entitlement_code", "report_code"}}
        if product["id"] == "iaq-complete":
            try:
                public["amount_minor"] = max(0, int(os.getenv("IAQ_FULL_REPORT_PRICE_IDR", str(public["amount_minor"]))))
            except ValueError:
                pass
        products.append(public)
    return products


def add_entitlement(owner_id: str, code: str, source_type: str, source_id: str, quantity: int = 1, granted_by: Optional[str] = None) -> Dict[str, Any]:
    for existing in ENTITLEMENTS.values():
        if existing["owner_id"] == owner_id and existing["code"] == code and existing["source_id"] == source_id and existing["status"] == "active":
            return existing
    entitlement = {
        "id": str(uuid4()), "code": code, "owner_type": "user", "owner_id": owner_id,
        "source_type": source_type, "source_id": source_id, "status": "active",
        "quantity": quantity, "remaining_quantity": quantity, "granted_by": granted_by,
        "created_at": now(), "expires_at": None,
    }
    ENTITLEMENTS[entitlement["id"]] = entitlement
    return entitlement


def has_entitlement(user_id: str, code: str) -> bool:
    return any(item["owner_id"] == user_id and item["code"] == code and item["status"] == "active" and item["remaining_quantity"] > 0 for item in ENTITLEMENTS.values())


def consume_entitlement(user_id: str, code: str, assessment_id: str) -> Optional[Dict[str, Any]]:
    for item in ENTITLEMENTS.values():
        if item["owner_id"] == user_id and item["code"] == code and item["status"] == "active" and item["remaining_quantity"] > 0:
            item["remaining_quantity"] -= 1
            item["status"] = "consumed" if item["remaining_quantity"] == 0 else "active"
            item["consumed_by"] = assessment_id
            item["consumed_at"] = now()
            return item
    return None


def seed_demo_entitlements() -> None:
    add_entitlement("demo-student", "assessment.free.start", "development_seed", "demo-free-assessment", quantity=99, granted_by="system")
    add_entitlement("demo-student", "assessment.complete.start", "development_seed", "demo-complete-assessment", quantity=99, granted_by="system")
    add_entitlement("demo-student", "assessment.complete.report", "development_seed", "demo-complete-report", quantity=99, granted_by="system")
    add_entitlement("demo-student", "report.download", "development_seed", "demo-report-download", quantity=99, granted_by="system")


def store_interest_attempt(user_id: str, responses: Dict[str, int]) -> Dict[str, Any]:
    """Store an exploratory interest check-in separately from cognitive scoring."""
    dimensions = ("R", "I", "A", "S", "E", "C")
    scores = {dimension: max(0, min(100, int(responses.get(dimension, 0)))) for dimension in dimensions}
    code = "".join(dimension for dimension, _ in sorted(scores.items(), key=lambda pair: pair[1], reverse=True)[:3])
    attempt = {
        "id": str(uuid4()), "user_id": user_id, "instrument": "RIASEC exploratory check-in",
        "instrument_version": "RIASEC-EXPLORATORY-0.1", "scores": scores, "code": code,
        "answered_count": len(responses), "data_origin": "REAL_PILOT", "status": "provisional", "created_at": now(),
    }
    INTEREST_ATTEMPTS[user_id] = attempt
    record_audit(user_id, "interest_attempt.created", "interest_attempt", attempt["id"], {"instrument_version": attempt["instrument_version"]})
    return attempt


def issue_certificate(user_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
    existing = next((item for item in CERTIFICATES.values() if item["user_id"] == user_id and item["result_id"] == result["id"] and item["status"] == "issued"), None)
    if existing:
        return existing
    identifier = f"IAQ-{secrets.token_hex(5).upper()}"
    certificate = {
        "id": str(uuid4()), "certificate_identifier": identifier, "user_id": user_id, "result_id": result["id"],
        "title": "IAQ Cognitive Profile completion", "assessment_version": result.get("assessment_version", "IAQ-COG-0.3"),
        "score_version": result.get("score_version", "SCORING-V1"), "status": "issued", "issued_at": now(),
        "verification_url": f"/verify?certificate={identifier}", "data_origin": "REAL_PILOT",
    }
    CERTIFICATES[certificate["id"]] = certificate
    record_audit(user_id, "certificate.issued", "certificate", certificate["id"], {"result_id": result["id"]})
    return certificate


def certificate_for_identifier(identifier: str) -> Optional[Dict[str, Any]]:
    return next((item for item in CERTIFICATES.values() if item["certificate_identifier"].upper() == identifier.strip().upper()), None)


def create_order(purchaser_id: str, product_id: str, beneficiary_id: Optional[str] = None, school_id: Optional[str] = None) -> Dict[str, Any]:
    product = PRODUCTS.get(product_id)
    if not product or not product["active"]:
        raise ValueError("Product is unavailable")
    beneficiary_id = beneficiary_id or purchaser_id
    if beneficiary_id != purchaser_id:
        relationship = GUARDIAN_RELATIONSHIPS.get(f"{purchaser_id}:{beneficiary_id}")
        if not relationship or relationship["status"] != "verified":
            raise PermissionError("A verified guardian relationship is required for this beneficiary")
    product = dict(product)
    if product_id == "iaq-complete":
        try:
            product["amount_minor"] = max(0, int(os.getenv("IAQ_FULL_REPORT_PRICE_IDR", str(product["amount_minor"]))))
        except ValueError:
            pass
    order_id = str(uuid4())
    order = {
        "id": order_id, "order_number": f"IAQ-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{order_id[:8].upper()}",
        "purchaser_user_id": purchaser_id, "beneficiary_user_id": beneficiary_id, "school_id": school_id,
        "product_id": product_id, "product_snapshot": {key: value for key, value in product.items() if key not in {"entitlement_code", "report_code"}},
        "price_id": product["price_id"], "price_snapshot": {"amount_minor": product["amount_minor"], "currency": product["currency"]},
        "currency": product["currency"], "subtotal_minor": product["amount_minor"], "discount_minor": 0, "tax_minor": 0,
        "total_minor": product["amount_minor"], "status": "awaiting_payment" if product["amount_minor"] else "paid",
        "terms_accepted_at": now(), "created_at": now(), "updated_at": now(),
    }
    ORDERS[order_id] = order
    record_audit(purchaser_id, "order.created", "order", order_id, {"product_id": product_id, "beneficiary_user_id": beneficiary_id})
    if product["amount_minor"] == 0:
        fulfill_order(order_id, "development_free")
    return order


def fulfill_order(order_id: str, source_type: str) -> Dict[str, Any]:
    order = ORDERS[order_id]
    if order["status"] == "fulfilled":
        return order
    product = PRODUCTS[order["product_id"]]
    order["status"] = "fulfilled"
    order["updated_at"] = now()
    add_entitlement(order["beneficiary_user_id"], product["entitlement_code"], source_type, order_id, quantity=1, granted_by=order["purchaser_user_id"])
    if product.get("report_code"):
        add_entitlement(order["beneficiary_user_id"], product["report_code"], source_type, order_id, quantity=1, granted_by=order["purchaser_user_id"])
    record_audit(order["purchaser_user_id"], "entitlement.granted", "order", order_id, {"beneficiary_user_id": order["beneficiary_user_id"]})
    return order


def create_payment_attempt(order_id: str) -> Dict[str, Any]:
    order = ORDERS[order_id]
    for attempt in PAYMENT_ATTEMPTS.values():
        if attempt["order_id"] == order_id and attempt["status"] == "pending":
            return attempt
    attempt_id = str(uuid4())
    attempt = {
        "id": attempt_id, "order_id": order_id, "provider": "mock", "provider_order_id": order["order_number"],
        "checkout_token": f"mock-snap-{uuid4()}", "redirect_url": f"/checkout/{order_id}/pay",
        "amount_minor": order["total_minor"], "currency": order["currency"], "status": "pending",
        "provider_status": "pending", "idempotency_key": f"order:{order_id}", "created_at": now(), "updated_at": now(),
    }
    PAYMENT_ATTEMPTS[attempt_id] = attempt
    order["status"] = "payment_pending"
    order["updated_at"] = now()
    return attempt


def settle_mock_payment(order_id: str, actor_id: str) -> Dict[str, Any]:
    order = ORDERS.get(order_id)
    if not order:
        raise KeyError("Order not found")
    if order["purchaser_user_id"] != actor_id and actor_id != "demo-admin":
        raise PermissionError("Only the purchaser or platform admin can settle this sandbox payment")
    attempt = next((item for item in PAYMENT_ATTEMPTS.values() if item["order_id"] == order_id), None)
    if not attempt:
        attempt = create_payment_attempt(order_id)
    event_key = f"mock:{order_id}:settlement"
    if event_key in PAYMENT_EVENTS:
        return order
    attempt["status"] = "settlement"
    attempt["provider_status"] = "settlement"
    attempt["updated_at"] = now()
    order["status"] = "paid"
    PAYMENT_EVENTS[event_key] = {"id": event_key, "order_id": order_id, "event_type": "settlement", "signature_valid": True, "status": "processed", "received_at": now()}
    fulfill_order(order_id, "mock_payment")
    return order


def orders_for(user_id: str) -> List[Dict[str, Any]]:
    return [order for order in ORDERS.values() if order["purchaser_user_id"] == user_id or order["beneficiary_user_id"] == user_id]


def school_seats(school_id: str) -> Dict[str, Any]:
    licence = next((item for item in SCHOOL_LICENCES.values() if item["school_id"] == school_id and item["status"] == "active"), None)
    allocations = [item for item in SEAT_ALLOCATIONS.values() if item["school_id"] == school_id and item["status"] == "active"]
    return {"licence": licence, "allocations": allocations, "available_seats": max(0, (licence["seat_quantity"] if licence else 0) - len(allocations))}


def allocate_school_seat(school_id: str, student_id: str, actor_id: str) -> Dict[str, Any]:
    snapshot = school_seats(school_id)
    if not snapshot["licence"] or snapshot["available_seats"] <= 0:
        raise ValueError("No school seats are available")
    if any(item["student_id"] == student_id for item in snapshot["allocations"]):
        raise ValueError("This student already has an active seat")
    allocation_id = str(uuid4())
    allocation = {"id": allocation_id, "licence_id": snapshot["licence"]["id"], "school_id": school_id, "student_id": student_id, "status": "active", "created_at": now(), "allocated_by": actor_id}
    SEAT_ALLOCATIONS[allocation_id] = allocation
    add_entitlement(student_id, "school.seat.complete", "school_seat", allocation_id, quantity=1, granted_by=actor_id)
    add_entitlement(student_id, "assessment.complete.start", "school_seat", allocation_id, quantity=1, granted_by=actor_id)
    record_audit(actor_id, "school.seat.allocated", "school_seat", allocation_id, {"school_id": school_id, "student_id": student_id})
    return allocation


seed_demo_entitlements()
