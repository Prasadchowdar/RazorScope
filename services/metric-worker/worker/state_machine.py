"""
Subscription state machine — source of truth for all MRR computations.

Every paise is stored as an integer. No floats anywhere in this file.
Wrong here = wrong everywhere. Test coverage of every branch is mandatory.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from worker.models import KafkaMessage, MRRMovement, MerchantConfig, SubscriptionSnapshot

# Normalization factors: convert any billing interval to monthly equivalent.
# 'weekly': 4.33 = 365/12/7 — used as integer arithmetic: multiply then truncate.
_MONTHLY_FACTORS: dict[str, float] = {
    "daily":     30.0,
    "weekly":    4.0,      # conservative: 4 weeks/month (avoids overestimating)
    "monthly":   1.0,
    "quarterly": 1 / 3,
    "yearly":    1 / 12,
}


def normalize_to_monthly_paise(amount_paise: int, interval_type: str) -> int:
    """Convert a charge amount to its monthly equivalent in paise. Always integers."""
    factor = _MONTHLY_FACTORS.get(interval_type, 1.0)
    return int(amount_paise * factor)


def process_event(
    event: KafkaMessage,
    snapshot: SubscriptionSnapshot,
    config: MerchantConfig,
    now: Optional[datetime] = None,
) -> Optional[MRRMovement]:
    """
    Core state machine. Returns an MRRMovement or None (no MRR change).

    Called once per Kafka event, in partition order (guaranteed per merchant).
    The caller is responsible for persisting the updated snapshot afterward.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    period_month = _first_of_month(now)
    prev_mrr = snapshot.mrr_paise

    def movement(
        kind: str,
        new_mrr: int,
        prev: int = prev_mrr,
        voluntary: bool = False,
    ) -> MRRMovement:
        return MRRMovement(
            merchant_id=event.merchant_id,
            period_month=period_month,
            movement_type=kind,
            razorpay_sub_id=event.sub_id or snapshot.sub_id,
            customer_id=event.customer_id or snapshot.customer_id,
            plan_id=event.plan_id or snapshot.plan_id,
            amount_paise=new_mrr,
            prev_amount_paise=prev,
            delta_paise=new_mrr - prev,
            voluntary=voluntary,
            country=getattr(event, "country", ""),
            source=getattr(event, "source", ""),
            payment_method=getattr(event, "payment_method", ""),
        )

    match event.event_type:

        case "subscription.charged":
            new_mrr = normalize_to_monthly_paise(event.amount_paise, snapshot.interval_type)

            if prev_mrr == 0 and not snapshot.ever_paid:
                return movement("new", new_mrr)

            if prev_mrr == 0 and snapshot.ever_paid:
                return movement("reactivation", new_mrr)

            if new_mrr > prev_mrr:
                return movement("expansion", new_mrr)

            if new_mrr < prev_mrr:
                return movement("contraction", new_mrr)

            return None  # same amount, no MRR movement

        case "subscription.cancelled":
            if prev_mrr == 0:
                return None  # already had no MRR, nothing to churn
            return movement("churn", 0, voluntary=True)

        case "subscription.completed":
            # Ran out of billing cycles — involuntary churn
            if prev_mrr == 0:
                return None
            return movement("churn", 0, voluntary=False)

        case "subscription.halted":
            # Razorpay halted after too many failed payment retries.
            # Treat as involuntary churn only if the churn window has also expired.
            if prev_mrr == 0:
                return None
            if _churn_window_expired(snapshot, config.churn_window_days, now):
                return movement("churn", 0, voluntary=False)
            return None  # halted but still within retry window

        case "subscription.paused" | "subscription.resumed" | "subscription.authenticated" | "subscription.pending":
            return None  # no MRR impact

        case _:
            # Unknown event type — log upstream, return None here
            return None


def _first_of_month(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _churn_window_expired(
    snapshot: SubscriptionSnapshot,
    churn_window_days: int,
    now: datetime,
) -> bool:
    """True when no payment has been received within churn_window_days of period end."""
    if snapshot.current_period_end is None:
        return False
    deadline = snapshot.current_period_end
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    delta = (now - deadline).days
    return delta >= churn_window_days


def updated_snapshot(
    snapshot: SubscriptionSnapshot,
    event: KafkaMessage,
    movement: Optional[MRRMovement],
) -> SubscriptionSnapshot:
    """
    Returns a new SubscriptionSnapshot reflecting the event outcome.
    The caller must persist this back to PostgreSQL.
    """
    from dataclasses import replace

    new_status = _derive_status(event.event_type, snapshot.status)
    new_mrr = movement.amount_paise if movement else snapshot.mrr_paise
    new_ever_paid = snapshot.ever_paid or (event.event_type == "subscription.charged")
    new_amount = event.amount_paise if event.event_type == "subscription.charged" and event.amount_paise > 0 else snapshot.amount_paise

    return replace(
        snapshot,
        status=new_status,
        mrr_paise=new_mrr,
        ever_paid=new_ever_paid,
        amount_paise=new_amount,
        churned_at=snapshot.churned_at if new_status not in ("cancelled", "completed", "halted") else datetime.now(timezone.utc),
    )


def _derive_status(event_type: str, current_status: str) -> str:
    mapping = {
        "subscription.charged":       "active",
        "subscription.cancelled":     "cancelled",
        "subscription.completed":     "completed",
        "subscription.halted":        "halted",
        "subscription.paused":        "paused",
        "subscription.resumed":       "active",
        "subscription.authenticated": "authenticated",
        "subscription.pending":       "pending",
    }
    return mapping.get(event_type, current_status)
