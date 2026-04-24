from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class KafkaMessage:
    """Canonical event message consumed from the razorpay.events Kafka topic."""
    event_id: str
    merchant_id: str
    event_type: str           # subscription.charged | subscription.cancelled | etc.
    sub_id: str
    payment_id: str
    customer_id: str
    plan_id: str
    amount_paise: int         # raw charge amount in paise (Int64)
    currency: str
    payment_method: str
    country: str              # ISO 3166-1 alpha-2, from subscription notes
    source: str               # acquisition channel, from subscription notes
    raw_payload: str          # full original JSON
    received_at: str          # RFC3339 string

    @classmethod
    def from_dict(cls, d: dict) -> "KafkaMessage":
        return cls(
            event_id=d.get("event_id", ""),
            merchant_id=d.get("merchant_id", ""),
            event_type=d.get("event_type", ""),
            sub_id=d.get("sub_id", ""),
            payment_id=d.get("payment_id", ""),
            customer_id=d.get("customer_id", ""),
            plan_id=d.get("plan_id", ""),
            amount_paise=int(d.get("amount_paise", 0)),
            currency=d.get("currency", "INR"),
            payment_method=d.get("payment_method", "unknown"),
            country=d.get("country", ""),
            source=d.get("source", ""),
            raw_payload=d.get("raw_payload", "{}"),
            received_at=d.get("received_at", ""),
        )


@dataclass
class SubscriptionSnapshot:
    """Current state of a subscription, loaded from PostgreSQL subscriptions table."""
    sub_id: str               # razorpay_sub_id
    merchant_id: str
    customer_id: str
    plan_id: str
    status: str               # active | cancelled | paused | completed | halted
    mrr_paise: int            # current normalized monthly amount
    amount_paise: int         # raw plan charge amount
    interval_type: str        # monthly | quarterly | yearly | weekly | daily
    ever_paid: bool
    churned_at: Optional[datetime]
    current_period_end: Optional[datetime]
    exists: bool = True       # False if subscription not yet seen


@dataclass
class MerchantConfig:
    """Per-merchant metric calculation settings from metric_configs table."""
    merchant_id: str
    churn_window_days: int = 30
    include_discounts: bool = False
    include_trials: bool = False
    timezone: str = "Asia/Kolkata"


@dataclass
class MRRMovement:
    """A single MRR movement event to be written to ClickHouse mrr_movements table."""
    merchant_id: str
    period_month: datetime     # first day of the month
    movement_type: str         # new | expansion | contraction | churn | reactivation
    razorpay_sub_id: str
    customer_id: str
    plan_id: str
    amount_paise: int          # MRR after this event
    prev_amount_paise: int     # MRR before this event
    delta_paise: int           # signed: positive = growth, negative = loss
    voluntary: bool = False    # True only for voluntary churn
    country: str = ""          # ISO 3166-1 alpha-2 from subscription notes
    source: str = ""           # acquisition channel from subscription notes
    payment_method: str = ""   # upi_autopay | card | nach | netbanking | unknown
