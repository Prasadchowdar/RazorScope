"""
Unit tests for the agentic churn defender endpoint.
Mocks OpenAI client to return a deterministic tool-use loop.
"""
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_merchant_id
from api.db import clickhouse as ch_db
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


def _sub_rows():
    return [
        {
            "razorpay_sub_id": "sub_001",
            "customer_id": "11111111-aaaa-bbbb-cccc-dddddddddddd",
            "plan_id": "plan_pro",
            "current_mrr_paise": 299900,
        }
    ]


def _customer():
    return {
        "id": "11111111-aaaa-bbbb-cccc-dddddddddddd",
        "name": "Acme Corp",
        "email": "ceo@acme.com",
        "phone": None,
        "company": "Acme",
        "source": "inbound",
        "merchant_id": MERCHANT,
    }


def _make_openai_response(tool_name: str, tool_input: dict, call_id: str = "call_1"):
    """Build a mock OpenAI chat completion that makes one tool call."""
    tool_call = MagicMock()
    tool_call.id = call_id
    tool_call.function.name = tool_name
    import json
    tool_call.function.arguments = json.dumps(tool_input)

    choice = MagicMock()
    choice.message.tool_calls = [tool_call]
    choice.message.content = None
    choice.finish_reason = "tool_calls"

    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_final_response(content: str = "Done"):
    choice = MagicMock()
    choice.message.tool_calls = None
    choice.message.content = content
    choice.finish_reason = "stop"

    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestAgenticChurnDefender:
    def _patch_all(self, mock_create, task_result=None):
        """Wire up the agentic loop: set_risk_label → draft_retention_email → create_crm_task."""
        task_result = task_result or {"id": "task_abc", "type": "follow_up", "body": "Contact Acme"}

        def side_effect(*args, **kwargs):
            messages = kwargs.get("messages") or args[1] if len(args) > 1 else []
            # count assistant tool messages already appended
            tool_msg_count = sum(1 for m in messages if getattr(m, "role", None) == "tool"
                                  or (isinstance(m, dict) and m.get("role") == "tool"))
            if tool_msg_count == 0:
                return _make_openai_response("set_risk_label", {"label": "high"})
            elif tool_msg_count == 1:
                return _make_openai_response("draft_retention_email", {
                    "subject": "We miss you", "body": "Hi Acme, ..."
                }, call_id="call_2")
            elif tool_msg_count == 2:
                return _make_openai_response("create_crm_task", {
                    "task_type": "follow_up", "body": "Contact Acme"
                }, call_id="call_3")
            else:
                return _make_final_response()

        mock_create.side_effect = side_effect

    def test_returns_200_with_previews(self, client):
        with patch.object(ch_db, "mrr_contraction_subscribers", return_value=_sub_rows()), \
             patch.object(pg_db, "get_customer_by_id", return_value=_customer()), \
             patch.object(pg_db, "create_task", return_value={"id": "t1"}), \
             patch("api.routers.agents_router.generate_query_embedding", return_value=[0.0] * 1536), \
             patch("api.db.postgres.search_similar_context", return_value=[]), \
             patch("api.routers.agents_router.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            self._patch_all(mock_client.chat.completions.create)
            resp = client.post("/api/v1/agents/churn-defender/run", headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        body = resp.json()
        assert "previews" in body
        assert "found" in body

    def test_no_at_risk_subs_returns_found_zero(self, client):
        with patch.object(ch_db, "mrr_contraction_subscribers", return_value=[]), \
             patch("api.routers.agents_router.get_client"):
            resp = client.post("/api/v1/agents/churn-defender/run", headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        assert resp.json()["found"] == 0
        assert resp.json()["previews"] == []

    def test_preview_has_expected_fields(self, client):
        with patch.object(ch_db, "mrr_contraction_subscribers", return_value=_sub_rows()), \
             patch.object(pg_db, "get_customer_by_id", return_value=_customer()), \
             patch.object(pg_db, "create_task", return_value={"id": "t1"}), \
             patch("api.routers.agents_router.generate_query_embedding", return_value=[0.0] * 1536), \
             patch("api.db.postgres.search_similar_context", return_value=[]), \
             patch("api.routers.agents_router.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            self._patch_all(mock_client.chat.completions.create)
            resp = client.post("/api/v1/agents/churn-defender/run", headers={"X-Api-Key": "any"})
        if resp.json()["previews"]:
            p = resp.json()["previews"][0]
            for field in ("razorpay_sub_id", "customer_name", "customer_email",
                          "plan_id", "current_mrr_paise", "risk_label",
                          "draft_subject", "draft_body", "tool_calls_made", "reasoning_steps"):
                assert field in p, f"Missing field: {field}"

    def test_tasks_created_count_matches(self, client):
        with patch.object(ch_db, "mrr_contraction_subscribers", return_value=_sub_rows()), \
             patch.object(pg_db, "get_customer_by_id", return_value=_customer()), \
             patch.object(pg_db, "create_task", return_value={"id": "t1"}) as mock_task, \
             patch("api.routers.agents_router.generate_query_embedding", return_value=[0.0] * 1536), \
             patch("api.db.postgres.search_similar_context", return_value=[]), \
             patch("api.routers.agents_router.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            self._patch_all(mock_client.chat.completions.create)
            resp = client.post("/api/v1/agents/churn-defender/run", headers={"X-Api-Key": "any"})
        body = resp.json()
        assert body["tasks_created"] == mock_task.call_count

    def test_missing_customer_does_not_crash(self, client):
        with patch.object(ch_db, "mrr_contraction_subscribers", return_value=_sub_rows()), \
             patch.object(pg_db, "get_customer_by_id", return_value=None), \
             patch("api.routers.agents_router.get_client"):
            resp = client.post("/api/v1/agents/churn-defender/run", headers={"X-Api-Key": "any"})
        assert resp.status_code == 200
        assert resp.json()["found"] == 1
        assert resp.json()["previews"] == []
