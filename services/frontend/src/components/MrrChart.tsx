import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { TrendMonth } from "../api/mrr";
import ChartTooltip from "./ChartTooltip";

interface Props {
  data: TrendMonth[];
}

const MOVEMENT_COLORS: Record<string, string> = {
  new:          "#34d399",
  expansion:    "#6ee7b7",
  reactivation: "#7ff7cb",
  contraction:  "#fbbf24",
  churn:        "#f87171",
};

function toRupees(paise: number) {
  return paise / 100;
}

function fmtAxis(v: number) {
  if (Math.abs(v) >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
  if (Math.abs(v) >= 1000) return `₹${(v / 1000).toFixed(0)}k`;
  return `₹${v}`;
}

export default function MrrChart({ data }: Props) {
  const chartData = data.map((m) => ({
    month: m.month,
    new:          toRupees(m.movements.new ?? 0),
    expansion:    toRupees(m.movements.expansion ?? 0),
    reactivation: toRupees(m.movements.reactivation ?? 0),
    contraction:  toRupees(m.movements.contraction ?? 0),
    churn:        toRupees(m.movements.churn ?? 0),
    closing:      toRupees(m.closing_mrr_paise),
  }));

  return (
    <div
      className="rounded-xl p-6"
      style={{ background: "var(--bg-2)", border: "1px solid var(--border-subtle)" }}
    >
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          MRR Movements
        </h2>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          12-month trend
        </span>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis
            dataKey="month"
            tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={fmtAxis}
            tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={56}
          />
          <Tooltip
            content={<ChartTooltip showNet />}
            cursor={{ fill: "rgba(255,255,255,0.03)" }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, color: "#64748b", paddingTop: 12 }}
          />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeDasharray="3 3" />
          {Object.entries(MOVEMENT_COLORS).map(([key, color], i) => (
            <Bar
              key={key}
              dataKey={key}
              stackId="movements"
              fill={color}
              name={key}
              animationBegin={i * 80}
              animationDuration={500}
              animationEasing="ease-out"
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
