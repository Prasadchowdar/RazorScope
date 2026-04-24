"""
Unit tests for the subscription state machine.

Every branch of process_event() must be covered.
Tests are pure — no database, no Kafka, no ClickHouse.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from worker.models import KafkaMessage, MerchantConfig, SubscriptionSnapshot
from worker.state_machine import (
    normalize_to_monthly_paise,
    process_event,
    updated_snapshot,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "webhook_payloads.json"
_RAW = json.loads(FIXTURES_PATH.read_text())


def _event(key: str) -> KafkaMessage:
    return KafkaMessage.from_dict(_RAW[key])


def _snapshot(
    sub_id: str = "sub_monthly001",
    mrr_paise: int = 0,
    ever_paid: bool = False,
    status: str = "active",
    interval_type: str = "monthly",
    amount_paise: int = 299900,
    churned_at=None,
    current_period_end=None,
) -> SubscriptionSnapshot:
    return SubscriptionSnapshot(
        sub_id=sub_id,
        merchant_id="11111111-1111-1111-1111-111111111111",
        customer_id="cust_001",
        plan_id="plan_growth_monthly",
        status=status,
        mrr_paise=mrr_paise,
        amount_paise=amount_paise,
        interval_type=interval_type,
        ever_paid=ever_paid,
        churned_at=churned_at,
        current_period_end=current_period_end,
    )


def _config(churn_window_days: int = 30) -> MerchantConfig:
    return MerchantConfig(
        merchant_id="11111111-1111-1111-1111-111111111111",
        churn_window_days=churn_window_days,
    )


NOW = datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc)


# ─── normalize_to_monthly_paise ───────────────────────────────────────────────

class TestNormalize:
    def test_monthly_unchanged(self):
        assert normalize_to_monthly_paise(299900, "monthly") == 299900

    def test_yearly_divided_by_12(self):
        # 36000000 paise / 12 = 3000000
        assert normalize_to_monthly_paise(36_000_00, "yearly") == 300_000

    def test_quarterly_divided_by_3(self):
        assert normalize_to_monthly_paise(900_000, "quarterly") == 300_000

    def test_daily_multiplied_by_30(self):
        assert normalize_to_monthly_paise(10_000, "daily") == 300_000

    def test_weekly_multiplied_by_4(self):
        assert normalize_to_monthly_paise(75_000, "weekly") == 300_000

    def test_always_integer(self):
        result = normalize_to_monthly_paise(100_001, "yearly")
        assert isinstance(result, int)

    def test_zero_amount(self):
        assert normalize_to_monthly_paise(0, "monthly") == 0


# ─── process_event: subscription.charged ────────────────────────────────────

class TestCharged:
    def test_new_subscription(self):
        """First payment on a subscription → movement type 'new'."""
        event = _event("subscription_charged_first")
        snap = _snapshot(mrr_paise=0, ever_paid=False)
        movement = process_event(event, snap, _config(), now=NOW)

        assert movement is not None
        assert movement.movement_type == "new"
        assert movement.amount_paise == 299900
        assert movement.prev_amount_paise == 0
        assert movement.delta_paise == 299900

    def test_renewal_no_movement(self):
        """Same amount renewal → None (no MRR movement)."""
        event = _event("subscription_charged_renewal")
        snap = _snapshot(mrr_paise=299900, ever_paid=True)
        movement = process_event(event, snap, _config(), now=NOW)

        assert movement is None

    def test_expansion(self):
        """Higher amount payment → movement type 'expansion'."""
        event = _event("subscription_charged_upgrade")
        snap = _snapshot(mrr_paise=299900, ever_paid=True)
        movement = process_event(event, snap, _config(), now=NOW)

        assert movement is not None
        assert movement.movement_type == "expansion"
        assert movement.amount_paise == 799900
        assert movement.prev_amount_paise == 299900
        assert movement.delta_paise == 500000  # 799900 - 299900

    def test_contraction(self):
        """Lower amount payment → movement type 'contraction'."""
        event = _event("subscription_charged_downgrade")
        snap = _snapshot(mrr_paise=799900, ever_paid=True)
        movement = process_event(event, snap, _config(), now=NOW)

        assert movement is not None
        assert movement.movement_type == "contraction"
        assert movement.amount_paise == 299900
        assert movement.prev_amount_paise == 799900
        assert movement.delta_paise == -500000  # 299900 - 799900

    def test_reactivation(self):
        """Payment after churn (ever_paid=True, mrr=0) → 'reactivation'."""
        event = _event("subscription_charged_reactivation")
        snap = _snapshot(mrr_paise=0, ever_paid=True, status="cancelled")
        movement = process_event(event, snap, _config(), now=NOW)

        assert movement is not None
        assert movement.movement_type == "reactivation"
        assert movement.amount_paise == 299900
        assert movement.delta_paise == 299900

    def test_quarterly_subscription_normalized(self):
        """Quarterly plan charge correctly normalized to monthly MRR."""
        event = _event("subscription_charged_first")
        # Override: quarterly plan, same subscription
        event.amount_paise = 900_000  # ₹9000 quarterly
        snap = _snapshot(mrr_paise=0, ever_paid=False, interval_type="quarterly")
        movement = process_event(event, snap, _config(), now=NOW)

        assert movement is not None
        assert movement.movement_type == "new"
        assert movement.amount_paise == 300_000  # 900000 / 3


# ─── process_event: subscription.cancelled ───────────────────────────────────

class TestCancelled:
    def test_voluntary_churn(self):
        """Cancellation → voluntary churn."""
        event = _event("subscription_cancelled")
        snap = _snapshot(mrr_paise=299900, ever_paid=True)
        movement = process_event(event, snap, _config(), now=NOW)

        assert movement is not None
        assert movement.movement_type == "churn"
        assert movement.voluntary is True
        assert movement.amount_paise == 0
        assert movement.prev_amount_paise == 299900
        assert movement.delta_paise == -299900

    def test_cancel_already_zero_mrr(self):
        """Cancellation when MRR already 0 → None (nothing to churn)."""
        event = _event("subscription_cancelled")
        snap = _snapshot(mrr_paise=0, ever_paid=True, status="cancelled")
        movement = process_event(event, snap, _config(), now=NOW)

        assert movement is None


# ─── process_event: subscription.completed ───────────────────────────────────

class TestCompleted:
    def test_involuntary_churn_on_completion(self):
        """Subscription ran out of cycles → involuntary churn."""
        event = _event("subscription_completed")
        snap = _snapshot(
            sub_id="sub_annual001",
            mrr_paise=250_000,
            ever_paid=True,
            interval_type="yearly",
        )
        movement = process_event(event, snap, _config(), now=NOW)

        assert movement is not None
        assert movement.movement_type == "churn"
        assert movement.voluntary is False
        assert movement.delta_paise == -250_000

    def test_completed_zero_mrr(self):
        event = _event("subscription_completed")
        snap = _snapshot(sub_id="sub_annual001", mrr_paise=0, ever_paid=True)
        movement = process_event(event, snap, _config(), now=NOW)
        assert movement is None


# ─── process_event: subscription.halted ──────────────────────────────────────

class TestHalted:
    def test_halted_within_window_no_churn(self):
        """Halted but churn window not yet expired → no churn movement."""
        event = _event("subscription_halted_in_window")
        # Period ended 10 days ago, churn window is 30 days → not expired
        period_end = datetime(2024, 3, 1, tzinfo=timezone.utc)
        snap = _snapshot(
            sub_id="sub_monthly002",
            mrr_paise=299900,
            ever_paid=True,
            current_period_end=period_end,
        )
        now = datetime(2024, 3, 10, tzinfo=timezone.utc)
        movement = process_event(event, snap, _config(churn_window_days=30), now=now)

        assert movement is None

    def test_halted_past_window_churns(self):
        """Halted and churn window expired → involuntary churn."""
        event = _event("subscription_halted_expired")
        # Period ended 35 days ago, churn window is 30 days → expired
        period_end = datetime(2024, 3, 1, tzinfo=timezone.utc)
        snap = _snapshot(
            sub_id="sub_monthly003",
            mrr_paise=299900,
            ever_paid=True,
            current_period_end=period_end,
        )
        now = datetime(2024, 4, 5, tzinfo=timezone.utc)  # 35 days later
        movement = process_event(event, snap, _config(churn_window_days=30), now=now)

        assert movement is not None
        assert movement.movement_type == "churn"
        assert movement.voluntary is False


# ─── process_event: no-ops ───────────────────────────────────────────────────

class TestNoOps:
    def test_paused_no_movement(self):
        event = _event("subscription_charged_first")
        event.event_type = "subscription.paused"
        snap = _snapshot(mrr_paise=299900, ever_paid=True)
        assert process_event(event, snap, _config(), now=NOW) is None

    def test_authenticated_no_movement(self):
        event = _event("subscription_charged_first")
        event.event_type = "subscription.authenticated"
        snap = _snapshot(mrr_paise=0, ever_paid=False)
        assert process_event(event, snap, _config(), now=NOW) is None

    def test_unknown_event_type_no_movement(self):
        event = _event("subscription_charged_first")
        event.event_type = "some.unknown.event"
        snap = _snapshot(mrr_paise=299900, ever_paid=True)
        assert process_event(event, snap, _config(), now=NOW) is None


# ─── updated_snapshot ─────────────────────────────────────────────────────────

class TestUpdatedSnapshot:
    def test_new_subscription_sets_ever_paid(self):
        event = _event("subscription_charged_first")
        snap = _snapshot(mrr_paise=0, ever_paid=False)
        movement = process_event(event, snap, _config(), now=NOW)
        new_snap = updated_snapshot(snap, event, movement)

        assert new_snap.ever_paid is True
        assert new_snap.mrr_paise == 299900
        assert new_snap.status == "active"

    def test_cancellation_zeros_mrr(self):
        event = _event("subscription_cancelled")
        snap = _snapshot(mrr_paise=299900, ever_paid=True)
        movement = process_event(event, snap, _config(), now=NOW)
        new_snap = updated_snapshot(snap, event, movement)

        assert new_snap.mrr_paise == 0
        assert new_snap.status == "cancelled"
        assert new_snap.churned_at is not None

    def test_renewal_mrr_unchanged(self):
        event = _event("subscription_charged_renewal")
        snap = _snapshot(mrr_paise=299900, ever_paid=True)
        movement = process_event(event, snap, _config(), now=NOW)  # None
        new_snap = updated_snapshot(snap, event, movement)

        assert new_snap.mrr_paise == 299900  # unchanged
        assert new_snap.ever_paid is True


# ─── Money invariants ─────────────────────────────────────────────────────────

class TestMoneyInvariants:
    """Verify that no floats ever leak into MRR calculations."""

    def test_all_amounts_are_int(self):
        event = _event("subscription_charged_first")
        snap = _snapshot(mrr_paise=0, ever_paid=False)
        movement = process_event(event, snap, _config(), now=NOW)

        assert isinstance(movement.amount_paise, int)
        assert isinstance(movement.prev_amount_paise, int)
        assert isinstance(movement.delta_paise, int)

    def test_yearly_normalization_integer(self):
        event = _event("subscription_charged_first")
        event.amount_paise = 35_988_00  # ₹35,988 yearly
        snap = _snapshot(mrr_paise=0, ever_paid=False, interval_type="yearly")
        movement = process_event(event, snap, _config(), now=NOW)

        assert isinstance(movement.amount_paise, int)
        assert movement.amount_paise == int(3_598_800 / 12)
