"""
AI agent endpoints: NL analytics copilot, churn defender, monthly brief generator.
Each endpoint replaces a distinct human workflow using OpenAI GPT-4o.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from api.auth import get_merchant_id
from api.db import clickhouse, postgres
from api.limiter import limiter
from api.llm import get_client

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# ─── Schemas ─────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    summary: str


class ChurnPreview(BaseModel):
    razorpay_sub_id: str
    customer_name: str
    customer_email: str
    plan_id: str
    current_mrr_paise: int
    contraction_count: int
    draft_subject: str
    draft_body: str


class ChurnDefenderResponse(BaseModel):
    found: int
    tasks_created: int
    previews: list[ChurnPreview]


class MonthlyBriefResponse(BaseModel):
    month: str
    brief: str


# ─── SQL safety ──────────────────────────────────────────────────────────────

_DANGEROUS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE|CALL)\b",
    re.IGNORECASE,
)


def _validate_and_prepare_sql(sql: str, merchant_id: str) -> str:
    sql = sql.strip().rstrip(";")
    if not sql.upper().startswith("SELECT"):
        raise HTTPException(400, "Only SELECT queries are allowed")
    if _DANGEROUS.search(sql):
        raise HTTPException(400, "Query contains disallowed SQL keywords")
    if "{mid:String}" not in sql:
        raise HTTPException(400, "Query is missing merchant_id filter")
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql += " LIMIT 500"
    return sql


# ─── System prompts ───────────────────────────────────────────────────────────

_NL_SYSTEM = """You are a ClickHouse SQL expert for RazorScope, a subscription analytics platform.
Generate a single SELECT query to answer the user's question.

Available tables (use exact names, database prefix not needed):
1. mrr_movements FINAL
   Columns: merchant_id (String), period_month (Date, first day of month), movement_type (String: 'new'|'expansion'|'contraction'|'churn'|'reactivation'), razorpay_sub_id (String), customer_id (String), plan_id (String), amount_paise (Int64, current monthly MRR), prev_amount_paise (Int64), delta_paise (Int64, signed change), voluntary (UInt8, 1=voluntary), country (String, ISO code), source (String), payment_method (String)
   Note: Uses ReplacingMergeTree — ALWAYS include FINAL modifier.

2. cohort_retention FINAL
   Columns: merchant_id (String), cohort_month (Date), period_month (Date), period_number (UInt16, months since signup), cohort_size (UInt32), retained_count (UInt32), revenue_paise (Int64)
   Note: Uses ReplacingMergeTree — ALWAYS include FINAL modifier.

3. subscription_events
   Columns: merchant_id (String), event_type (String), razorpay_sub_id (String), plan_id (String), customer_id (String), amount_paise (Int64), payment_method (String), interval_type (String), mrr_paise (Int64), event_ts (DateTime, IST)

Rules:
- ALWAYS filter merchant with: merchant_id = {mid:String}
- Monetary values are in paise (1 INR = 100 paise); label columns accordingly
- Add LIMIT 100 if no LIMIT present
- Return ONLY the SQL query — no markdown, no explanation, no code fences
"""

_BRIEF_SYSTEM = """You are a CFO writing a monthly business review for a SaaS company.
Write a concise, investor-quality monthly brief in markdown format based on the provided metrics.
Structure: 1) 2-sentence executive summary, 2) MRR Movement (bullet list with INR amounts), 3) Subscriber Health (churn rate, retention note), 4) What to Watch (1-2 risks or opportunities).
Be specific with numbers. Convert paise to INR (divide by 100). Format INR as ₹X,XXX.
Keep it under 300 words. Use markdown headers (##) and bullet points (-)."""

_CHURN_EMAIL_SYSTEM = """You are a customer success manager writing retention emails.
Given subscriber data, write a personalized, warm retention email.
Return a JSON object with exactly two keys: "subject" (string, max 80 chars) and "body" (string, 3 short paragraphs, plain text, no HTML).
Be specific about the plan/tenure. Offer value, not just discounts. Sound human, not automated."""


# ─── 1. NL Analytics Copilot ─────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
@limiter.limit("10/minute")
def nl_query(
    request: Request,
    body: QueryRequest,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    """Translate a natural-language question into ClickHouse SQL and execute it."""
    if not body.question.strip():
        raise HTTPException(400, "question cannot be empty")

    client = get_client()

    # Step 1: Ask GPT-4o to generate SQL via function calling
    tools = [
        {
            "type": "function",
            "function": {
                "name": "execute_analytics_query",
                "description": "Execute a ClickHouse SQL SELECT query against RazorScope data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "The ClickHouse SQL SELECT query. Must include WHERE merchant_id = {mid:String}",
                        }
                    },
                    "required": ["sql"],
                },
            },
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _NL_SYSTEM},
            {"role": "user", "content": body.question},
        ],
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "execute_analytics_query"}},
        temperature=0,
    )

    tool_call = response.choices[0].message.tool_calls[0]
    args = json.loads(tool_call.function.arguments)
    raw_sql = args.get("sql", "")

    # Step 2: Validate and execute
    safe_sql = _validate_and_prepare_sql(raw_sql, merchant_id)
    try:
        result = clickhouse._ch().query(safe_sql, parameters={"mid": merchant_id})
    except Exception as e:
        raise HTTPException(500, f"Query execution failed: {e}")

    columns = list(result.column_names)
    rows = [list(row) for row in result.result_rows]

    # Step 3: Ask GPT-4o to summarize the result
    summary_resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": (
                    f"Question: {body.question}\n"
                    f"SQL result columns: {columns}\n"
                    f"First 5 rows: {rows[:5]}\n"
                    f"Total rows: {len(rows)}\n\n"
                    "Write one sentence summarizing the key insight from this data. Be specific with numbers."
                ),
            }
        ],
        temperature=0.3,
        max_tokens=100,
    )
    summary = summary_resp.choices[0].message.content.strip()

    return QueryResponse(sql=safe_sql, columns=columns, rows=rows, summary=summary)


# ─── 2. Churn Defender Agent ──────────────────────────────────────────────────

@router.post("/churn-defender/run", response_model=ChurnDefenderResponse)
@limiter.limit("5/minute")
def run_churn_defender(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
):
    """
    Find at-risk subscribers (recent contraction movements), draft a personalized
    retention email for each via GPT-4o, and create a CRM task per subscriber.
    """
    client = get_client()

    # Step 1: Find at-risk subscribers in ClickHouse
    ch_result = clickhouse._ch().query(
        """
        SELECT
            razorpay_sub_id,
            customer_id,
            plan_id,
            argMax(amount_paise, period_month)         AS current_mrr,
            countIf(movement_type = 'contraction')     AS contraction_count,
            min(period_month)                          AS first_seen
        FROM mrr_movements FINAL
        WHERE merchant_id = {mid:String}
          AND period_month >= toDate(now() - INTERVAL 3 MONTH)
        GROUP BY razorpay_sub_id, customer_id, plan_id
        HAVING contraction_count > 0 AND current_mrr > 0
        ORDER BY contraction_count DESC, current_mrr DESC
        LIMIT 10
        """,
        parameters={"mid": merchant_id},
    )

    at_risk = [
        {
            "razorpay_sub_id": row[0],
            "customer_id": row[1],
            "plan_id": row[2],
            "current_mrr_paise": int(row[3]),
            "contraction_count": int(row[4]),
            "first_seen": row[5],
        }
        for row in ch_result.result_rows
    ]

    if not at_risk:
        return ChurnDefenderResponse(found=0, tasks_created=0, previews=[])

    # Step 2: Enrich with customer name/email from Postgres
    enriched = []
    for sub in at_risk:
        customer = postgres.get_customer_by_razorpay_id(merchant_id, sub["customer_id"])
        enriched.append({**sub, **(customer or {"name": "Unknown", "email": ""})})

    # Step 3: Draft retention emails via GPT-4o
    previews: list[ChurnPreview] = []
    tasks_created = 0

    for sub in enriched:
        tenure_months = _months_since(sub.get("first_seen"))
        prompt_data = (
            f"Subscriber: {sub.get('name', 'Unknown')}\n"
            f"Plan: {sub['plan_id']}\n"
            f"Current MRR: ₹{sub['current_mrr_paise'] // 100:,}\n"
            f"Tenure: {tenure_months} months\n"
            f"Downgrades in last 3 months: {sub['contraction_count']}\n"
            f"Email: {sub.get('email', '')}"
        )

        draft_resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _CHURN_EMAIL_SYSTEM},
                {"role": "user", "content": prompt_data},
            ],
            temperature=0.6,
            max_tokens=400,
            response_format={"type": "json_object"},
        )

        try:
            draft = json.loads(draft_resp.choices[0].message.content)
            subject = draft.get("subject", "We'd love to hear from you")
            body = draft.get("body", "")
        except (json.JSONDecodeError, KeyError):
            subject = "Checking in on your subscription"
            body = draft_resp.choices[0].message.content

        # Step 4: Create CRM task with the draft email
        task_title = f"[AI] Retention outreach — {sub.get('name', sub['razorpay_sub_id'])}"
        task_description = f"Subject: {subject}\n\n{body}\n\n---\nSub ID: {sub['razorpay_sub_id']} | Plan: {sub['plan_id']} | MRR: ₹{sub['current_mrr_paise'] // 100:,}"
        postgres.create_task(merchant_id, {
            "title": task_title,
            "description": task_description,
            "lead_id": None,
            "due_date": None,
            "assignee": None,
        })
        tasks_created += 1

        previews.append(ChurnPreview(
            razorpay_sub_id=sub["razorpay_sub_id"],
            customer_name=sub.get("name", "Unknown"),
            customer_email=sub.get("email", ""),
            plan_id=sub["plan_id"],
            current_mrr_paise=sub["current_mrr_paise"],
            contraction_count=sub["contraction_count"],
            draft_subject=subject,
            draft_body=body,
        ))

    return ChurnDefenderResponse(
        found=len(at_risk),
        tasks_created=tasks_created,
        previews=previews,
    )


def _months_since(d: Any) -> int:
    if not d:
        return 0
    try:
        if isinstance(d, date):
            ref = d
        else:
            ref = datetime.fromisoformat(str(d)).date()
        today = date.today()
        return (today.year - ref.year) * 12 + (today.month - ref.month)
    except Exception:
        return 0


# ─── 3. Monthly Brief Generator ───────────────────────────────────────────────

@router.get("/monthly-brief", response_model=MonthlyBriefResponse)
@limiter.limit("5/minute")
def monthly_brief(
    request: Request,
    merchant_id: Annotated[str, Depends(get_merchant_id)],
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="YYYY-MM"),
):
    """
    Pull all metrics for a given month and generate an investor-quality
    narrative brief via GPT-4o.
    """
    try:
        year, mo = int(month[:4]), int(month[5:7])
        month_start = date(year, mo, 1)
    except (ValueError, IndexError):
        raise HTTPException(422, "month must be YYYY-MM format")

    client = get_client()

    # Gather metrics using existing ClickHouse functions
    opening = clickhouse.mrr_opening(merchant_id, month_start)
    movements = clickhouse.mrr_movements_by_type(merchant_id, month_start)
    churn = clickhouse.churn_stats(merchant_id, month_start)
    cohorts = clickhouse.cohort_grid(merchant_id, max_cohort_months=6)

    net_new = sum(movements.values())
    closing = opening + net_new

    # Compute average retention from recent cohorts
    avg_retention_pct = _avg_retention(cohorts)

    metrics_text = f"""Month: {month}

MRR:
- Opening MRR: ₹{opening // 100:,}
- New: ₹{movements.get('new', 0) // 100:,}
- Expansion: ₹{movements.get('expansion', 0) // 100:,}
- Contraction: ₹{movements.get('contraction', 0) // 100:,}
- Churn: ₹{movements.get('churn', 0) // 100:,}
- Reactivation: ₹{movements.get('reactivation', 0) // 100:,}
- Net New MRR: ₹{net_new // 100:,}
- Closing MRR: ₹{closing // 100:,}

Subscriber Activity:
- New subscribers: {churn.get('new_subscribers', 0)}
- Churned subscribers: {churn.get('churned_subscribers', 0)}
- Active at period start: {churn.get('active_at_period_start', 0)}
- Churn MRR lost: ₹{churn.get('churn_mrr_paise', 0) // 100:,}

Retention (avg across last 6 cohorts, month 3): {avg_retention_pct:.1f}%
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _BRIEF_SYSTEM},
            {"role": "user", "content": metrics_text},
        ],
        temperature=0.5,
        max_tokens=500,
    )

    brief_text = response.choices[0].message.content.strip()

    return MonthlyBriefResponse(month=month, brief=brief_text)


def _avg_retention(cohorts: list[dict]) -> float:
    """Average month-3 retention % across available cohorts."""
    month3_rows = [c for c in cohorts if c.get("period_number") == 3 and c.get("cohort_size", 0) > 0]
    if not month3_rows:
        return 0.0
    pcts = [r["retained_count"] / r["cohort_size"] * 100 for r in month3_rows]
    return sum(pcts) / len(pcts)
