# Data dictionary

| Data | Meaning | Origin |
| --- | --- | --- |
| `item_candidates` | Content under development | Reviewed / synthetic candidate |
| `item_versions` | Immutable student-facing content and key | Reviewed content |
| `responses` | Student answer, timing, order, and scoring result | Real pilot or synthetic test |
| `domain_scores` | Versioned provisional domain output | Derived |

## Question-bank fields

| Field | Meaning | Notes |
| --- | --- | --- |
| `item_family_id` | Reusable reasoning format or construct family | Supports future variants without changing scored item versions |
| `difficulty_label` | Intended content difficulty | `medium_hard` is provisional and is not a calibrated difficulty estimate |
| `lifecycle_status` | Content review state | Current seed items are `PILOT` |
| `data_origin` | Content provenance or response provenance | Seed items use `REVIEWED_CONTENT`; responses use `REAL_PILOT` |
| `item_order` | Session-specific randomized item IDs | Stored in the local demo session and hidden from the client session summary |
| `session_quality_flags` | Timing, interruption, fatigue, or technical context | Derived |
| `interest_profiles` | Questionnaire scores and top-three code | Student response |
| `major_matches` | Fit, readiness, feasibility, confidence | Derived |
| `audit_logs` | Sensitive access and change history | System |

Identity should remain separate from research export data. Use UUIDs, explicit timestamps, foreign keys, indexes, and soft deletion where audit history is required.
