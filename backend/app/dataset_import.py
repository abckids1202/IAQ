"""Import the quarantined assessment catalog into PostgreSQL.

This is deliberately a separate command from the student-bank seed. Imported
research candidates are stored in ``dataset_candidates`` as DRAFT records and
never become session-eligible as a side effect of import.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Optional

from . import external_data


def _dsn(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _candidate_payload(item: Dict[str, Any]) -> tuple[Any, ...]:
    stimulus = {
        key: item.get(key)
        for key in ("stimulus", "protocol", "image_path", "asset_path")
        if item.get(key) is not None
    }
    rendering = {
        "render_type": item.get("render_type", item.get("type", "choice")),
        "render_parameters": item.get("render_parameters") or {},
        "asset_exists": bool(item.get("asset_exists")),
    }
    provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {"description": item.get("provenance", "")}
    answer_key = {key: item.get(key) for key in ("answer", "answer_index") if item.get(key) is not None}
    return (
        item["id"], item["source_dataset"], item["source_file"], item["source_id"],
        item["domain"], item["construct_id"], item["item_family_id"], item.get("content_version", 1),
        item["type"], item["prompt"], json.dumps(item.get("options") or []), json.dumps(answer_key),
        json.dumps(stimulus) if stimulus else None, json.dumps(rendering), json.dumps(provenance),
        provenance.get("source_license"), item.get("difficulty_estimate"), item.get("language", "en"),
    )


def import_candidates(database_url: str, *, items: Optional[Iterable[Dict[str, Any]]] = None) -> Dict[str, int]:
    """Insert staged candidates without overwriting an existing version.

    A source correction must be represented as a new ``content_version``. The
    command therefore uses ``ON CONFLICT DO NOTHING`` and reports existing
    records instead of silently mutating reviewed content.
    """
    import psycopg

    rows = items if items is not None else external_data.iter_external_items(include_verbal=True, language="en")
    inserted = 0
    existing = 0
    with psycopg.connect(_dsn(database_url)) as connection:
        with connection.cursor() as cursor:
            for item in rows:
                cursor.execute(
                    """
                    INSERT INTO dataset_candidates
                      (external_id, source_dataset, source_file, source_id, domain,
                       construct_id, item_family_id, content_version, item_type,
                       prompt, options, answer_key, stimulus, rendering, provenance,
                       license_evidence, actual_difficulty, language,
                       lifecycle_status, review_status, calibrated,
                       commercial_use_approved, production_eligible)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                            %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s,
                            %s, 'DRAFT', 'unreviewed', false, false, false)
                    ON CONFLICT (external_id) DO NOTHING
                    """,
                    _candidate_payload(item),
                )
                if cursor.rowcount:
                    inserted += 1
                else:
                    existing += 1
        connection.commit()
    return {"inserted": inserted, "already_present": existing, "total_seen": inserted + existing}


if __name__ == "__main__":
    database_url = os.getenv("IAQ_DATABASE_URL")
    if not database_url:
        raise SystemExit("IAQ_DATABASE_URL is required to import the staged catalog")
    print(json.dumps(import_candidates(database_url), indent=2))
