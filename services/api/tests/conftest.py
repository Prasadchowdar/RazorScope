"""Shared pytest fixtures for RazorScope API tests."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.auth import get_merchant_id, require_admin
from api.main import app

MERCHANT = "11111111-1111-1111-1111-111111111111"


def _override_auth():
    return MERCHANT


@pytest.fixture()
def auth_client():
    """TestClient with get_merchant_id overridden — for protected endpoints."""
    app.dependency_overrides[get_merchant_id] = _override_auth
    app.dependency_overrides[require_admin] = _override_auth
    with patch("api.db.postgres.init_pool"), \
         patch("api.db.postgres.close_pool"), \
         patch("api.db.clickhouse.init_client"):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def public_client():
    """TestClient with NO auth override — for public endpoints like /auth/*."""
    with patch("api.db.postgres.init_pool"), \
         patch("api.db.postgres.close_pool"), \
         patch("api.db.clickhouse.init_client"):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
