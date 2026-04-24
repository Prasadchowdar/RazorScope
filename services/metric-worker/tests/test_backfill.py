"""
Unit tests for the backfill worker module.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch, call

import pytest

from worker.backfill.razorpay_client import DevRazorpayClient
from worker.backfill.processor import run_backfill_job, poll_and_run_backfill
from worker.models import MRRMovement
from datetime import datetime


MERCHANT = "11111111-1111-1111-1111-111111111111"
JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _make_job(**kwargs):
    defaults = {
        "job_id": JOB_ID,
        "merchant_id": MERCHANT,
        "from_date": date(2024, 1, 1),
        "to_date": date(2024, 3, 1),
        "pages_fetched": 0,
        "cursor": None,
    }
    defaults.update(kwargs)
    return defaults


# ─── DevRazorpayClient ────────────────────────────────────────────────────────

class TestDevRazorpayClient:
    def test_generates_events_in_range(self):
        client = DevRazorpayClient()
        events, _ = client.fetch_page(MERCHANT, date(2024, 1, 1), date(2024, 3, 1), None)
        assert len(events) > 0

    def test_events_have_correct_structure(self):
        client = DevRazorpayClient()
        events, _ = client.fetch_page(MERCHANT, date(2024, 1, 1), date(2024, 1, 1), None)
        required_keys = {"event_id", "merchant_id", "event_type", "sub_id",
                         "payment_id", "customer_id", "plan_id", "amount_paise",
                         "currency", "payment_method", "raw_payload", "received_at"}
        for ev in events:
            assert required_keys.issubset(ev.keys())

    def test_event_type_is_subscription_charged(self):
        client = DevRazorpayClient()
        events, _ = client.fetch_page(MERCHANT, date(2024, 1, 1), date(2024, 1, 1), None)
        for ev in events:
            assert ev["event_type"] == "subscription.charged"

    def test_amount_paise_is_integer(self):
        client = DevRazorpayClient()
        events, _ = client.fetch_page(MERCHANT, date(2024, 1, 1), date(2024, 1, 1), None)
        for ev in events:
            assert isinstance(ev["amount_paise"], int)
            assert ev["amount_paise"] > 0

    def test_returns_none_cursor_on_last_page(self):
        client = DevRazorpayClient()
        # Keep paging until we get None
        cursor = None
        last_cursor = "SENTINEL"
        for _ in range(100):
            _, cursor = client.fetch_page(MERCHANT, date(2024, 1, 1), date(2024, 1, 1), cursor)
            if cursor is None:
                last_cursor = None
                break
        assert last_cursor is None

    def test_deterministic_event_ids(self):
        client = DevRazorpayClient()
        events1, _ = client.fetch_page(MERCHANT, date(2024, 1, 1), date(2024, 1, 1), None)
        events2, _ = client.fetch_page(MERCHANT, date(2024, 1, 1), date(2024, 1, 1), None)
        assert [e["event_id"] for e in events1] == [e["event_id"] for e in events2]


# ─── processor.run_backfill_job ───────────────────────────────────────────────

class TestRunBackfillJob:
    def _mock_movement(self):
        return MRRMovement(
            merchant_id=MERCHANT,
            period_month=datetime(2024, 1, 1),
            movement_type="new",
            razorpay_sub_id="sub_001",
            customer_id="cust_001",
            plan_id="plan_001",
            amount_paise=299900,
            prev_amount_paise=0,
            delta_paise=299900,
            voluntary=False,
        )

    def test_marks_job_done_on_success(self):
        job = _make_job()
        with patch("worker.backfill.processor.pg") as mock_pg, \
             patch("worker.backfill.processor.get_client") as mock_client_fn, \
             patch("worker.backfill.processor.process_event", return_value=None), \
             patch("worker.backfill.processor.updated_snapshot", return_value=MagicMock()), \
             patch("worker.backfill.processor.db"):
            mock_pg.claim_backfill_job.return_value = True
            mock_pg.load_merchant_config.return_value = MagicMock()
            mock_pg.load_snapshot.return_value = MagicMock()
            mock_pg.load_merchant_razorpay_credentials.return_value = None
            client = MagicMock()
            client.fetch_page.return_value = ([], None)
            mock_client_fn.return_value = client

            run_backfill_job(job)

        mock_pg.complete_backfill_job.assert_called_once_with(JOB_ID)

    def test_marks_job_failed_on_exception(self):
        job = _make_job()
        with patch("worker.backfill.processor.pg") as mock_pg, \
             patch("worker.backfill.processor.get_client") as mock_client_fn:
            mock_pg.claim_backfill_job.return_value = True
            mock_pg.load_merchant_config.side_effect = RuntimeError("DB down")
            mock_pg.load_merchant_razorpay_credentials.return_value = None
            mock_client_fn.return_value = MagicMock()

            run_backfill_job(job)

        mock_pg.fail_backfill_job.assert_called_once()
        args = mock_pg.fail_backfill_job.call_args[0]
        assert args[0] == JOB_ID
        assert "DB down" in args[1]

    def test_skips_job_if_already_claimed(self):
        job = _make_job()
        with patch("worker.backfill.processor.pg") as mock_pg:
            mock_pg.claim_backfill_job.return_value = False
            run_backfill_job(job)
        mock_pg.complete_backfill_job.assert_not_called()
        mock_pg.fail_backfill_job.assert_not_called()

    def test_updates_progress_per_page(self):
        job = _make_job()
        page1 = [{"event_id": "e1", "merchant_id": MERCHANT, "event_type": "subscription.charged",
                   "sub_id": "sub_1", "payment_id": "p1", "customer_id": "c1", "plan_id": "pl1",
                   "amount_paise": 99900, "currency": "INR", "payment_method": "upi",
                   "raw_payload": "{}", "received_at": "2024-01-01T00:00:00Z"}]

        with patch("worker.backfill.processor.pg") as mock_pg, \
             patch("worker.backfill.processor.get_client") as mock_client_fn, \
             patch("worker.backfill.processor.process_event", return_value=None), \
             patch("worker.backfill.processor.updated_snapshot", return_value=MagicMock()), \
             patch("worker.backfill.processor.db"):
            mock_pg.claim_backfill_job.return_value = True
            mock_pg.load_merchant_config.return_value = MagicMock()
            mock_pg.load_snapshot.return_value = MagicMock()
            mock_pg.load_merchant_razorpay_credentials.return_value = None
            client = MagicMock()
            client.fetch_page.side_effect = [(page1, "10"), ([], None)]
            mock_client_fn.return_value = client

            run_backfill_job(job)

        assert mock_pg.update_backfill_progress.call_count == 2


# ─── poll_and_run_backfill ────────────────────────────────────────────────────

class TestPollAndRunBackfill:
    def test_no_jobs_does_nothing(self):
        with patch("worker.backfill.processor.pg") as mock_pg, \
             patch("worker.backfill.processor.run_backfill_job") as mock_run:
            mock_pg.poll_pending_backfill_jobs.return_value = []
            poll_and_run_backfill()
        mock_run.assert_not_called()

    def test_runs_each_pending_job(self):
        jobs = [_make_job(job_id="job-1"), _make_job(job_id="job-2")]
        with patch("worker.backfill.processor.pg") as mock_pg, \
             patch("worker.backfill.processor.run_backfill_job") as mock_run:
            mock_pg.poll_pending_backfill_jobs.return_value = jobs
            poll_and_run_backfill()
        assert mock_run.call_count == 2
