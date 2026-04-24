from fastapi import APIRouter
from api.db import postgres, clickhouse

router = APIRouter()


@router.get("/health")
def health():
    checks: dict[str, str] = {}
    try:
        postgres.merchant_id_for_api_key("__ping__")
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"

    try:
        clickhouse._ch().query("SELECT 1")
        checks["clickhouse"] = "ok"
    except Exception as exc:
        checks["clickhouse"] = f"error: {exc}"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, **checks}
