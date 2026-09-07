# Scoring V1

The demo scoring function is intentionally interpretable and provisional:

```text
domain score = 50 + (correct / answered × 45)
composite = mean(domain scores with at least four scored items)
```

Domains with fewer than four scored items remain `null`/“Not assessed”; they are never filled with a flattering baseline. A composite is withheld until at least two domains have enough evidence. Rapid responses, interruption events, fatigue patterns, and accessibility adjustments become session-quality context. They do not become hidden intelligence penalties. Complete sessions are limited to 35 minutes, but the timer is not converted into a hidden score penalty.

The service returns `score_version=SCORING-V1`. It does not create population percentiles, a bell curve, diagnostic labels, or clinical interpretations. Future pilot analysis should estimate classical item statistics, reliability, fairness, and eventually IRT parameters before adaptive or normed reporting.
