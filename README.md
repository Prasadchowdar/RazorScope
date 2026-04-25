# RazorScope

Subscription analytics and revenue intelligence for Razorpay merchants — with AI agents that replace manual workflows.

Built end-to-end with a real-time event pipeline (Razorpay webhooks → Kafka → metric worker → ClickHouse) feeding a React dashboard and four GPT-4o powered AI features.

---

## AI Features

### Ask RazorScope — Natural Language Analytics
Type a question in plain English. The agent translates it to ClickHouse SQL via function-calling, executes it, and returns a table with a one-sentence AI insight.

> *Replaces: an analyst writing SQL queries manually*

**Example queries:**
- "Show churn by plan for the last 6 months"
- "Which country has the highest expansion MRR?"
- "New vs churned subscribers per month in 2025"

### Churn Defender — Agentic Multi-Step Loop
One click triggers a true GPT-4o tool-use loop per at-risk subscriber. The agent inspects payment history, reads CRM notes via **RAG (pgvector semantic search)**, drafts a personalized retention email, sets a risk label, and creates a CRM task — up to 6 reasoning steps per subscriber.

> *Replaces: a CSM doing weekly manual at-risk reviews*

Each subscriber card in the UI shows a collapsible reasoning trace with every tool call the agent made.

### Churn Risk Score — Deterministic Scoring
Every subscriber gets a 0–100 risk score computed from four signals: recent contraction, payment failures, tenure, and MRR vs peak. Scores appear as color-coded badges in the movements table and subscriber drawer.

> *Replaces: gut-feel CSM prioritisation*

### MRR Forecast — 3-Month Projection
The MRR chart extends 3 months forward using OLS linear regression on historical closing MRR. Forecast bars are rendered at reduced opacity with a confidence interval and a dashed boundary line separating actual from projected data.

> *Replaces: a spreadsheet revenue model*

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
| Postgres + pgvector | — | Operational store + vector embeddings for RAG |
| ClickHouse | — | Analytics store (MRR movements, cohort retention) |
| Kafka | — | Event transport between receiver and worker |
| Redis | — | Bloom filter for webhook deduplication |
| Prometheus + Grafana | — | Metrics and monitoring |
| Nginx | — | Reverse proxy for frontend |

**202+ tests** — API service + metric-worker (49).

---

## What It Covers

- Real-time Razorpay webhook ingestion with HMAC validation and idempotency
- MRR movements: new, expansion, contraction, churn, reactivation
- Cohort retention heatmap (up to 24 months)
- Subscriber segmentation: plan, country, source, payment method
- ARPU, churn rate, NRR, LTV, SaaS benchmarks
- Churn risk scores (0–100) with factor breakdown per subscriber
- MRR 3-month forecast with confidence intervals
- RAG embeddings on CRM notes via pgvector for personalized outreach
- Agentic churn defender with multi-step tool-use loop and reasoning trace UI
- CRM: Kanban pipeline, lead drawer, tasks, sequences, rep performance
- Historical backfill via Razorpay API
- JWT auth, named API keys, RBAC, audit log
- Prometheus + Grafana monitoring
- Runtime environment injection (no secrets baked into frontend builds)

---

## Quick Start (Docker)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2)
- An OpenAI API key — **required for the AI agents tab**. Everything else runs without it.

### 1. Configure environment

```bash
cp .env.example .env
```

Open `.env` and set your OpenAI API key (leave blank to skip AI features):

```
OPENAI_API_KEY=sk-proj-...
```

Or pass it inline without editing any file:

```bash
OPENAI_API_KEY=sk-proj-... docker compose up -d --wait
```

### 2. Start the full stack

```bash
docker compose up -d --wait
```

This pulls images, builds services, runs Postgres migrations (including pgvector), and waits until all health checks pass (~2–3 minutes on first run).

### 3. Seed ClickHouse schema + demo data

```bash
# Apply ClickHouse table schemas
for f in schema/clickhouse/*.sql; do
  docker compose exec -T clickhouse clickhouse-client \
    --user razorscope --password razorscope_dev --database razorscope \
    --query "$(cat $f)"
done

# Seed demo merchants and movements
docker compose exec api python seed_demo.py
```

### 4. Open the app

```
http://localhost:3001
```

Register an account. Connect Razorpay in **Settings**, or use the seeded demo data to explore immediately.

After seeding, go to the **AI ✦** tab and try:
- **Ask:** "Show MRR by plan for last 6 months"
- **Churn Defender:** Run → see the agentic tool-call trace per subscriber
- **Monthly Brief:** Generate for the current month

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
# From Docker (no local Python needed)
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
├── migrations/postgres/  # Flyway SQL migrations (V1–V19, includes pgvector)
├── schema/clickhouse/    # ClickHouse DDL
├── monitoring/           # Prometheus config + Grafana provisioning
├── nginx/                # Production nginx config
├── scripts/              # Utility scripts (e2e test, backfill, seed)
├── docker-compose.yml        # Development stack
├── docker-compose.prod.yml   # Production stack
└── .env.example              # Environment template
```
