# Assessment model

The cognitive baseline covers abstract reasoning, deductive logic, numerical reasoning, verbal reasoning, visual-spatial reasoning, working memory, and processing speed. The demo includes reviewed baseline examples across each domain, with memory and speed represented as distinct task types.

Each assessment version has an immutable item version, scoring model version, and (in future) a norm version. An item version cannot be edited after scored responses exist; a new version is created instead.

Content lifecycle: `DRAFT → AI_GENERATED → AUTOMATICALLY_VERIFIED → HUMAN_REVIEWED → PILOT → CALIBRATED → ACTIVE → RETIRED`.

Synthetic data is labelled `SYNTHETIC`. Pilot responses are labelled `REAL_PILOT`. These datasets are never silently mixed.
