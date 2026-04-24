import Badge from "./Badge";
import type { BenchmarkItem } from "../api/benchmarks";

function fmt(value: number, unit: BenchmarkItem["unit"]): string {
  if (unit === "pct") return `${value.toFixed(1)}%`;
  if (unit === "months") return `${value.toFixed(1)} mo`;
  const rupees = value / 100;
  if (rupees >= 1_00_000) return `₹${(rupees / 1_00_000).toFixed(1)}L`;
  if (rupees >= 1000) return `₹${(rupees / 1000).toFixed(1)}K`;
  return `₹${rupees.toFixed(0)}`;
}

type BadgeVariant = "positive" | "negative" | "warning" | "brand2" | "neutral";

const LABEL_VARIANT: Record<string, BadgeVariant> = {
  "top quartile":    "positive",
  "above median":    "brand2",
  "below median":    "warning",
  "bottom quartile": "negative",
};

const BAND_COLORS = [
  "rgba(248,113,113,0.18)",
  "rgba(251,191,36,0.18)",
  "rgba(52,211,153,0.12)",
  "rgba(52,211,153,0.25)",
];

interface BenchmarkCardProps {
  item: BenchmarkItem;
}

function BenchmarkCard({ item }: BenchmarkCardProps) {
  const pct = Math.min(100, Math.max(0, item.percentile));

  return (
    <div className="rounded-xl p-5 bg-[var(--bg-2)] border border-[var(--border-subtle)] hover:border-[var(--border-default)] transition-colors">
      <div className="flex justify-between items-start mb-1 gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-[var(--text-primary)] leading-tight truncate">{item.name}</p>
          <p className="text-xs text-[var(--text-muted)] mt-0.5 leading-tight">{item.description}</p>
        </div>
        <Badge variant={LABEL_VARIANT[item.label] ?? "neutral"} className="shrink-0 mt-0.5">
          {item.label}
        </Badge>
      </div>

      <div className="mt-4 mb-1">
        <p className="text-2xl font-bold tabular text-[var(--text-primary)]">
          {fmt(item.merchant_value, item.unit)}
        </p>
        <p className="text-xs text-[var(--text-muted)] mt-0.5">
          {item.percentile.toFixed(0)}th percentile
        </p>
      </div>

      {/* Percentile ruler */}
      <div className="mt-3 relative">
        <div className="flex h-2.5 rounded-full overflow-hidden gap-px">
          {BAND_COLORS.map((color, i) => (
            <div key={i} className="flex-1 rounded-sm" style={{ backgroundColor: color }} />
          ))}
        </div>
        {/* Marker */}
        <div
          className="benchmark-marker absolute top-0 w-0.5 h-2.5 rounded-full"
          style={{
            left: `${pct}%`,
            transform: "translateX(-50%)",
            background: "#fff",
            boxShadow: "0 0 6px rgba(255,255,255,0.7)",
          }}
        />
      </div>

      {/* Axis labels */}
      <div className="flex justify-between text-[10px] text-[var(--text-muted)] mt-2">
        <span>P10: {fmt(item.industry_p10, item.unit)}</span>
        <span>P50: {fmt(item.industry_p50, item.unit)}</span>
        <span>P90: {fmt(item.industry_p90, item.unit)}</span>
      </div>

      <p className="text-[10px] text-[var(--text-muted)] mt-1 text-right">
        {item.direction === "higher" ? "↑ higher is better" : "↓ lower is better"}
      </p>
    </div>
  );
}

interface Props {
  items: BenchmarkItem[];
  dataSource: string;
}

export default function BenchmarkGauge({ items, dataSource }: Props) {
  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((item) => (
          <BenchmarkCard key={item.metric_key} item={item} />
        ))}
      </div>
      <p className="text-[10px] text-[var(--text-muted)] mt-4 text-right">Source: {dataSource}</p>
    </div>
  );
}
