interface TooltipEntry {
  dataKey?: string | number;
  name?: string | number;
  value?: number;
  color?: string;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipEntry[];
  label?: string | number;
  formatValue?: (v: number) => string;
  showNet?: boolean;
}

function formatINR(paise: number): string {
  const rupees = Math.abs(paise) / 100;
  if (rupees >= 100000) return `₹${(rupees / 100000).toFixed(1)}L`;
  if (rupees >= 1000) return `₹${(rupees / 1000).toFixed(1)}K`;
  return `₹${rupees.toFixed(0)}`;
}

export default function ChartTooltip({ active, payload, label, formatValue, showNet = false }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  const fmt = formatValue ?? formatINR;

  const positiveKeys = ["new", "expansion", "reactivation"];
  const netValue = showNet
    ? payload.reduce((sum, p) => {
        const val = (p.value as number) ?? 0;
        return positiveKeys.includes(p.dataKey as string) ? sum + val : sum + val;
      }, 0)
    : null;

  return (
    <div style={{
      background: "rgba(13,23,38,0.96)",
      border: "1px solid rgba(255,255,255,0.10)",
      borderRadius: "10px",
      padding: "10px 14px",
      backdropFilter: "blur(16px)",
      boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
      minWidth: "160px",
    }}>
      <p style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "8px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
        {label}
      </p>
      {payload.map((p, i) => (
        <div key={String(p.dataKey ?? p.name ?? i)} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "20px", marginBottom: "4px" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#94a3b8", fontSize: "12px" }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, backgroundColor: p.color, display: "inline-block", flexShrink: 0 }} />
            {String(p.dataKey ?? p.name)}
          </span>
          <span style={{ color: "#e8f0fe", fontSize: "12px", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
            {fmt((p.value as number) ?? 0)}
          </span>
        </div>
      ))}
      {showNet && netValue !== null && (
        <>
          <div style={{ borderTop: "1px solid rgba(255,255,255,0.08)", marginTop: "6px", paddingTop: "6px", display: "flex", justifyContent: "space-between", gap: "20px" }}>
            <span style={{ color: "#e8f0fe", fontSize: "12px", fontWeight: 600 }}>Net</span>
            <span style={{
              color: netValue >= 0 ? "#34d399" : "#f87171",
              fontSize: "12px",
              fontWeight: 700,
              fontVariantNumeric: "tabular-nums",
            }}>
              {netValue >= 0 ? "+" : ""}{fmt(netValue)}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
