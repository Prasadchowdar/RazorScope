# RazorScope

Subscription analytics and revenue intelligence for Razorpay merchants — with AI agents that replace manual workflows.

Built end-to-end with a real-time event pipeline (Razorpay webhooks → Kafka → metric worker → ClickHouse) feeding a React dashboard and three GPT-4o powered agents.

---

## AI Agents

### Ask RazorScope — Natural Language Analytics
Type a question in plain English. The agent translates it to ClickHouse SQL via function-calling, executes it, and returns a table with a one-sentence AI insight.

> *Replaces: an analyst writing SQL queries manually*

**Example queries:**
- "Show churn by plan for the last 6 months"
- "Which country has the highest expansion MRR?"
- "New vs churned subscribers per month in 2025"

### Churn Defender — At-Risk Subscriber Agent
One click. Scans ClickHouse for subscribers with recent contraction movements, calls GPT-4o to draft a personalized retention email per subscriber, and creates a CRM task for each — draft-only, reviewed before sending.

> *Replaces: a CSM doing weekly manual at-risk reviews*

### Monthly Brief Generator
Pick a month. Pulls MRR movements, churn stats, and cohort retention, then writes an investor-quality narrative brief in markdown.

> *Replaces: a founder spending 2 hours writing the monthly update*

---

## Architecture

12 services across 4 languages:

| Service | Stack | Role |
|---|---|---|
| `services/frontend` | React + Vite + Tailwind | Dashboard, AI tab, CRM, setup flow |
| `services/api` | FastAPI (Python) | Analytics, auth, AI agent endpoints, backfill |
| `services/webhook-receiver` | Go | Validates + ingests Razorpay webhook events |
| `services/metric-worker` | Python | Kafka consumer, MRR state machine, cohort jobs |
| Postgres | — | Operational store (merchants, users, CRM, API keys) |
| ClickHouse | — | Analytics store (MRR movements, cohort retention) |
| Kafka | — | Event transport between receiver and worker |
| Redis | — | Bloom filter for webhook deduplication |
| Prometheus + Grafana | — | Metrics and monitoring |
| Nginx | — | Reverse proxy for frontend |

**229 tests** — API service (180) + metric-worker (49).

---

## What It Covers

- Real-time Razorpay webhook ingestion with HMAC validation and idempotency
- MRR movements: new, expansion, contraction, churn, reactivation
- Cohort retention heatmap (up to 24 months)
- Subscriber segmentation: plan, country, source, payment method
- ARPU, churn rate, NRR, LTV, SaaS benchmarks
- CRM: Kanban pipeline, lead drawer, tasks, sequences, rep performance
- Historical backfill via Razorpay API
- JWT auth, named API keys, RBAC, audit log
- Prometheus + Grafana monitoring
- Runtime environment injection (no secrets baked into frontend builds)

---

## Quick Start (Docker)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2)
- An OpenAI API key — **required only for the AI agents tab**. Everything else runs without it.

### 1. Configure environment

```bash
cp .env.example .env
```

Open `.env` and set your OpenAI API key (leave blank to skip AI features):

```
OPENAI_API_KEY=sk-proj-...
```

### 2. Start the full stack

```bash
docker compose up -d --wait
```

This pulls images, builds services, runs Postgres migrations, and waits until all health checks pass (~2–3 minutes on first run).

### 3. Open the app

```
http://localhost:3001
```

Register an account. Connect Razorpay in **Settings**, or seed demo data to explore immediately:

```bash
docker compose exec api python seed_demo.py
```

After seeding, go to the **AI ✦** tab and try all three agents.

---

## Service Ports

| Port | Service |
|------|---------|
| `3001` | Frontend (React dashboard) |
| `8090` | Dashboard API (FastAPI) |
| `8080` | Webhook Receiver (Go) |
| `9090` | Prometheus |
| `3000` | Grafana (`admin` / `razorscope_dev`) |
| `5432` | Postgres |
| `8123` | ClickHouse HTTP |
| `6379` | Redis |
| `29092` | Kafka (external listener) |

---

## Run Tests

```bash
# API — 180 tests
cd services/api && pip install -r requirements.txt && pytest tests/ -q

# Metric worker — 49 tests
cd services/metric-worker && pip install -r requirements.txt && pytest tests/ -q
```

Or run both from Docker (no local Python needed):

```bash
docker compose exec api pytest tests/ -q
docker compose exec metric-worker pytest tests/ -q
```

---

## End-to-End Webhook Test

Send a test webhook event through the full pipeline (receiver → Kafka → worker → ClickHouse → dashboard):

```bash
bash scripts/test-e2e.sh
```

---

## Production Deploy

```bash
cp .env.production.example .env.prod
# Fill in all values (strong passwords, real OPENAI_API_KEY, JWT_SECRET_KEY, etc.)
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d
```

---

## Project Structure

```
├── services/
│   ├── api/              # FastAPI — analytics, auth, AI endpoints
│   ├── webhook-receiver/ # Go — Razorpay webhook ingestion
│   ├── metric-worker/    # Python — Kafka consumer, MRR state machine
│   └── frontend/         # React + Vite — dashboard UI
├── migrations/postgres/  # Flyway SQL migrations (V1–V18)
├── schema/clickhouse/    # ClickHouse DDL
├── monitoring/           # Prometheus config + Grafana provisioning
├── nginx/                # Production nginx config
├── scripts/              # Utility scripts (e2e test, backfill, seed)
├── docker-compose.yml        # Development stack
├── docker-compose.prod.yml   # Production stack
└── .env.example              # Environment template
```
