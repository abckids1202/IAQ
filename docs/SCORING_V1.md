# Scoring V1

The demo scoring function is intentionally interpretable and provisional:

```text
domain signal = correct / answered × 100
composite = mean(domain scores with at least four scored items)
```

Domains with fewer than four scored items remain `null`/“Not assessed”; they are never filled with a flattering baseline. A composite is withheld until at least two domains have enough evidence. Rapid responses, interruption events, fatigue patterns, and accessibility adjustments become session-quality context. They do not become hidden intelligence penalties. Complete sessions are limited to 35 minutes, but the timer is not converted into a hidden score penalty.

The service returns `score_version=IAQ-PROVISIONAL-ACCURACY-1` and `score_kind=provisional_domain_signal`. It reports observed accuracy directly; it does not create population percentiles, a bell curve, diagnostic labels, or clinical interpretations. A future mean-100/SD-15 IAQ IQ estimate requires age-specific norms, reliability, fairness, validity, confidence intervals, and independent psychometric review before release.

## Experimental IQ-style display score

The app also returns `iq_score` for a complete seven-domain form. It is shown to
students as **IAQ IQ score · experimental** on a familiar 100/15 display
convention. This is a transparent reference transform, not a normed IQ result:

```text
iq_score = round(70 + (seven_domain_mean × 0.60))
```

The number is withheld when any domain has fewer than four scored items. It does
not use age norms, population data, IRT parameters, percentiles, or a licensed
test conversion table. Its version is `IAQ-IQ-EXPERIMENTAL-1`, and
`official_iq_enabled` remains `false`. Do not use this value for clinical,
educational-placement, employment, diagnosis, or eligibility decisions.

This display track exists only so the private pilot can test the product flow
with a clearly identified number. It must be replaced by an independently
reviewed, age-normed scoring and reporting pipeline before IAQ can make an
official IQ claim.
