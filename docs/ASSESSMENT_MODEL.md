# Assessment model

The cognitive baseline covers abstract reasoning, deductive logic, numerical reasoning, verbal reasoning, visual-spatial reasoning, working memory, and processing speed. The pilot bank contains 280 original pilot items: 40 reviewable candidates per domain, with memory and speed represented as distinct task types and deterministic factory variants recorded with provenance.

The default complete form selects 8 items from each domain (56 questions total) without replacement, avoids duplicate item families where the bank permits it, then shuffles the combined order with a secure random source. The complete session has a 35-minute server-enforced deadline. A new session receives a new form; item IDs, answer keys, and explanations remain server-side.

The `medium_hard` label is a content target, not an established psychometric result. Difficulty, discrimination, fairness, reliability, and norms require real pilot responses and review.

Each assessment version has an immutable item version, scoring model version, and (in future) a norm version. An item version cannot be edited after scored responses exist; a new version is created instead.

Content lifecycle: `DRAFT → AI_GENERATED → AUTOMATICALLY_VERIFIED → HUMAN_REVIEWED → PILOT → CALIBRATED → ACTIVE → RETIRED`.

Synthetic data is labelled `SYNTHETIC`. Pilot responses are labelled `REAL_PILOT`. These datasets are never silently mixed.
