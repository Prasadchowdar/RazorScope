"""
Unit tests for the agentic churn defender endpoint.
Kept to ≤ 3 endpoint calls per test run to stay within the 3/minute rate limit.
"""
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_merchant_id
from api.db import postgres as pg_db

MERCHANT = "11111111-1111-1111-1111-111111111111"


def _override_auth():
    return MERCHANT


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_merchant_id] = _override_auth
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    with patch("api.db.postgres.init_pool"), \
         patch("api.db.postgres.close_pool"), \
         patch("api.db.clickhouse.init_client"):
        with TestClient(app) as c:
            yield c


def _mock_ch(rows):
    mock_result = MagicMock()
    mock_result.result_rows = rows
    mock_client = MagicMock()
    mock_client.query.return_value = mock_result
    return mock_client


def _at_risk_rows():
    return [("sub_001", "cust-uuid-001", "plan_pro", 299900, 2, "2026-01-01")]


def _customer():
    return {
        "id": "cust-uuid-001",
        "name": "Acme Corp",
        "email": "ceo@acme.com",
        "phone": None,
        "company": "Acme",
        "source": "inbound",
        "merchant_id": MERCHANT,
    }


def _stop_response():
    choice = MagicMock()
    choice.message.tool_calls = None
    choice.message.content = "Done"
    choice.finish_reason = "stop"
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _tool_response(name, args, call_id="call_1"):
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = json.dumps(args)
    choice = MagicMock()
    choice.message.tool_calls = [tc]
    choice.message.content = None
    choice.finish_reason = "tool_calls"
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestAgenticChurnDefender:
    def test_no_at_risk_subs_returns_found_zero(self, client):
        with patch("api.db.clickhouse._ch", return_value=_mock_ch([])), \
             patch("api.routers.agents_router.get_client"):
            resp = client.post("/api/v1/agents/churn-defender/run",
                               headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        assert resp.json()["found"] == 0
        assert resp.json()["previews"] == []

    def test_at_risk_sub_found_count_and_preview_fields(self, client):
        def minimal_loop(*args, **kwargs):
            return _stop_response()

        with patch("api.db.clickhouse._ch", return_value=_mock_ch(_at_risk_rows())), \
             patch.object(pg_db, "get_customer_by_razorpay_id", return_value=_customer()), \
             patch.object(pg_db, "create_task", return_value={"id": "t1"}) as mock_task, \
             patch("api.routers.agents_router.get_client") as mock_get:
            mock_get.return_value.chat.completions.create.side_effect = minimal_loop
            resp = client.post("/api/v1/agents/churn-defender/run",
                               headers={"X-Api-Key": "any"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["found"] == 1
        assert body["tasks_created"] == mock_task.call_count
        assert len(body["previews"]) == 1
        p = body["previews"][0]
        for field in ("razorpay_sub_id", "customer_name", "customer_email",
                      "plan_id", "current_mrr_paise", "risk_label",
                      "draft_subject", "draft_body", "tool_calls_made", "reasoning_steps"):
            assert field in p, f"Missing field: {field}"

    def test_missing_customer_still_returns_200(self, client):
        def minimal_loop(*args, **kwargs):
            return _stop_response()

        with patch("api.db.clickhouse._ch", return_value=_mock_ch(_at_risk_rows())), \
             patch.object(pg_db, "get_customer_by_razorpay_id", return_value=None), \
             patch("api.routers.agents_router.get_client") as mock_get:
            mock_get.return_value.chat.completions.create.side_effect = minimal_loop
            resp = client.post("/api/v1/agents/churn-defender/run",
                               headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        assert resp.json()["found"] == 1
