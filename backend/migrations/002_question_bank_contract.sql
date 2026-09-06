-- IAQ question-bank contract
--
-- The local pilot seed is defined in app/question_bank.py so it can be checked
-- in source control, tested independently, and loaded without requiring a
-- PostgreSQL connection. Production deployment should import those reviewed
-- records into items/item_versions through an idempotent seed job.

CREATE INDEX IF NOT EXISTS items_domain_lifecycle_idx
    ON items (domain, lifecycle_status);

CREATE INDEX IF NOT EXISTS item_versions_item_created_idx
    ON item_versions (item_id, created_at);

COMMENT ON TABLE items IS
    'IAQ item bank. The pilot baseline currently contains 840 pilot-ready items, 120 per cognitive domain.';
