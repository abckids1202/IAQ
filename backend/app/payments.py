"""Legacy payment adapter kept only for migration compatibility.

IAQ's active payment flow is manual BCA QRIS proof review. This module must
not be used to grant entitlements.
"""
from __future__ import annotations

from typing import Any, Dict


def provider_name() -> str:
    return "manual_qris"


def midtrans_snap(order: Dict[str, Any], customer: Dict[str, Any]) -> Dict[str, Any]:
    raise RuntimeError("Midtrans checkout is disabled; use the manual QRIS payment flow")
