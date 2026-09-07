"""Idempotent seed entry point for the reviewed question bank.

Without ``IAQ_DATABASE_URL`` this prints a safe local seed summary. When the
variable is set, it loads the same reviewed content into PostgreSQL after the
migrations have been applied. Answer keys are written only to item_versions,
which is a server-side table and is never returned by the public API.
"""
from __future__ import annotations

import json
import os

from .main import ITEMS, MAJORS
from .question_bank import bank_counts, reviewed_counts, review_gate_ready


def seed() -> None:
    print(f"seeded {len(ITEMS)} question candidates")
    print(f"items_per_domain={bank_counts()}")
    print(f"reviewed_per_domain={reviewed_counts()}")
    print(f"review_gate_ready={review_gate_ready()}")
    print(f"seeded {len(MAJORS)} major profiles")
    print("data_origin=SYNTHETIC is reserved for simulator output; no synthetic norming data is created")


def seed_database(database_url: str) -> int:
    """Insert the reviewed bank into the PostgreSQL persistence contract.

    Item versions use ``ON CONFLICT DO NOTHING`` so scored content is not
    silently edited. A future content change must receive a new version.
    """
    import psycopg

    dsn = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            generation_runs = {item.get("generation_run_id") for item in ITEMS.values() if item.get("generation_run_id")}
            for run_id in generation_runs:
                generated = [item for item in ITEMS.values() if item.get("generation_run_id") == run_id]
                cursor.execute(
                    """
                    INSERT INTO item_generation_runs (run_id, factory, seed, parameters, item_count, status)
                    VALUES (%s, 'deterministic_item_factory', %s, %s::jsonb, %s, 'COMPLETED')
                    ON CONFLICT (run_id) DO UPDATE SET item_count = EXCLUDED.item_count
                    """,
                    (run_id, run_id, json.dumps({"language": "en", "target": "medium_hard"}), len(generated)),
                )
            for item in ITEMS.values():
                cursor.execute(
                    """
                    INSERT INTO item_families (family_id, domain, rules, lifecycle_status)
                    VALUES (%s, %s, %s::jsonb, %s)
                    ON CONFLICT (family_id) DO UPDATE SET domain = EXCLUDED.domain
                    """,
                    (item["item_family_id"], item["domain"], json.dumps({"format": item["item_family_id"]}), item.get("lifecycle_status", item.get("status", "DRAFT"))),
                )
                cursor.execute(
                    """
                    INSERT INTO items (item_id, item_family_id, domain, lifecycle_status, data_origin, construct_id, language, generation_run_id, provenance)
                    SELECT %s, id, %s, %s, %s, %s, 'en', %s, %s
                    FROM item_families WHERE family_id = %s
                    ON CONFLICT (item_id) DO UPDATE SET
                        item_family_id = EXCLUDED.item_family_id,
                        domain = EXCLUDED.domain,
                        lifecycle_status = EXCLUDED.lifecycle_status,
                        data_origin = EXCLUDED.data_origin,
                        construct_id = EXCLUDED.construct_id,
                        language = EXCLUDED.language,
                        generation_run_id = EXCLUDED.generation_run_id,
                        provenance = EXCLUDED.provenance
                    """,
                    (item["id"], item["domain"], item.get("lifecycle_status", item.get("status", "DRAFT")), item.get("data_origin", "REVIEWED_CONTENT"), item["domain"], item.get("generation_run_id"), item.get("provenance", "IAQ item provenance pending review"), item["item_family_id"]),
                )
                cursor.execute(
                    """
                    INSERT INTO item_versions (item_id, version, prompt, answer_key, options, difficulty_target, difficulty_estimate, render_type, generation_parameters, actual_difficulty, reading_level, independent_answer, license_evidence)
                    SELECT id, %s, %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, %s, %s, %s, %s
                    FROM items WHERE item_id = %s
                    ON CONFLICT (item_id, version) DO NOTHING
                    """,
                    (item["content_version"], item["prompt"], item["answer"], json.dumps(item["options"]), item.get("difficulty_label", "medium_hard"), item.get("difficulty_estimate"), item.get("render_type", item.get("type", "choice")), json.dumps(item.get("render_parameters") or item.get("generation_parameters") or {}), item.get("difficulty_estimate"), None, item["answer"], item.get("license_evidence"), item["id"]),
                )
        connection.commit()
    return len(ITEMS)


if __name__ == "__main__":
    database_url = os.getenv("IAQ_DATABASE_URL")
    if database_url:
        print(f"loaded {seed_database(database_url)} question candidates into PostgreSQL")
    else:
        seed()
