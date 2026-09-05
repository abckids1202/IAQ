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
from .question_bank import bank_counts


def seed() -> None:
    print(f"seeded {len(ITEMS)} reviewed baseline items")
    print(f"items_per_domain={bank_counts()}")
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
            for item in ITEMS.values():
                cursor.execute(
                    """
                    INSERT INTO item_families (family_id, domain, rules, lifecycle_status)
                    VALUES (%s, %s, %s::jsonb, 'PILOT')
                    ON CONFLICT (family_id) DO UPDATE SET domain = EXCLUDED.domain
                    """,
                    (item["item_family_id"], item["domain"], json.dumps({"format": item["item_family_id"]})),
                )
                cursor.execute(
                    """
                    INSERT INTO items (item_id, item_family_id, domain, lifecycle_status, data_origin)
                    SELECT %s, id, %s, 'PILOT', 'REVIEWED_CONTENT'
                    FROM item_families WHERE family_id = %s
                    ON CONFLICT (item_id) DO UPDATE SET
                        item_family_id = EXCLUDED.item_family_id,
                        domain = EXCLUDED.domain,
                        lifecycle_status = EXCLUDED.lifecycle_status,
                        data_origin = EXCLUDED.data_origin
                    """,
                    (item["id"], item["domain"], item["item_family_id"]),
                )
                cursor.execute(
                    """
                    INSERT INTO item_versions (item_id, version, prompt, answer_key, options)
                    SELECT id, %s, %s, %s, %s::jsonb
                    FROM items WHERE item_id = %s
                    ON CONFLICT (item_id, version) DO NOTHING
                    """,
                    (item["content_version"], item["prompt"], item["answer"], json.dumps(item["options"]), item["id"]),
                )
        connection.commit()
    return len(ITEMS)


if __name__ == "__main__":
    database_url = os.getenv("IAQ_DATABASE_URL")
    if database_url:
        print(f"loaded {seed_database(database_url)} reviewed baseline items into PostgreSQL")
    else:
        seed()
