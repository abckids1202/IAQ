# Scoring V1

The demo scoring function is intentionally interpretable and provisional:

```text
domain signal = correct / answered × 100
composite = mean(domain scores with at least four scored items)
```

Domains with fewer than four scored items remain `null`/“Not assessed”; they are never filled with a flattering baseline. A composite is withheld until at least two domains have enough evidence. Rapid responses, interruption events, fatigue patterns, and accessibility adjustments become session-quality context. They do not become hidden intelligence penalties. Complete sessions are limited to 35 minutes, but the timer is not converted into a hidden score penalty.

The service returns `score_version=IAQ-PROVISIONAL-ACCURACY-1` and `score_kind=provisional_domain_signal`. It reports observed accuracy directly; it does not create population percentiles, a bell curve, diagnostic labels, or clinical interpretations. A future mean-100/SD-15 IAQ IQ estimate requires age-specific norms, reliability, fairness, validity, confidence intervals, and independent psychometric review before release.
