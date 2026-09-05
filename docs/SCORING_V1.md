# Scoring V1

The demo scoring function is intentionally interpretable and provisional:

```text
domain score = 50 + (correct / answered × 45)
composite = mean(all seven domain scores)
```

Unanswered domains remain visible at a conservative baseline and reduce confidence. Rapid responses, interruption events, fatigue patterns, and accessibility adjustments become session-quality context. They do not become hidden intelligence penalties.

The service returns `score_version=SCORING-V1`. It does not create population percentiles, a bell curve, diagnostic labels, or clinical interpretations. Future pilot analysis should estimate classical item statistics, reliability, fairness, and eventually IRT parameters before adaptive or normed reporting.
