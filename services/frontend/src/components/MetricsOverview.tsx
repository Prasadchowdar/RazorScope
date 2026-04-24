import type { MetricsOverview } from "../api/metrics";

interface Props {
  data: MetricsOverview;
}

function fmtRupees(paise: number) {
  const r = paise / 100;
  if (Math.abs(r) >= 1_00_000) return `₹${(r / 1_00_000).toFixed(2)}L`;
  return `₹${r.toLocaleString("en-IN")}`;
}

function fmtRate(r: number) {
  return `${r.toFixed(1)}%`;
}

interface KpiCardProps {
  label: string;
  value: string;
  sub?: string;
  highlight?: "good" | "bad" | "neutral";
  glow?: boolean;
}

function KpiCard({ label, value, sub, highlight = "neutral", glow = false }: KpiCardProps) {
  const accentColor =
    highlight === "good"  ? "var(--positive)"
    : highlight === "bad" ? "var(--negative)"
    : "var(--text-primary)";

  const badgeStyle =
    highlight === "good"
      ? { background: "var(--positive-dim)", color: "var(--positive)" }
      : highlight === "bad"
      ? { background: "var(--negative-dim)", color: "var(--negative)" }
      : null;

  return (
    <div
      className="rounded-xl p-4 transition-colors"
      style={{
        background: glow ? "rgba(52,211,153,0.06)" : "var(--bg-2)",
        border: glow ? "1px solid rgba(52,211,153,0.25)" : "1px solid var(--border-subtle)",
      }}
    >
      <div className="flex items-start justify-between mb-2 gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-muted)] leading-tight">
          {label}
        </p>
        {badgeStyle && (
          <span
            className="text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0"
            style={badgeStyle}
          >
            {highlight === "good" ? "↑" : "↓"}
          </span>
        )}
      </div>
      <p className="text-2xl font-semibold tabular" style={{ color: accentColor }}>
        {value}
      </p>
      {sub && (
        <p className="text-xs mt-1 text-[var(--text-muted)]">{sub}</p>
      )}
    </div>
  );
}

export default function MetricsOverviewPanel({ data }: Props) {
  const nrrGood = data.nrr_pct >= 100;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard label="Active Subscribers" value={String(data.active_subscribers)} />
        <KpiCard
          label="New This Month"
          value={`+${data.new_subscribers}`}
          highlight="good"
        />
        <KpiCard
          label="Churned This Month"
          value={`-${data.churned_subscribers}`}
          highlight={data.churned_subscribers > 0 ? "bad" : "neutral"}
        />
        <KpiCard
          label="Reactivated"
          value={`+${data.reactivated_subscribers}`}
          highlight={data.reactivated_subscribers > 0 ? "good" : "neutral"}
        />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard label="ARPU" value={fmtRupees(data.arpu_paise)} sub="per active sub" />
        <KpiCard
          label="Customer Churn"
          value={fmtRate(data.customer_churn_rate)}
          highlight={data.customer_churn_rate > 5 ? "bad" : data.customer_churn_rate > 2 ? "neutral" : "good"}
        />
        <KpiCard
          label="Revenue Churn"
          value={fmtRate(data.revenue_churn_rate)}
          highlight={data.revenue_churn_rate > 5 ? "bad" : "neutral"}
        />
        <KpiCard
          label="NRR"
          value={`${data.nrr_pct.toFixed(1)}%`}
          highlight={nrrGood ? "good" : "bad"}
          sub={nrrGood ? "expansion > churn ✓" : "churn > expansion"}
          glow={nrrGood}
        />
        <KpiCard
          label="LTV"
          value={data.ltv_months != null ? `${data.ltv_months}mo` : "—"}
          sub="avg subscription life"
        />
        <KpiCard
          label="Closing MRR"
          value={fmtRupees(data.closing_mrr_paise)}
          highlight={data.closing_mrr_paise >= data.opening_mrr_paise ? "good" : "bad"}
        />
      </div>
    </div>
  );
}
