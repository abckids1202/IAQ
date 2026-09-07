"""Provider-neutral report email adapter.

Development keeps a durable-looking queue record without network calls. A
Resend API key enables the same contract in staging/production.
"""
from __future__ import annotations

import json
import os
from html import escape
from typing import Any, Dict
from urllib.request import Request, urlopen


def configured() -> bool:
    return bool(os.getenv("RESEND_API_KEY", "").strip())


def send_report(delivery: Dict[str, Any], report_url: str) -> Dict[str, Any]:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        return {"status": "QUEUED_DEV", "provider": "development_log", "provider_message_id": None, "message": "Delivery recorded in development mode; no real email was sent."}
    payload = {
        "from": os.getenv("EMAIL_FROM_ADDRESS", "reports@example.invalid"),
        "to": [delivery["email"]],
        "subject": "Your IAQ Cognitive Profile report",
        "html": f"<p>Hi {escape(str(delivery['name']))},</p><p>Your private IAQ report is ready.</p><p><a href=\"{escape(report_url, quote=True)}\">Open your report</a></p><p>This is an experimental educational profile, not an official IQ score.</p>",
    }
    request = Request("https://api.resend.com/emails", data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8"))
        return {"status": "SENT", "provider": "resend", "provider_message_id": body.get("id"), "message": "Report email sent."}
    except Exception as error:
        return {"status": "FAILED_RETRYABLE", "provider": "resend", "provider_message_id": None, "error": str(error)[:500], "message": "The report could not be delivered yet. Please retry."}
