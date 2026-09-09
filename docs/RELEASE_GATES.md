# IAQ release gates

## Current pilot gate

- `IAQ-PROVISIONAL-ACCURACY-1` reports observed within-profile accuracy only.
- It is not an official IQ score, percentile, diagnosis, or population ranking.
- A live form requires the configured reviewed-item gate in production.
- Every live item must have two independent human approvals for its current version.
- Generated candidates remain available to admin QA, but cannot silently become student items.
- `/ready` fails closed until durable commerce, review, and guardian-consent repositories are wired; local dictionaries are QA-only.

## Age and language gate

- Adults may use the persisted assessment flow when the item-bank and production gates pass.
- Ages 15–17 are routed to an ephemeral practice session until guardian consent is implemented.
- Practice sessions do not consume entitlements, store responses, create results, or trigger email/AI/directions.
- The session language is fixed at creation. The current scored bank is English-only; Indonesian sessions return a clear not-released response until a separate Indonesian bank is reviewed and piloted.
- Production scored sessions require `IAQ_REQUIRE_VERIFIED_AGE=true` and a server-owned adult age band; user-editable Supabase metadata is not an age safeguard.

## Future IAQ IQ estimate gate

An IAQ IQ Estimate may only be enabled after age-stratified Indonesian norming, reliability, test–retest and criterion-validity evidence, subgroup fairness analysis, confidence intervals, standardized administration, and independent psychometric review. Until then, mean-100/SD-15 transformations remain disabled.
