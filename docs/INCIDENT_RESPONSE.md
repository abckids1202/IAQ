# Incident response

For auth, access, or payment incidents: preserve correlation IDs and audit records, disable the affected feature flag, rotate exposed secrets, inspect role/entitlement changes, replay only verified events, notify affected users where required, and document the timeline. Do not include OTPs, access tokens, provider secrets, raw assessment responses, or card data in tickets or logs.
