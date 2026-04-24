"""
Razorpay data source for backfill.

DevRazorpayClient  — synthetic deterministic events (no real API key needed).
LiveRazorpayClient — real Razorpay API (requires RAZORPAY_KEY_ID + RAZORPAY_KEY_SECRET).

Both return lists of dicts with the same fields as KafkaMessage.
"""
from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Iterator


_PLAN_AMOUNTS = [99900, 199900, 299900, 499900]  # paise
_PAGE_SIZE = 10


class RazorpayClient(ABC):
    @abstractmethod
    def fetch_page(
        self,
        merchant_id: str,
        from_date: date,
        to_date: date,
        cursor: str | None,
    ) -> tuple[list[dict], str | None]:
        """
        Return (events_for_page, next_cursor).
        next_cursor is None when there are no more pages.
        Each event dict has the same keys as KafkaMessage.
        """


class DevRazorpayClient(RazorpayClient):
    """Generates deterministic synthetic subscription events for a date range.

    Produces one 'subscription.charged' event per subscription per month in the range.
    Subscription IDs are deterministic so re-running the same job is idempotent.
    """

    def _month_range(self, from_date: date, to_date: date) -> list[date]:
        months = []
        cur = from_date.replace(day=1)
        end = to_date.replace(day=1)
        while cur <= end:
            months.append(cur)
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)
        return months

    def _all_events(self, merchant_id: str, from_date: date, to_date: date) -> list[dict]:
        months = self._month_range(from_date, to_date)
        events = []
        # Generate 5 synthetic subscriptions per merchant
        for i in range(5):
            sub_seed = f"{merchant_id}:sub:{i}"
            sub_id = "sub_bf_" + hashlib.sha256(sub_seed.encode()).hexdigest()[:12]
            amount = _PLAN_AMOUNTS[i % len(_PLAN_AMOUNTS)]
            plan_id = f"plan_bf_{i % 3}"
            cust_id = f"cust_bf_{hashlib.sha256((sub_seed + ':cust').encode()).hexdigest()[:8]}"

            for month in months:
                event_seed = f"{sub_id}:{month.isoformat()}"
                event_id = "evt_bf_" + hashlib.sha256(event_seed.encode()).hexdigest()[:12]
                events.append({
                    "event_id": event_id,
                    "merchant_id": merchant_id,
                    "event_type": "subscription.charged",
                    "sub_id": sub_id,
                    "payment_id": "pay_bf_" + hashlib.sha256((event_seed + ":pay").encode()).hexdigest()[:12],
                    "customer_id": cust_id,
                    "plan_id": plan_id,
                    "amount_paise": amount,
                    "currency": "INR",
                    "payment_method": "upi",
                    "raw_payload": "{}",
                    "received_at": month.isoformat() + "T00:00:00Z",
                })
        return events

    def fetch_page(
        self,
        merchant_id: str,
        from_date: date,
        to_date: date,
        cursor: str | None,
    ) -> tuple[list[dict], str | None]:
        all_events = self._all_events(merchant_id, from_date, to_date)
        offset = int(cursor) if cursor else 0
        page = all_events[offset: offset + _PAGE_SIZE]
        next_cursor = str(offset + _PAGE_SIZE) if offset + _PAGE_SIZE < len(all_events) else None
        return page, next_cursor


class LiveRazorpayClient(RazorpayClient):
    """Calls the real Razorpay API to fetch historical subscription payments."""

    def __init__(self, key_id: str, key_secret: str) -> None:
        import razorpay  # type: ignore[import]
        self._client = razorpay.Client(auth=(key_id, key_secret))

    def fetch_page(
        self,
        merchant_id: str,
        from_date: date,
        to_date: date,
        cursor: str | None,
    ) -> tuple[list[dict], str | None]:
        from_ts = int(date.fromisoformat(from_date.isoformat()).strftime("%s") if hasattr(from_date, "isoformat") else from_date)
        to_ts = int(date.fromisoformat(to_date.isoformat()).strftime("%s") if hasattr(to_date, "isoformat") else to_date)

        params: dict = {"from": from_ts, "to": to_ts, "count": _PAGE_SIZE}
        if cursor:
            params["skip"] = int(cursor)

        subs = self._client.subscription.all(params).get("items", [])
        events: list[dict] = []
        for sub in subs:
            payments = self._client.payment.all(
                {"subscription_id": sub["id"], "count": 100}
            ).get("items", [])
            for pay in payments:
                if pay.get("status") != "captured":
                    continue
                events.append({
                    "event_id": f"bf_{pay['id']}",
                    "merchant_id": merchant_id,
                    "event_type": "subscription.charged",
                    "sub_id": sub["id"],
                    "payment_id": pay["id"],
                    "customer_id": sub.get("customer_id", ""),
                    "plan_id": sub.get("plan_id", ""),
                    "amount_paise": int(pay.get("amount", 0)),
                    "currency": pay.get("currency", "INR"),
                    "payment_method": pay.get("method", "unknown"),
                    "raw_payload": "{}",
                    "received_at": str(pay.get("created_at", "")),
                })

        skip = int(cursor or 0)
        next_cursor = str(skip + _PAGE_SIZE) if len(subs) == _PAGE_SIZE else None
        return events, next_cursor


def get_client(key_id: str | None = None, key_secret: str | None = None) -> RazorpayClient:
    """Return the correct client based on merchant credentials or env fallback."""
    if key_id and key_secret:
        return LiveRazorpayClient(key_id, key_secret)

    env_key_id = os.getenv("RAZORPAY_KEY_ID", "")
    env_key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    if env_key_id and env_key_secret and not env_key_id.startswith("rzp_test_dev"):
        return LiveRazorpayClient(env_key_id, env_key_secret)
    return DevRazorpayClient()
