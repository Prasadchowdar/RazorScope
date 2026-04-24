# How I built RazorScope with Claude Code

## The problem

Razorpay merchants have no first-class subscription analytics. They can export CSVs. They can see a basic dashboard. But there is no ChartMogul for Razorpay — no MRR waterfall, no cohort retention, no churn breakdown by plan. I built one.

But the more interesting part is what I added on top.

---

## What I built

RazorScope is a 12-service subscription analytics platform: a Go webhook receiver that validates and ingests Razorpay events, a Kafka-backed Python metric worker that runs an MRR state machine, a FastAPI dashboard API with 14 routers, a React + ClickHouse analytics frontend, Postgres for operational data, and Prometheus + Grafana for observability.

It covers the full ChartMogul feature set: MRR movements, cohort retention, plan analytics, ARPU, NRR, LTV, SaaS benchmarks, subscriber segmentation, a CRM with Kanban pipeline and sequences, JWT auth, named API keys, RBAC, and audit log.

**229 tests.** Production Docker Compose. Runtime env injection so no secrets are baked into builds.

I built this with Claude Code as my primary tool — not to generate boilerplate, but to move fast across a stack I was building simultaneously in Go, Python, and TypeScript.

---

## The Claude Code workflow

The thing that changed how I work is treating Claude Code not as an autocomplete but as a pair programmer that can hold the entire codebase in context.

A few patterns that actually mattered:

**Cross-service consistency without copy-pasting.** When I added segmentation filters (country, source, payment method) across the stack, the change touched Go structs, Kafka payloads, Python worker logic, ClickHouse schema, FastAPI query parameters, React hooks, and filter UI — 8 files across 4 services. One Claude Code session, one review pass. The alternative was 2 days of context-switching.

**Test-first, not test-after.** For every new router I wrote, I'd describe the contract to Claude Code and ask for tests before implementation. This caught three edge cases in the MRR state machine before they hit production — including a double-counting bug when a subscription was cancelled and reactivated in the same billing period.

**The dual-auth migration.** The riskiest change was replacing a single API-key auth system with dual-auth (API key + JWT Bearer) without breaking the 11 existing routers that depended on `get_merchant_id`. I described the constraint, Claude Code proposed a dependency-injection approach using FastAPI's `Depends()` chain that required zero changes to existing routers. I reviewed the diff, ran the full test suite, shipped.

---

## The AI agents

After building the analytics foundation, I added three agents that replace actual workflows — not demos, production features:

**Ask RazorScope** uses GPT-4o function-calling with one tool: `execute_analytics_query(sql)`. The system prompt describes the ClickHouse schema (three tables, their columns, ReplacingMergeTree constraints). The model generates safe SQL, I validate it (SELECT-only, merchant_id scoped, LIMIT capped), execute it, then ask the model to summarize the result in one sentence. The whole thing is ~80 lines of Python.

*What it replaces: an analyst writing ClickHouse SQL to answer a one-off business question.*

**Churn Defender** is an agentic workflow: query ClickHouse for subscribers with contraction movements in the last 90 days → join with Postgres for name and email → call GPT-4o with subscriber context → receive a draft retention email as structured JSON → create a CRM task per subscriber. One endpoint, no human in the loop until review.

*What it replaces: a CSM's weekly manual review of at-risk subscribers.*

**Monthly Brief Generator** pulls six metrics from ClickHouse (opening MRR, movement breakdown by type, churn rate, cohort retention), formats them as a structured prompt, and asks GPT-4o to write a 300-word investor narrative. The output is specific — it cites actual numbers, flags risks, notes opportunities.

*What it replaces: the 2-hour monthly update a founder writes for their investors.*

---

## What I learned about building with AI

The bottleneck in AI-assisted development is not generation speed — it is review quality. Claude Code can generate a correct-looking FastAPI router in 30 seconds. The question is whether you can read the diff fast enough to catch the subtle things: a missing `FINAL` modifier on a ReplacingMergeTree query, a rate limit that's too generous on an expensive endpoint, a SQL injection surface on a user-controlled parameter.

The developers who will win with AI tools are not the ones who trust the output most — they are the ones who review it fastest. That is a different skill than writing code, and it is the skill I've been building.

The other thing I learned: the most valuable use of an AI agent is not generating code. It is replacing the cognitive overhead of context-switching. When I had to touch 8 files across 4 services for a single feature, the question was not "can I do this?" — it was "can I hold all of it in my head at once?" With Claude Code, I did not have to. I described the change, reviewed the output service by service, and shipped.

---

## Numbers

- 12 services, 4 languages (Go, Python, TypeScript, SQL)
- 229 tests (180 API, 49 metric-worker)
- 3 AI agents replacing 3 distinct workflows
- ~3 weeks from blank directory to production-ready

The repo is at: [github.com/your-username/razorscope]
