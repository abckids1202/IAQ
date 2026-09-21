"""Small PostgreSQL adapter for the assessment and results boundary.

The API keeps its dependency-light in-memory mode for local UI previews. When
IAQ_DATABASE_URL is configured, this adapter makes sessions, responses, and
results durable without exposing answer keys to the client.
"""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, NAMESPACE_URL, uuid5

import psycopg


class PostgresAssessmentStore:
    def __init__(self, database_url: str):
        self.dsn = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def _connection(self):
        return psycopg.connect(self.dsn)

    def _ensure_reference_data(self, cursor, assessment_version: str) -> str:
        cursor.execute(
            """
            INSERT INTO assessment_definitions (slug, name)
            VALUES ('iaq-cognitive', 'IAQ Cognitive Profile')
            ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """
        )
        definition_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO assessment_versions (definition_id, version, scoring_model_version, norm_version, status)
            VALUES (%s, %s, 'SCORING-V1', NULL, 'PILOT')
            ON CONFLICT (version) DO UPDATE SET status = EXCLUDED.status
            RETURNING id
            """,
            (definition_id, assessment_version),
        )
        return str(cursor.fetchone()[0])

    def _db_user_id(self, external_user_id: str) -> str:
        """Map local/demo identities to stable UUIDs without a shared user."""
        try:
            return str(UUID(external_user_id))
        except (ValueError, AttributeError):
            return str(uuid5(NAMESPACE_URL, f"https://iaq.local/user/{external_user_id}"))

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def ensure_user(self, external_user_id: str, email: str, display_name: str = "IAQ student", age_band: str = "unknown", role: str = "student") -> str:
        """Provision the application-side identity for a Supabase or guest user."""
        database_user_id = self._db_user_id(external_user_id)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (id, email, role)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email
                    """,
                    (database_user_id, email.strip().lower(), role if role in {"student", "guardian", "counselor", "school_admin", "content_reviewer", "platform_admin", "reviewer", "admin"} else "student"),
                )
                cursor.execute(
                    """
                    INSERT INTO profiles (user_id, display_name, age_band)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET display_name = EXCLUDED.display_name, age_band = EXCLUDED.age_band, updated_at = now()
                    """,
                    (database_user_id, display_name.strip() or "IAQ student", age_band),
                )
        return database_user_id

    def store_guest_session(self, external_user_id: str, token: str, expires_at: str, email: str, display_name: str = "Guest") -> None:
        database_user_id = self.ensure_user(external_user_id, email, display_name, "unknown", "student")
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO guest_sessions (token_hash, external_user_id, user_id, expires_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (token_hash) DO UPDATE SET expires_at = EXCLUDED.expires_at, revoked_at = NULL
                    """,
                    (self._token_hash(token), external_user_id, database_user_id, expires_at),
                )

    def get_guest_user(self, token: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT gs.external_user_id, u.email, COALESCE(p.display_name, 'Guest'), COALESCE(p.age_band, 'unknown')
                    FROM guest_sessions gs
                    JOIN users u ON u.id = gs.user_id
                    LEFT JOIN profiles p ON p.user_id = gs.user_id
                    WHERE gs.token_hash = %s AND gs.revoked_at IS NULL AND gs.expires_at > now()
                    """,
                    (self._token_hash(token),),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0], "email": row[1], "display_name": row[2], "roles": ["guest"],
                    "account_status": "guest", "age_band": row[3], "school_id": None,
                    "mfa_verified": False, "is_guest": True,
                }

    def store_guest_identity(self, result_id: str, external_guest_user_id: str, token: str, email: str, display_name: str, age_band: str, consent_version: str, expires_at: str) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO guest_result_identities
                      (result_id, external_guest_user_id, email, display_name, age_band, consent_version, token_hash, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (result_id) DO UPDATE SET email = EXCLUDED.email, display_name = EXCLUDED.display_name,
                      age_band = EXCLUDED.age_band, consent_version = EXCLUDED.consent_version,
                      token_hash = EXCLUDED.token_hash, expires_at = EXCLUDED.expires_at
                    """,
                    (result_id, external_guest_user_id, email.strip().lower(), display_name.strip(), age_band, consent_version, self._token_hash(token), expires_at),
                )

    def get_guest_identity(self, result_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT result_id, external_guest_user_id, email, display_name, age_band, consent_version, captured_at, expires_at
                    FROM guest_result_identities WHERE result_id = %s
                    """,
                    (result_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return {"result_id": str(row[0]), "user_id": row[1], "email": row[2], "display_name": row[3], "age_band": row[4], "consent_version": row[5], "captured_at": row[6].isoformat(), "expires_at": row[7].isoformat()}

    def claim_guest_result(self, result_id: str, external_guest_user_id: str, external_user_id: str, email: str, display_name: str, age_band: str) -> bool:
        guest_database_id = self._db_user_id(external_guest_user_id)
        user_database_id = self.ensure_user(external_user_id, email, display_name, age_band, "student")
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE test_sessions ts
                    SET user_id = %s, external_user_id = %s
                    FROM assessment_results ar
                    WHERE ar.id = %s AND ts.id = ar.session_id AND ts.user_id = %s
                    """,
                    (user_database_id, external_user_id, result_id, guest_database_id),
                )
                changed = cursor.rowcount > 0
                if changed:
                    cursor.execute("DELETE FROM guest_result_identities WHERE result_id = %s", (result_id,))
                return changed

    def store_order(self, order: Dict[str, Any]) -> None:
        purchaser = str(order["purchaser_user_id"])
        beneficiary = str(order["beneficiary_user_id"])
        purchaser_db_id = self.ensure_user(purchaser, f"{purchaser}@local.iaq")
        beneficiary_db_id = self.ensure_user(beneficiary, f"{beneficiary}@local.iaq")
        try:
            school_id = str(UUID(str(order["school_id"]))) if order.get("school_id") else None
        except (ValueError, AttributeError):
            school_id = None
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO orders
                      (id, order_number, purchaser_user_id, beneficiary_user_id, school_id, result_id,
                       purchaser_external_user_id, beneficiary_external_user_id, currency, subtotal_minor,
                       discount_minor, tax_minor, total_minor, status, product_snapshot, price_snapshot,
                       terms_accepted_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status, result_id = EXCLUDED.result_id,
                      updated_at = EXCLUDED.updated_at
                    """,
                    (
                        order["id"], order["order_number"], purchaser_db_id, beneficiary_db_id, school_id,
                        order.get("result_id"), purchaser, beneficiary, order["currency"], order["subtotal_minor"],
                        order["discount_minor"], order["tax_minor"], order["total_minor"], order["status"],
                        json.dumps(order["product_snapshot"]), json.dumps({**order["price_snapshot"], "id": order.get("price_id")}),
                        order["terms_accepted_at"], order["created_at"], order["updated_at"],
                    ),
                )

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, order_number, purchaser_external_user_id, beneficiary_external_user_id, school_id,
                           result_id, currency, subtotal_minor, discount_minor, tax_minor, total_minor, status,
                           product_snapshot, price_snapshot, terms_accepted_at, created_at, updated_at
                    FROM orders WHERE id = %s
                    """,
                    (order_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                product = row[12] if isinstance(row[12], dict) else json.loads(row[12])
                price = row[13] if isinstance(row[13], dict) else json.loads(row[13])
                return {
                    "id": str(row[0]), "order_number": row[1], "purchaser_user_id": row[2], "beneficiary_user_id": row[3],
                    "school_id": str(row[4]) if row[4] else None, "result_id": str(row[5]) if row[5] else None,
                    "product_id": product.get("id"), "product_snapshot": product, "price_id": price.get("id"),
                    "price_snapshot": price, "currency": row[6], "subtotal_minor": row[7], "discount_minor": row[8],
                    "tax_minor": row[9], "total_minor": row[10], "status": row[11],
                    "terms_accepted_at": row[14].isoformat(), "created_at": row[15].isoformat(), "updated_at": row[16].isoformat(),
                }

    def get_order_for_result(self, external_user_id: str, result_id: str) -> Optional[Dict[str, Any]]:
        user_db_id = self._db_user_id(external_user_id)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM orders WHERE result_id = %s AND (purchaser_user_id = %s OR beneficiary_user_id = %s) AND status IN ('awaiting_payment','proof_submitted','payment_proof_rejected','fulfilled','paid') ORDER BY created_at DESC LIMIT 1",
                    (result_id, user_db_id, user_db_id),
                )
                row = cursor.fetchone()
                return self.get_order(str(row[0])) if row else None

    def list_orders_for_user(self, external_user_id: str) -> List[Dict[str, Any]]:
        user_db_id = self._db_user_id(external_user_id)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM orders WHERE purchaser_user_id = %s OR beneficiary_user_id = %s ORDER BY created_at DESC",
                    (user_db_id, user_db_id),
                )
                order_ids = [str(row[0]) for row in cursor.fetchall()]
        return [order for order_id in order_ids if (order := self.get_order(order_id))]

    def list_entitlements_for_user(self, external_user_id: str) -> List[Dict[str, Any]]:
        user_db_id = self._db_user_id(external_user_id)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, code, owner_type, owner_id, source_type, source_id, status, quantity, remaining_quantity, granted_by, granted_at, expires_at FROM entitlements WHERE owner_id = %s ORDER BY granted_at DESC",
                    (user_db_id,),
                )
                return [
                    {"id": str(row[0]), "code": row[1], "owner_type": row[2], "owner_id": external_user_id, "source_type": row[4], "source_id": str(row[5]) if row[5] else None, "status": row[6], "quantity": row[7], "remaining_quantity": row[8], "granted_by": str(row[9]) if row[9] else None, "granted_at": row[10].isoformat() if row[10] else None, "expires_at": row[11].isoformat() if row[11] else None}
                    for row in cursor.fetchall()
                ]

    def consume_entitlement(self, external_user_id: str, code: str, assessment_id: str) -> bool:
        """Consume one start credit atomically in the durable store."""
        user_db_id = self._db_user_id(external_user_id)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE entitlements
                    SET remaining_quantity = remaining_quantity - 1,
                        status = CASE WHEN remaining_quantity - 1 <= 0 THEN 'consumed' ELSE 'active' END
                    WHERE id = (
                        SELECT id FROM entitlements
                        WHERE owner_id = %s AND code = %s AND status = 'active' AND remaining_quantity > 0
                        ORDER BY granted_at ASC
                        FOR UPDATE SKIP LOCKED LIMIT 1
                    )
                    RETURNING id
                    """,
                    (user_db_id, code),
                )
                return cursor.fetchone() is not None

    def list_results_for_user(self, external_user_id: str) -> List[Dict[str, Any]]:
        """Return durable results owned by one external user, newest first."""
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ar.id
                    FROM assessment_results ar
                    JOIN test_sessions ts ON ts.id = ar.session_id
                    WHERE COALESCE(ts.external_user_id, ts.user_id::text) = %s
                    ORDER BY ar.completed_at DESC
                    """,
                    (external_user_id,),
                )
                result_ids = [str(row[0]) for row in cursor.fetchall()]
        return [result for result_id in result_ids if (result := self.get_result(result_id))]

    def store_entitlements_for_order(self, order: Dict[str, Any], codes: List[str], granted_by: Optional[str]) -> None:
        owner_db_id = self._db_user_id(str(order["beneficiary_user_id"]))
        grantor_db_id = self._db_user_id(str(granted_by)) if granted_by else None
        with self._connection() as connection:
            with connection.cursor() as cursor:
                for code in codes:
                    cursor.execute(
                        """
                        INSERT INTO entitlements (code, owner_type, owner_id, source_type, source_id, status, quantity, remaining_quantity, granted_by)
                        VALUES (%s, 'user', %s, 'manual_qris_admin_verified', %s, 'active', 1, 1, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (code, owner_db_id, order["id"], grantor_db_id),
                    )

    def has_result_entitlement(self, external_user_id: str, result_id: str) -> bool:
        user_db_id = self._db_user_id(external_user_id)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1 FROM entitlements e
                    JOIN orders o ON o.id = e.source_id
                    WHERE e.owner_id = %s AND e.status = 'active' AND e.remaining_quantity > 0
                      AND e.code IN ('assessment.complete.report', 'report.download')
                      AND o.result_id = %s AND o.status = 'fulfilled'
                    LIMIT 1
                    """,
                    (user_db_id, result_id),
                )
                return cursor.fetchone() is not None

    def store_payment_proof(self, proof: Dict[str, Any], content: bytes, idempotency_key: Optional[str]) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO payment_proofs
                      (id, order_id, user_id, idempotency_key, filename, content_type, content, size_bytes, transaction_ref, status, note, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    """,
                    (proof["id"], proof["order_id"], self._db_user_id(proof["user_id"]), idempotency_key, proof["filename"], proof["content_type"], content, proof["size"], proof.get("transaction_ref"), proof["status"], proof.get("note", ""), proof["created_at"], proof["updated_at"]),
                )

    def get_payment_proof(self, proof_id: str, include_content: bool = False) -> Optional[Dict[str, Any]]:
        columns = "id, order_id, user_id, idempotency_key, filename, content_type, size_bytes, transaction_ref, status, note, reviewed_by, created_at, updated_at"
        if include_content:
            columns += ", content"
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT {columns} FROM payment_proofs WHERE id = %s", (proof_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                base = {"id": str(row[0]), "order_id": str(row[1]), "user_id": str(row[2]), "idempotency_key": row[3], "filename": row[4], "content_type": row[5], "size": row[6], "transaction_ref": row[7], "status": row[8], "note": row[9], "reviewed_by": str(row[10]) if row[10] else None, "created_at": row[11].isoformat(), "updated_at": row[12].isoformat()}
                if include_content:
                    base["content"] = bytes(row[13])
                return base

    def get_payment_proof_by_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM payment_proofs WHERE idempotency_key = %s", (idempotency_key,))
                row = cursor.fetchone()
                return self.get_payment_proof(str(row[0])) if row else None

    def update_payment_proof(self, proof_id: str, status: str, note: str, reviewed_by: Optional[str] = None) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE payment_proofs SET status = %s, note = %s, reviewed_by = %s, updated_at = now() WHERE id = %s", (status, note, self._db_user_id(reviewed_by) if reviewed_by else None, proof_id))

    def list_payment_proofs(self) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM payment_proofs ORDER BY created_at DESC")
                return [self.get_payment_proof(str(row[0])) for row in cursor.fetchall()]

    def store_qris_settings(self, settings: Dict[str, Any], admin_id: str) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO qris_settings (id, merchant_name, instructions, image_filename, image, image_content_type, updated_by)
                    VALUES ('default', %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET merchant_name = EXCLUDED.merchant_name, instructions = EXCLUDED.instructions,
                      image_filename = EXCLUDED.image_filename, image = EXCLUDED.image, image_content_type = EXCLUDED.image_content_type,
                      updated_by = EXCLUDED.updated_by, updated_at = now()
                    """,
                    (settings["merchant_name"], settings["instructions"], settings.get("image_filename"), settings.get("image_bytes"), settings.get("image_content_type"), self._db_user_id(admin_id)),
                )

    def get_qris_settings(self) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT merchant_name, instructions, image_filename, image, image_content_type FROM qris_settings WHERE id = 'default'")
                row = cursor.fetchone()
                if not row:
                    return None
                return {"merchant_name": row[0], "instructions": row[1], "image_filename": row[2], "image_bytes": bytes(row[3]) if row[3] is not None else None, "image_content_type": row[4]}

    def store_interest_attempt(self, attempt: Dict[str, Any]) -> None:
        user_db_id = self._db_user_id(attempt["user_id"])
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO interest_instruments (slug, version, language, status, scoring_version)
                    VALUES ('compass-v1', %s, 'en', 'PILOT', %s)
                    ON CONFLICT (slug) DO UPDATE SET version = EXCLUDED.version, scoring_version = EXCLUDED.scoring_version
                    RETURNING id
                    """,
                    (attempt["instrument_version"], attempt["instrument_version"]),
                )
                instrument_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    INSERT INTO interest_attempts
                      (id, user_id, instrument_id, status, language, response_snapshot, result_snapshot, started_at, completed_at)
                    VALUES (%s, %s, %s, 'COMPLETED', 'en', %s::jsonb, %s::jsonb, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (attempt["id"], user_db_id, instrument_id, json.dumps(attempt.get("responses", {})), json.dumps({"result_id": attempt.get("result_id"), "scores": attempt["scores"], "code": attempt["code"], "version": attempt["instrument_version"]}), attempt["created_at"], attempt["created_at"]),
                )

    def get_interest_attempt(self, external_user_id: str, result_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        user_db_id = self._db_user_id(external_user_id)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ia.id, ia.user_id, ia.response_snapshot, ia.result_snapshot, ia.started_at, ia.completed_at, ii.version
                    FROM interest_attempts ia
                    JOIN interest_instruments ii ON ii.id = ia.instrument_id
                    WHERE ia.user_id = %s
                      AND (%s IS NULL OR ia.result_snapshot->>'result_id' = %s)
                    ORDER BY ia.completed_at DESC NULLS LAST
                    LIMIT 1
                    """,
                    (user_db_id, result_id, result_id),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                result = row[3] if isinstance(row[3], dict) else json.loads(row[3] or "{}")
                responses = row[2] if isinstance(row[2], dict) else json.loads(row[2] or "{}")
                return {"id": str(row[0]), "user_id": external_user_id, "instrument": "RIASEC exploratory check-in", "instrument_version": row[6], "scores": result.get("scores", {}), "code": result.get("code"), "answered_count": len(responses), "data_origin": "REAL_PILOT", "status": "provisional", "created_at": row[5].isoformat() if row[5] else row[4].isoformat(), "result_id": result.get("result_id") or result_id}

    def store_certificate(self, certificate: Dict[str, Any]) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO certificates
                      (id, result_id, user_id, certificate_identifier, title, language, audience, assessment_version, scoring_version, status, issued_at)
                    VALUES (%s, %s, %s, %s, %s, 'en', 'student', %s, %s, %s, %s)
                    ON CONFLICT (result_id, document_revision) DO NOTHING
                    """,
                    (certificate["id"], certificate["result_id"], self._db_user_id(certificate["user_id"]), certificate["certificate_identifier"], certificate["title"], certificate["assessment_version"], certificate["score_version"], certificate["status"], certificate["issued_at"]),
                )

    def get_certificate(self, certificate_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, result_id, user_id, certificate_identifier, title, assessment_version, scoring_version, status, issued_at FROM certificates WHERE id = %s",
                    (certificate_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return {"id": str(row[0]), "result_id": str(row[1]), "user_id": str(row[2]), "certificate_identifier": row[3], "title": row[4], "assessment_version": row[5], "score_version": row[6], "status": row[7], "issued_at": row[8].isoformat(), "verification_url": f"/verify?certificate={row[3]}"}

    def get_certificate_for_result(self, external_user_id: str, result_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM certificates WHERE result_id = %s AND user_id = %s AND status = 'issued' ORDER BY issued_at DESC LIMIT 1",
                    (result_id, self._db_user_id(external_user_id)),
                )
                row = cursor.fetchone()
                return self.get_certificate(str(row[0])) if row else None

    def list_certificates(self, external_user_id: str) -> List[Dict[str, Any]]:
        user_db_id = self._db_user_id(external_user_id)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM certificates WHERE user_id = %s ORDER BY issued_at DESC", (user_db_id,))
                return [certificate for row in cursor.fetchall() if (certificate := self.get_certificate(str(row[0])))]

    def certificate_for_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM certificates WHERE upper(certificate_identifier) = upper(%s) LIMIT 1", (identifier.strip(),))
                row = cursor.fetchone()
                return self.get_certificate(str(row[0])) if row else None

    def create_session(self, session: Dict[str, Any]) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                assessment_version_id = self._ensure_reference_data(cursor, session["assessment_version"])
                external_user_id = str(session.get("user_id", "demo-student"))
                database_user_id = self._db_user_id(external_user_id)
                cursor.execute(
                    """
                    INSERT INTO users (id, email, role)
                    VALUES (%s, %s, 'student')
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (database_user_id, f"{external_user_id}@local.iaq"),
                )
                cursor.execute(
                    """
                    INSERT INTO test_sessions (id, user_id, external_user_id, assessment_version_id, status, data_origin, started_at, deadline_at, duration_seconds, consent_snapshot, language, age_band)
                    VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s, %s::jsonb, %s, %s)
                    """,
                    (session["id"], database_user_id, external_user_id, assessment_version_id, session["status"], session.get("data_origin", "REAL_PILOT"), session["deadline_at"], session["duration_seconds"], json.dumps(session.get("consent_snapshot", {})), session.get("language", "en"), session.get("age_band", "unknown")),
                )
                for position, item_id in enumerate(session["item_order"]):
                    cursor.execute(
                        """
                        INSERT INTO assessment_form_items (session_id, item_version_id, domain, presented_order)
                        SELECT %s, iv.id, i.domain, %s
                        FROM items i JOIN LATERAL (
                            SELECT id FROM item_versions WHERE item_id = i.id ORDER BY version DESC LIMIT 1
                        ) iv ON TRUE
                        WHERE i.item_id = %s
                        ON CONFLICT (session_id, presented_order) DO NOTHING
                        """,
                        (session["id"], position, item_id),
                    )

    def store_identity(self, external_user_id: str, email: str, display_name: str, age_band: str, consent_version: str, granted: bool) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                database_user_id = self._db_user_id(external_user_id)
                cursor.execute(
                    """
                    INSERT INTO users (id, email, role)
                    VALUES (%s, %s, 'student')
                    ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email
                    """,
                    (database_user_id, email),
                )
                cursor.execute("SELECT 1 FROM profiles WHERE user_id = %s LIMIT 1", (database_user_id,))
                if cursor.fetchone():
                    cursor.execute("UPDATE profiles SET display_name = %s, age_band = %s, updated_at = now() WHERE user_id = %s", (display_name, age_band, database_user_id))
                else:
                    cursor.execute("INSERT INTO profiles (user_id, display_name, age_band) VALUES (%s, %s, %s)", (database_user_id, display_name, age_band))
                cursor.execute(
                    "INSERT INTO user_consents (user_id, consent_version, purpose, granted) VALUES (%s, %s, 'pilot_data_and_private_report', %s)",
                    (database_user_id, consent_version, granted),
                )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ts.id, ad.slug, av.version, ts.status, ts.created_at, ts.started_at,
                           ts.deadline_at, ts.duration_seconds, ts.result_id, COALESCE(ts.external_user_id, ts.user_id::text),
                           ts.language, ts.age_band, ts.data_origin
                    FROM test_sessions ts
                    JOIN assessment_versions av ON av.id = ts.assessment_version_id
                    JOIN assessment_definitions ad ON ad.id = av.definition_id
                    WHERE ts.id = %s
                    """,
                    (session_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                cursor.execute(
                    """
                    SELECT i.item_id FROM assessment_form_items afi
                    JOIN item_versions iv ON iv.id = afi.item_version_id
                    JOIN items i ON i.id = iv.item_id
                    WHERE afi.session_id = %s ORDER BY afi.presented_order
                    """,
                    (session_id,),
                )
                item_order = [item[0] for item in cursor.fetchall()]
                cursor.execute(
                    """
                    SELECT i.item_id, r.response, r.response_time_ms, r.presented_order
                    FROM responses r
                    JOIN item_versions iv ON iv.id = r.item_version_id
                    JOIN items i ON i.id = iv.item_id
                    WHERE r.session_id = %s
                    """,
                    (session_id,),
                )
                responses = {}
                for item_id, response, response_time_ms, presented_order in cursor.fetchall():
                    payload = response if isinstance(response, dict) else json.loads(response)
                    responses[item_id] = {"item_id": item_id, "answer": payload.get("answer", ""), "response_time_ms": response_time_ms or 10000, "presented_order": presented_order, "data_origin": "REAL_PILOT"}
                cursor.execute("SELECT event_type, metadata, created_at FROM session_events WHERE session_id = %s ORDER BY created_at", (session_id,))
                events = {}
                for event_type, metadata, created_at in cursor.fetchall():
                    details = metadata if isinstance(metadata, dict) else json.loads(metadata or "{}")
                    if event_type == "memory_recall_started" and details.get("item_id"):
                        events[f"recall_started:{details['item_id']}"] = created_at.isoformat()
                    else:
                        events[f"{event_type}:{created_at.isoformat()}"] = details
                return {
                    "id": str(row[0]), "assessment_id": row[1], "assessment_version": row[2], "status": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "started_at": row[5].isoformat() if row[5] else None,
                    "deadline_at": row[6].isoformat() if row[6] else None,
                    "duration_seconds": row[7], "result_id": str(row[8]) if row[8] else None,
                    "responses": responses, "events": events, "item_order": item_order, "user_id": row[9], "language": row[10] or "en", "age_band": row[11] or "unknown", "data_origin": row[12] or "REAL_PILOT",
                }

    def update_session(self, session_id: str, values: Dict[str, Any]) -> None:
        allowed = {"status", "started_at", "result_id"}
        updates = {key: value for key, value in values.items() if key in allowed}
        if not updates:
            return
        assignments = ", ".join(f"{key} = %s" for key in updates)
        parameters = list(updates.values()) + [session_id]
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"UPDATE test_sessions SET {assignments} WHERE id = %s", parameters)

    def insert_response(self, session_id: str, item_id: str, answer: str, response_time_ms: int, presented_order: int, idempotency_key: Optional[str]) -> bool:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO responses (session_id, item_version_id, presented_order, response, is_correct, response_time_ms, idempotency_key)
                    SELECT %s, iv.id, %s, %s::jsonb, (%s = iv.answer_key), %s, %s
                    FROM items i JOIN LATERAL (
                        SELECT id, answer_key FROM item_versions WHERE item_id = i.id ORDER BY version DESC LIMIT 1
                    ) iv ON TRUE
                    WHERE i.item_id = %s
                    ON CONFLICT (idempotency_key) DO NOTHING
                    """,
                    (session_id, presented_order, json.dumps({"answer": answer}), answer, response_time_ms, idempotency_key, item_id),
                )
                return cursor.rowcount > 0

    def insert_event(self, session_id: str, event_id: str, event_type: str, metadata: Dict[str, Any]) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO session_events (id, session_id, event_type, metadata) VALUES (%s, %s, %s, %s::jsonb)",
                    (event_id, session_id, event_type, json.dumps(metadata)),
                )

    def count_events(self, session_id: str, event_type: str) -> int:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM session_events WHERE session_id = %s AND event_type = %s", (session_id, event_type))
                return int(cursor.fetchone()[0])

    def store_result(self, session_id: str, result: Dict[str, Any]) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO assessment_results (id, session_id, composite, iq_score, confidence, disclaimer, question_count, answered_count, domain_metrics, quality, completed_at, score_kind, norm_version, iq_score_kind, iq_score_label, iq_score_version, iq_score_scale, iq_score_method, official_iq_enabled)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id) DO NOTHING
                    """,
                    (result["id"], session_id, result["composite"], result.get("iq_score"), result["confidence"], result["disclaimer"], result["question_count"], result["answered_count"], json.dumps(result["domain_metrics"]), json.dumps(result["quality"]), result["completed_at"], result.get("score_kind", "provisional_domain_signal"), result.get("norm_version"), result.get("iq_score_kind"), result.get("iq_score_label"), result.get("iq_score_version"), result.get("iq_score_scale"), result.get("iq_score_method"), result.get("official_iq_enabled", False)),
                )
                for domain, score in result["domain_scores"].items():
                    cursor.execute(
                        "INSERT INTO domain_scores (session_id, domain, score, score_version) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        (session_id, domain, score, result["score_version"]),
                    )

    def store_result_and_complete_session(self, session_id: str, result: Dict[str, Any]) -> None:
        """Persist the result and close the session in one database transaction."""
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO assessment_results (id, session_id, composite, iq_score, confidence, disclaimer, question_count, answered_count, domain_metrics, quality, completed_at, score_kind, norm_version, iq_score_kind, iq_score_label, iq_score_version, iq_score_scale, iq_score_method, official_iq_enabled)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id) DO NOTHING
                    """,
                    (result["id"], session_id, result["composite"], result.get("iq_score"), result["confidence"], result["disclaimer"], result["question_count"], result["answered_count"], json.dumps(result["domain_metrics"]), json.dumps(result["quality"]), result["completed_at"], result.get("score_kind", "provisional_domain_signal"), result.get("norm_version"), result.get("iq_score_kind"), result.get("iq_score_label"), result.get("iq_score_version"), result.get("iq_score_scale"), result.get("iq_score_method"), result.get("official_iq_enabled", False)),
                )
                for domain, score in result["domain_scores"].items():
                    cursor.execute(
                        "INSERT INTO domain_scores (session_id, domain, score, score_version) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        (session_id, domain, score, result["score_version"]),
                    )
                cursor.execute(
                    "UPDATE test_sessions SET status = 'complete', result_id = %s, completed_at = %s WHERE id = %s",
                    (result["id"], result["completed_at"], session_id),
                )

    def get_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT ar.id, ar.session_id, ar.composite, ar.confidence, ar.disclaimer,
                           ar.question_count, ar.answered_count, ar.domain_metrics, ar.quality,
                           ar.completed_at, COALESCE(ts.external_user_id, ts.user_id::text), ar.access_tier,
                           ar.score_kind, ar.norm_version, ar.iq_score,
                           ar.iq_score_kind, ar.iq_score_label, ar.iq_score_version,
                           ar.iq_score_scale, ar.iq_score_method, ar.official_iq_enabled
                    FROM assessment_results ar
                    JOIN test_sessions ts ON ts.id = ar.session_id
                    WHERE ar.id = %s
                """, (result_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                cursor.execute("SELECT version FROM assessment_versions av JOIN test_sessions ts ON ts.assessment_version_id = av.id WHERE ts.id = %s", (row[1],))
                version = cursor.fetchone()
                cursor.execute("SELECT score_version, domain, score FROM domain_scores WHERE session_id = %s", (row[1],))
                domain_rows = cursor.fetchall()
                metrics = row[7] if isinstance(row[7], dict) else json.loads(row[7])
                quality = row[8] if isinstance(row[8], dict) else json.loads(row[8])
                return {
                    "id": str(row[0]), "session_id": str(row[1]), "user_id": row[10], "assessment_version": version[0] if version else "IAQ-COG-0.4", "score_version": domain_rows[0][0] if domain_rows else "IAQ-PROVISIONAL-ACCURACY-1", "score_kind": row[12] or "provisional_domain_signal", "norm_version": row[13], "iq_score": int(row[14]) if row[14] is not None else None,
                    "iq_score_kind": row[15], "iq_score_label": row[16], "iq_score_version": row[17], "iq_score_scale": row[18], "iq_score_method": row[19], "official_iq_enabled": bool(row[20]),
                    "composite": int(row[2]) if row[2] is not None else None, "domain_scores": {domain: int(score) if score is not None else None for _, domain, score in domain_rows}, "domain_metrics": metrics,
                    "confidence": row[3], "quality": quality, "answered_count": row[6], "question_count": row[5], "duration_seconds": 2100,
                    "completed_at": row[9].isoformat() if row[9] else datetime.now(timezone.utc).isoformat(), "created_at": row[9].isoformat() if row[9] else None, "disclaimer": row[4], "access_tier": row[11] or "summary",
                }

    def store_report_delivery(self, delivery: Dict[str, Any]) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO report_delivery_requests (id, result_id, name, email, consent_version, status, provider, requested_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (result_id, email) DO NOTHING
                    """,
                    (delivery["id"], delivery["result_id"], delivery["name"], delivery["email"], delivery["consent_version"], delivery["status"], delivery["provider"], delivery["requested_at"]),
                )

    def get_report_delivery(self, result_id: str, email: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, result_id, name, email, consent_version, status, provider, requested_at, sent_at FROM report_delivery_requests WHERE result_id = %s AND email = %s",
                    (result_id, email),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return {"id": str(row[0]), "result_id": str(row[1]), "name": row[2], "email": row[3], "consent_version": row[4], "status": row[5], "provider": row[6], "requested_at": row[7].isoformat() if row[7] else None, "sent_at": row[8].isoformat() if row[8] else None}

    def get_ai_output(self, result_id: str, kind: str, input_hash: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, result_id, kind, status, data_origin, provider, model,
                           prompt_version, input_hash, output, fallback_used,
                           provider_request_id, error, created_at
                    FROM ai_result_outputs
                    WHERE result_id = %s AND kind = %s AND input_hash = %s
                    """,
                    (result_id, kind, input_hash),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                output = row[9] if isinstance(row[9], dict) else json.loads(row[9]) if row[9] else {}
                return {
                    "id": str(row[0]), "result_id": str(row[1]), "kind": row[2],
                    "status": row[3], "data_origin": row[4], "provider": row[5],
                    "model": row[6], "prompt_version": row[7], "input_hash": row[8],
                    **output, "fallback_used": row[10], "provider_request_id": row[11],
                    "error": row[12], "created_at": row[13].isoformat() if row[13] else None,
                }

    def store_ai_output(self, output: Dict[str, Any]) -> None:
        nested = {key: value for key, value in output.items() if key not in {"id", "result_id", "user_id", "kind", "status", "data_origin", "provider", "model", "prompt_version", "input_hash", "fallback_used", "provider_request_id", "error", "created_at"}}
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ai_result_outputs
                      (id, result_id, user_id, kind, status, data_origin, provider, model,
                       prompt_version, input_hash, output, fallback_used, provider_request_id,
                       error, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                    ON CONFLICT (result_id, kind, input_hash) DO UPDATE SET
                      status = EXCLUDED.status, output = EXCLUDED.output,
                      fallback_used = EXCLUDED.fallback_used, error = EXCLUDED.error,
                      updated_at = EXCLUDED.updated_at
                    """,
                    (output["id"], output["result_id"], self._db_user_id(str(output.get("user_id", "demo-student"))), output["kind"], output["status"], output["data_origin"], output["provider"], output["model"], output["prompt_version"], output["input_hash"], json.dumps(nested), bool(output.get("fallback_used", False)), output.get("provider_request_id"), output.get("error"), output.get("created_at"), output.get("created_at")),
                )

    def store_feedback(self, feedback: Dict[str, Any]) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO feedback_messages (id, message, page, email, created_at) VALUES (%s, %s, %s, %s, %s)",
                    (feedback["id"], feedback["message"], feedback["page"], feedback["email"], feedback["created_at"]),
                )
