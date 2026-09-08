# IAQ staged assessment data

This directory is a local/server-side research staging area populated from the
user-provided IAQ five-domain package and research data kit.

- `five_domains/banks/` contains 2,000 records each for logical, numerical,
  abstract, spatial, and memory reasoning.
- `five_domains/assets/` contains the matching visual assets referenced by the
  bank `image_path` fields.
- `verbal/jsonl/` contains the supplied LogiQA English and Chinese research
  splits. The IAQ loader currently previews English records only.

These records are not part of the live student question bank. They are loaded
only through protected admin dataset endpoints, and every record is forced to
`DRAFT`, `unreviewed`, `calibrated=false`, and `production_eligible=false`.
Answer keys and rules must never be returned by student session endpoints.

The large banks and image assets are ignored by Git intentionally. Keep them in
private storage or a private repository for deployment, and verify item-level
licenses before any commercial or scored use.
