"""Small PostgreSQL adapter for the assessment and results boundary.

The API keeps its dependency-light in-memory mode for local UI previews. When
IAQ_DATABASE_URL is configured, this adapter makes sessions, responses, and
results durable without exposing answer keys to the client.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import psycopg


DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"


class PostgresAssessmentStore:
    def __init__(self, database_url: str):
        self.dsn = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def _connection(self):
        return psycopg.connect(self.dsn)

    def _ensure_reference_data(self, cursor, assessment_version: str) -> str:
        cursor.execute(
            """
            INSERT INTO users (id, email, role)
            VALUES (%s, 'demo-student@iaq.local', 'student')
            ON CONFLICT (id) DO NOTHING
            """,
            (DEMO_USER_ID,),
        )
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

    def create_session(self, session: Dict[str, Any]) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                assessment_version_id = self._ensure_reference_data(cursor, session["assessment_version"])
                cursor.execute(
                    """
                    INSERT INTO test_sessions (id, user_id, assessment_version_id, status, data_origin, started_at, deadline_at, duration_seconds)
                    VALUES (%s, %s, %s, %s, 'REAL_PILOT', NULL, %s, %s)
                    """,
                    (session["id"], DEMO_USER_ID, assessment_version_id, session["status"], session["deadline_at"], session["duration_seconds"]),
                )
                for position, item_id in enumerate(session["item_order"]):
                    cursor.execute(
                        """
                        INSERT INTO assessment_form_items (session_id, item_version_id, domain, presented_order)
                        SELECT %s, iv.id, i.domain, %s
                        FROM items i JOIN item_versions iv ON iv.item_id = i.id AND iv.version = 1
                        WHERE i.item_id = %s
                        ON CONFLICT (session_id, presented_order) DO NOTHING
                        """,
                        (session["id"], position, item_id),
                    )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ts.id, ad.slug, av.version, ts.status, ts.created_at, ts.started_at,
                           ts.deadline_at, ts.duration_seconds, ts.result_id
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
                return {
                    "id": str(row[0]), "assessment_id": row[1], "assessment_version": row[2], "status": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "started_at": row[5].isoformat() if row[5] else None,
                    "deadline_at": row[6].isoformat() if row[6] else None,
                    "duration_seconds": row[7], "result_id": str(row[8]) if row[8] else None,
                    "responses": responses, "item_order": item_order, "user_id": "demo-student",
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
                    FROM items i JOIN item_versions iv ON iv.item_id = i.id AND iv.version = 1
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

    def store_result(self, session_id: str, result: Dict[str, Any]) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO assessment_results (id, session_id, composite, confidence, disclaimer, question_count, answered_count, domain_metrics, quality, completed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                    ON CONFLICT (session_id) DO NOTHING
                    """,
                    (result["id"], session_id, result["composite"], result["confidence"], result["disclaimer"], result["question_count"], result["answered_count"], json.dumps(result["domain_metrics"]), json.dumps(result["quality"]), result["completed_at"]),
                )
                for domain, score in result["domain_scores"].items():
                    cursor.execute(
                        "INSERT INTO domain_scores (session_id, domain, score, score_version) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        (session_id, domain, score, result["score_version"]),
                    )

    def get_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, session_id, composite, confidence, disclaimer, question_count, answered_count, domain_metrics, quality, completed_at FROM assessment_results WHERE id = %s", (result_id,))
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
                    "id": str(row[0]), "session_id": str(row[1]), "assessment_version": version[0] if version else "IAQ-COG-0.3", "score_version": domain_rows[0][0] if domain_rows else "SCORING-V1",
                    "composite": int(row[2]), "domain_scores": {domain: int(score) for _, domain, score in domain_rows}, "domain_metrics": metrics,
                    "confidence": row[3], "quality": quality, "answered_count": row[6], "question_count": row[5], "duration_seconds": 2100,
                    "completed_at": row[9].isoformat() if row[9] else datetime.now(timezone.utc).isoformat(), "created_at": row[9].isoformat() if row[9] else None, "disclaimer": row[4],
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
