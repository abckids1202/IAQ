"""Payment-provider boundary for Midtrans sandbox and production."""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict
from urllib.request import Request, urlopen


def provider_name() -> str:
    return "midtrans" if os.getenv("MIDTRANS_SERVER_KEY", "").strip() else "mock"


def midtrans_snap(order: Dict[str, Any], customer: Dict[str, Any]) -> Dict[str, Any]:
    server_key = os.getenv("MIDTRANS_SERVER_KEY", "").strip()
    if not server_key:
        return {"provider": "mock", "checkout_token": f"mock-snap-{order['id']}", "redirect_url": f"/checkout/{order['id']}/pay", "status": "pending"}
    if os.getenv("MIDTRANS_IS_PRODUCTION", "false").lower() == "true" and os.getenv("MIDTRANS_LIVE_ENABLED", "false").lower() != "true":
        raise RuntimeError("Midtrans live mode is disabled until merchant, privacy, refund, and webhook checks are complete")
    credentials = base64.b64encode(f"{server_key}:".encode("utf-8")).decode("ascii")
    payload = {
        "transaction_details": {"order_id": order["order_number"], "gross_amount": order["total_minor"]},
        "customer_details": {"first_name": customer.get("display_name", "IAQ student"), "email": customer.get("email")},
        "enabled_payments": ["gopay", "qris", "dana"],
    }
    base_url = "https://app.midtrans.com" if os.getenv("MIDTRANS_IS_PRODUCTION", "false").lower() == "true" else "https://app.sandbox.midtrans.com"
    request = Request(f"{base_url}/snap/v1/transactions", data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/json", "Accept": "application/json"}, method="POST")
    with urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    return {"provider": "midtrans", "checkout_token": body.get("token"), "redirect_url": body.get("redirect_url"), "status": "pending"}
