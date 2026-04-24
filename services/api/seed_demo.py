#!/usr/bin/env python3
"""
Seed demo analytics data for RazorScope.
Inserts 6 months of realistic MRR movements + cohort retention.
Run: docker compose exec api python seed_demo.py
"""
import os, sys
from datetime import date, datetime

import psycopg2, psycopg2.extras
import clickhouse_connect

# ─── Connections ──────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://razorscope_app:app_dev_password@postgres:5432/razorscope")
CH_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CH_USER = os.getenv("CLICKHOUSE_USER", "razorscope")
CH_PASS = os.getenv("CLICKHOUSE_PASSWORD", "razorscope_dev")
CH_DB   = os.getenv("CLICKHOUSE_DB", "razorscope")

NOW = datetime(2026, 4, 24, 10, 0, 0)

# ─── Plans ────────────────────────────────────────────────────────────────────
STARTER    = 99900
GROWTH     = 299900
ENTERPRISE = 999900

# ─── 15 demo customers ────────────────────────────────────────────────────────
# (razorpay_id, name, email, country, payment_method, source)
CUSTOMERS = [
    ("cust_arjun_001",   "Arjun Sharma",   "arjun@techstartup.in",    "IN", "upi_autopay", "organic"),
    ("cust_priya_002",   "Priya Patel",    "priya@designstudio.co",   "IN", "card",        "google_ads"),
    ("cust_rohit_003",   "Rohit Mehta",    "rohit@saastools.io",      "IN", "nach",        "referral"),
    ("cust_anjali_004",  "Anjali Singh",   "anjali@ecommerceapp.com", "IN", "upi_autopay", "organic"),
    ("cust_vikram_005",  "Vikram Nair",    "vikram@fintech.in",       "IN", "card",        "google_ads"),
    ("cust_deepa_006",   "Deepa Krishnan", "deepa@hrplatform.co",     "SG", "card",        "organic"),
    ("cust_saurabh_007", "Saurabh Joshi",  "saurabh@edtech.in",       "IN", "upi_autopay", "referral"),
    ("cust_meera_008",   "Meera Iyer",     "meera@healthapp.io",      "IN", "upi_autopay", "organic"),
    ("cust_rajesh_009",  "Rajesh Gupta",   "rajesh@logistics.com",    "IN", "nach",        "google_ads"),
    ("cust_kavita_010",  "Kavita Desai",   "kavita@retailtech.in",    "US", "card",        "referral"),
    ("cust_amit_011",    "Amit Bose",      "amit@cloudtools.co",      "IN", "upi_autopay", "organic"),
    ("cust_neha_012",    "Neha Rao",       "neha@mediatech.in",       "IN", "card",        "google_ads"),
    ("cust_suresh_013",  "Suresh Pillai",  "suresh@autotech.io",      "IN", "nach",        "organic"),
    ("cust_pooja_014",   "Pooja Agarwal",  "pooja@eduplatform.com",   "IN", "upi_autopay", "google_ads"),
    ("cust_kiran_015",   "Kiran Kumar",    "kiran@iotsolutions.in",   "IN", "card",        "referral"),
]
CUST = {c[0]: c for c in CUSTOMERS}

# ─── MRR movements ────────────────────────────────────────────────────────────
# (period_month, movement_type, razorpay_sub_id, customer_id, plan_id, amount, prev_amount, voluntary)
MOVEMENTS = [
    # Nov 2025 — cohort 1: 10 new subscribers
    (date(2025,11,1), "new",         "sub_arjun_001",   "cust_arjun_001",   "plan_growth",      GROWTH,      0,      0),
    (date(2025,11,1), "new",         "sub_priya_002",   "cust_priya_002",   "plan_starter",     STARTER,     0,      0),
    (date(2025,11,1), "new",         "sub_rohit_003",   "cust_rohit_003",   "plan_enterprise",  ENTERPRISE,  0,      0),
    (date(2025,11,1), "new",         "sub_anjali_004",  "cust_anjali_004",  "plan_growth",      GROWTH,      0,      0),
    (date(2025,11,1), "new",         "sub_vikram_005",  "cust_vikram_005",  "plan_starter",     STARTER,     0,      0),
    (date(2025,11,1), "new",         "sub_deepa_006",   "cust_deepa_006",   "plan_growth",      GROWTH,      0,      0),
    (date(2025,11,1), "new",         "sub_saurabh_007", "cust_saurabh_007", "plan_enterprise",  ENTERPRISE,  0,      0),
    (date(2025,11,1), "new",         "sub_meera_008",   "cust_meera_008",   "plan_starter",     STARTER,     0,      0),
    (date(2025,11,1), "new",         "sub_rajesh_009",  "cust_rajesh_009",  "plan_starter",     STARTER,     0,      0),
    (date(2025,11,1), "new",         "sub_kavita_010",  "cust_kavita_010",  "plan_growth",      GROWTH,      0,      0),

    # Dec 2025 — cohort 2: 3 new subscribers
    (date(2025,12,1), "new",         "sub_amit_011",    "cust_amit_011",    "plan_starter",     STARTER,     0,      0),
    (date(2025,12,1), "new",         "sub_pooja_014",   "cust_pooja_014",   "plan_growth",      GROWTH,      0,      0),
    (date(2025,12,1), "new",         "sub_kiran_015",   "cust_kiran_015",   "plan_enterprise",  ENTERPRISE,  0,      0),

    # Jan 2026 — 2 expansions + 1 voluntary churn
    (date(2026,1,1),  "expansion",   "sub_priya_002",   "cust_priya_002",   "plan_growth",      GROWTH,      STARTER, 0),
    (date(2026,1,1),  "expansion",   "sub_vikram_005",  "cust_vikram_005",  "plan_growth",      GROWTH,      STARTER, 0),
    (date(2026,1,1),  "churn",       "sub_amit_011",    "cust_amit_011",    "plan_starter",     0,           STARTER, 1),

    # Feb 2026 — 2 new + 1 involuntary churn + 2 contractions (AT-RISK)
    (date(2026,2,1),  "new",         "sub_neha_012",    "cust_neha_012",    "plan_growth",      GROWTH,      0,      0),
    (date(2026,2,1),  "new",         "sub_suresh_013",  "cust_suresh_013",  "plan_enterprise",  ENTERPRISE,  0,      0),
    (date(2026,2,1),  "churn",       "sub_rohit_003",   "cust_rohit_003",   "plan_enterprise",  0,           ENTERPRISE, 0),
    (date(2026,2,1),  "contraction", "sub_arjun_001",   "cust_arjun_001",   "plan_starter",     STARTER,     GROWTH,  0),
    (date(2026,2,1),  "contraction", "sub_deepa_006",   "cust_deepa_006",   "plan_starter",     STARTER,     GROWTH,  0),

    # Mar 2026 — reactivation + expansion + contraction (AT-RISK)
    (date(2026,3,1),  "reactivation","sub_amit_011",    "cust_amit_011",    "plan_starter",     STARTER,     0,      0),
    (date(2026,3,1),  "expansion",   "sub_rajesh_009",  "cust_rajesh_009",  "plan_growth",      GROWTH,      STARTER, 0),
    (date(2026,3,1),  "contraction", "sub_pooja_014",   "cust_pooja_014",   "plan_starter",     STARTER,     GROWTH,  0),

    # Apr 2026 — expansion + voluntary churn
    (date(2026,4,1),  "expansion",   "sub_meera_008",   "cust_meera_008",   "plan_growth",      GROWTH,      STARTER, 0),
    (date(2026,4,1),  "churn",       "sub_anjali_004",  "cust_anjali_004",  "plan_growth",      0,           GROWTH,  1),
]

# ─── Cohort retention (precomputed) ──────────────────────────────────────────
# (cohort_month, period_month, period_number, cohort_size, retained_count, revenue_paise)
COHORTS = [
    # Nov 2025 cohort (10 customers)
    (date(2025,11,1), date(2025,11,1), 0, 10, 10, 3_599_000),
    (date(2025,11,1), date(2025,12,1), 1, 10, 10, 3_599_000),
    (date(2025,11,1), date(2026, 1,1), 2, 10, 10, 3_998_000),  # 2 upgrades
    (date(2025,11,1), date(2026, 2,1), 3, 10,  9, 2_599_100),  # rohit churned, 2 contracted
    (date(2025,11,1), date(2026, 3,1), 4, 10,  9, 2_799_100),  # rajesh expanded
    (date(2025,11,1), date(2026, 4,1), 5, 10,  8, 2_499_200),  # anjali churned, meera expanded

    # Dec 2025 cohort (3 customers: amit, pooja, kiran)
    (date(2025,12,1), date(2025,12,1), 0,  3,  3, 1_399_700),
    (date(2025,12,1), date(2026, 1,1), 1,  3,  2, 1_299_800),  # amit churned
    (date(2025,12,1), date(2026, 2,1), 2,  3,  2, 1_299_800),
    (date(2025,12,1), date(2026, 3,1), 3,  3,  3, 1_199_700),  # amit reactivated, pooja contracted
    (date(2025,12,1), date(2026, 4,1), 4,  3,  3, 1_199_700),

    # Feb 2026 cohort (2 customers: neha, suresh)
    (date(2026, 2,1), date(2026, 2,1), 0,  2,  2, 1_299_800),
    (date(2026, 2,1), date(2026, 3,1), 1,  2,  2, 1_299_800),
    (date(2026, 2,1), date(2026, 4,1), 2,  2,  2, 1_299_800),
]


def seed_postgres(merchant_id: str):
    conn = psycopg2.connect(DATABASE_URL)
    inserted = 0
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL app.current_merchant_id = %s", (merchant_id,))
            for razorpay_id, name, email, country, _pm, _src in CUSTOMERS:
                cur.execute(
                    """
                    INSERT INTO customers (merchant_id, razorpay_customer_id, name, email)
                    VALUES (%s::uuid, %s, %s, %s)
                    ON CONFLICT (merchant_id, razorpay_customer_id) DO NOTHING
                    """,
                    (merchant_id, razorpay_id, name, email),
                )
                inserted += cur.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(f"  Postgres: {inserted} customers inserted")


def seed_clickhouse(merchant_id: str, ch):
    # Check if already seeded (look for our specific sub_ids)
    result = ch.query(
        "SELECT count() FROM mrr_movements WHERE merchant_id = {mid:String} AND razorpay_sub_id = 'sub_arjun_001'",
        parameters={"mid": merchant_id},
    )
    existing = result.first_row[0]
    if existing > 0:
        print(f"  ClickHouse: demo data already present — skipping")
        return

    # Insert mrr_movements
    mv_cols = [
        "merchant_id", "period_month", "movement_type", "razorpay_sub_id",
        "customer_id", "plan_id", "amount_paise", "prev_amount_paise", "delta_paise",
        "voluntary", "country", "source", "payment_method", "computed_at", "updated_at",
    ]
    mv_rows = []
    for period, mtype, sub_id, cust_id, plan_id, amount, prev, voluntary in MOVEMENTS:
        c = CUST[cust_id]
        mv_rows.append([
            merchant_id, period, mtype, sub_id,
            cust_id, plan_id, amount, prev, amount - prev,
            voluntary, c[3], c[5], c[4], NOW, NOW,
        ])
    ch.insert("mrr_movements", mv_rows, column_names=mv_cols)
    print(f"  ClickHouse: {len(mv_rows)} movement rows inserted")

    # Insert cohort_retention
    cr_cols = [
        "merchant_id", "cohort_month", "period_month", "period_number",
        "cohort_size", "retained_count", "revenue_paise", "updated_at",
    ]
    cr_rows = [
        [merchant_id, cohort_m, period_m, period_n, size, retained, revenue, NOW]
        for cohort_m, period_m, period_n, size, retained, revenue in COHORTS
    ]
    ch.insert("cohort_retention", cr_rows, column_names=cr_cols)
    print(f"  ClickHouse: {len(cr_rows)} cohort retention rows inserted")


def main():
    print("Connecting to Postgres...")
    pg = psycopg2.connect(DATABASE_URL)
    with pg.cursor() as cur:
        # Use most recently created real merchant (skip old dev/test accounts)
        cur.execute(
            "SELECT id FROM merchants WHERE deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
    pg.close()

    if not row:
        print("ERROR: No merchant found. Register an account first at http://localhost:3001")
        sys.exit(1)

    merchant_id = str(row[0])
    print(f"Seeding merchant: {merchant_id}")

    print("Seeding Postgres customers...")
    seed_postgres(merchant_id)

    print("Connecting to ClickHouse...")
    ch = clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT,
        username=CH_USER, password=CH_PASS,
        database=CH_DB,
    )

    print("Seeding ClickHouse analytics...")
    seed_clickhouse(merchant_id, ch)

    print()
    print("Done! Open the AI tab and try:")
    print("  Ask: 'Show MRR by plan for last 6 months'")
    print("  Ask: 'Which subscribers churned in 2026?'")
    print("  Churn Defender: should find 3 at-risk subscribers")
    print("  Monthly Brief: generate for 2026-03 or 2026-04")


if __name__ == "__main__":
    main()
