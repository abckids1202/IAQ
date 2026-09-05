# Data dictionary

| Data | Meaning | Origin |
| --- | --- | --- |
| `item_candidates` | Content under development | Reviewed / synthetic candidate |
| `item_versions` | Immutable student-facing content and key | Reviewed content |
| `responses` | Student answer, timing, order, and scoring result | Real pilot or synthetic test |
| `domain_scores` | Versioned provisional domain output | Derived |
| `session_quality_flags` | Timing, interruption, fatigue, or technical context | Derived |
| `interest_profiles` | Questionnaire scores and top-three code | Student response |
| `major_matches` | Fit, readiness, feasibility, confidence | Derived |
| `audit_logs` | Sensitive access and change history | System |

Identity should remain separate from research export data. Use UUIDs, explicit timestamps, foreign keys, indexes, and soft deletion where audit history is required.
