interface StatCardProps {
  label: string;
  valuePaise: number;
  positive?: boolean;
  trend?: number;
}

function formatRupees(paise: number): string {
  const rupees = paise / 100;
  if (Math.abs(rupees) >= 1_00_000) {
    return `₹${(rupees / 1_00_000).toFixed(2)}L`;
  }
  return `₹${rupees.toLocaleString("en-IN")}`;
}

export default function StatCard({ label, valuePaise, positive, trend }: StatCardProps) {
  const valueColor =
    positive === undefined
      ? "var(--text-primary)"
      : valuePaise >= 0
      ? "var(--positive)"
      : "var(--negative)";

  const trendPositive = trend !== undefined && trend >= 0;

  return (
    <div
      className="rounded-xl p-5 transition-colors"
      style={{
        background: "var(--bg-2)",
        border: "1px solid var(--border-subtle)",
      }}
    >
      <p
        className="text-[10px] font-semibold uppercase tracking-[0.06em] mb-3"
        style={{ color: "var(--text-muted)" }}
      >
        {label}
      </p>
      <p
        className="text-2xl font-semibold tabular"
        style={{ color: valueColor }}
      >
        {formatRupees(valuePaise)}
      </p>
      {trend !== undefined && (
        <div className="mt-2 flex items-center gap-1.5">
          <span
            className="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
            style={{
              background: trendPositive ? "var(--positive-dim)" : "var(--negative-dim)",
              color: trendPositive ? "var(--positive)" : "var(--negative)",
            }}
          >
            {trendPositive ? "+" : ""}{trend.toFixed(1)}% vs last month
          </span>
        </div>
      )}
    </div>
  );
}
