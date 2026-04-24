import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from prometheus_fastapi_instrumentator import Instrumentator

from api.config import Config
from api.db import clickhouse, postgres
from api.limiter import limiter
from api.routers import (
    agents_router,
    auth_router,
    backfill,
    benchmarks,
    cohort,
    crm,
    health,
    integrations,
    metrics,
    mrr,
    plans,
    security,
    segments,
    subscribers,
)

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Config.validate_runtime()
    postgres.init_pool(Config.DATABASE_URL)
    clickhouse.init_client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database=Config.CLICKHOUSE_DB,
    )
    yield
    postgres.close_pool()


app = FastAPI(title="RazorScope Dashboard API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_headers=["X-Api-Key", "Content-Type", "Authorization"],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_credentials=True,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(health.router)
app.include_router(mrr.router)
app.include_router(cohort.router)
app.include_router(metrics.router)
app.include_router(benchmarks.router)
app.include_router(plans.router)
app.include_router(subscribers.router)
app.include_router(backfill.router)
app.include_router(crm.router)
app.include_router(segments.router)
app.include_router(security.router)
app.include_router(integrations.router)
app.include_router(auth_router.router)
app.include_router(agents_router.router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=Config.PORT, reload=False)
