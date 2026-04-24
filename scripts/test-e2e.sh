#!/usr/bin/env bash
# End-to-end pipeline test.
#
# Path verified: webhook POST → Kafka → metric-worker → mrr_movements (ClickHouse)
#
# Requires only: bash, curl, openssl (no Python on host)
# All heavy lifting is done by running Docker services.
set -euo pipefail

WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:8080}"
MERCHANT_ID="${DEV_MERCHANT_ID:-11111111-1111-1111-1111-111111111111}"
WEBHOOK_SECRET="${DEV_WEBHOOK_SECRET:-whsec_dev_test_secret}"
CH_HOST="${CLICKHOUSE_HOST:-localhost}"
CH_PORT="${CLICKHOUSE_HTTP_PORT:-8123}"
CH_USER="${CLICKHOUSE_USER:-razorscope}"
CH_PASS="${CLICKHOUSE_PASSWORD:-razorscope_dev}"
CH_DB="${CLICKHOUSE_DB:-razorscope}"

echo "=== RazorScope E2E Test ==="

# ─── Step 1: Build payload with a unique sub_id (guarantees "new" movement) ──
# Use nanosecond timestamp to avoid collision with previous test runs.
TS=$(date +%s)
SUB_ID="sub_e2e_${TS}"
PAY_ID="pay_e2e_${TS}"

PAYLOAD=$(cat <<EOF
{
  "entity": "event",
  "account_id": "acc_dev_test",
  "event": "subscription.charged",
  "contains": ["payment", "subscription"],
  "created_at": ${TS},
  "payload": {
    "payment": {
      "entity": {
        "id": "${PAY_ID}",
        "entity": "payment",
        "amount": 299900,
        "currency": "INR",
        "status": "captured",
        "method": "upi",
        "vpa": "test@upi",
        "customer_id": "cust_e2e_${TS}",
        "recurring": true,
        "recurring_type": "auto",
        "created_at": ${TS}
      }
    },
    "subscription": {
      "entity": {
        "id": "${SUB_ID}",
        "entity": "subscription",
        "plan_id": "plan_growth_monthly",
        "customer_id": "cust_e2e_${TS}",
        "status": "active",
        "current_start": ${TS},
        "current_end": $((TS + 2592000)),
        "paid_count": 1,
        "created_at": ${TS}
      }
    }
  }
}
EOF
)

# ─── Step 2: Sign and POST ────────────────────────────────────────────────────
SIGNATURE=$(printf '%s' "${PAYLOAD}" | openssl dgst -sha256 -hmac "${WEBHOOK_SECRET}" | awk '{print $2}')
echo "Posting sub_id=${SUB_ID}"

HTTP_CODE=$(curl -s -o /tmp/e2e_response.json -w "%{http_code}" \
  -X POST "${WEBHOOK_URL}/v1/webhooks/razorpay/${MERCHANT_ID}" \
  -H "Content-Type: application/json" \
  -H "X-Razorpay-Signature: ${SIGNATURE}" \
  -d "${PAYLOAD}")

echo "  Webhook → HTTP ${HTTP_CODE} $(cat /tmp/e2e_response.json)"

if [ "${HTTP_CODE}" != "200" ]; then
  echo "FAIL: webhook receiver returned ${HTTP_CODE}"
  exit 1
fi

# ─── Step 3: Poll mrr_movements until sub_id appears (metric-worker path) ────
echo "Waiting for metric-worker to write mrr_movements (up to 20s)..."
for i in $(seq 1 40); do
  COUNT=$(curl -sf \
    "http://${CH_HOST}:${CH_PORT}/?database=${CH_DB}&query=SELECT+count()+FROM+mrr_movements+WHERE+razorpay_sub_id%3D'${SUB_ID}'" \
    -u "${CH_USER}:${CH_PASS}" 2>/dev/null || echo "0")
  COUNT=$(echo "$COUNT" | tr -d '[:space:]')
  if [ "${COUNT:-0}" -ge 1 ] 2>/dev/null; then
    ELAPSED=$(( i * 500 ))
    echo ""
    echo "SUCCESS: mrr_movement found after ~${ELAPSED}ms"
    echo "  sub_id=${SUB_ID}"
    echo "=== E2E PASSED ==="
    exit 0
  fi
  printf "."
  sleep 0.5
done

echo ""
echo "FAIL: mrr_movement for ${SUB_ID} not found within 20s"
echo "Check: docker compose logs metric-worker --tail 30"
exit 1
