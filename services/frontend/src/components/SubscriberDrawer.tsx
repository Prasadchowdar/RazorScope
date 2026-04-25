import { useEffect, useState } from "react";
import { X } from "lucide-react";
import type { SubscriberDetail, RiskScore } from "../api/subscribers";
import { fetchSubscriber, fetchRiskScores } from "../api/subscribers";
import Badge from "./Badge";
import RiskBadge from "./RiskBadge";
import { useAuth } from "../context/AuthContext";

type BadgeVariant = "positive" | "negative" | "warning" | "brand" | "neutral";

const TYPE_VARIANT: Record<string, BadgeVariant> = {
  new:          "positive",
  expansion:    "positive",
  reactivation: "brand",
  contraction:  "warning",
  churn:        "negative",
};

function fmtRupees(paise: number) {
  const sign = paise >= 0 ? "+" : "";
  return `${sign}₹${(paise / 100).toLocaleString("en-IN")}`;
}

interface Props {
  subId: string | null;
  onClose: () => void;
}

export default function SubscriberDrawer({ subId, onClose }: Props) {
  const { accessToken } = useAuth();
  const [detail, setDetail] = useState<SubscriberDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [riskScore, setRiskScore] = useState<RiskScore | null>(null);

  useEffect(() => {
    if (!subId || !accessToken) return;
    setDetail(null);
    setError(null);
    setRiskScore(null);
    setLoading(true);
    fetchSubscriber(accessToken, subId)
      .then(setDetail)
      .catch(() => setError("Failed to load subscriber details."))
      .finally(() => setLoading(false));
    fetchRiskScores(accessToken, 200)
      .then(({ scores }) => setRiskScore(scores.find((s) => s.razorpay_sub_id === subId) ?? null))
      .catch(() => {});
  }, [accessToken, subId]);

  if (!subId) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm" onClick={onClose} />

      <div
        className="fixed right-0 top-0 h-full w-full max-w-md z-50 flex flex-col border-l border-[var(--border-subtle)] shadow-2xl"
        style={{ background: "var(--bg-1)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-subtle)]">
          <div>
            <div className="flex items-center gap-2">
              <p className="text-xs font-mono text-[var(--brand-2)]">{subId}</p>
              {riskScore && <RiskBadge score={riskScore.risk_score} label={riskScore.risk_label} showScore />}
            </div>
            {detail && (
              <p className="text-xs text-[var(--text-muted)] mt-0.5">
                {detail.customer_id} · {detail.plan_id}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="w-7 h-7 flex items-center justify-center rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-2)] transition-colors"
          >
            <X size={15} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading && (
            <div className="space-y-3 mt-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-8 rounded-lg animate-pulse bg-[var(--surface-1)]" />
              ))}
            </div>
          )}
          {error && (
            <p className="text-sm text-[var(--negative)] text-center mt-10">{error}</p>
          )}
          {detail && (
            <>
              {/* Risk factors */}
              {riskScore && riskScore.factors.length > 0 && (
                <div className="mb-5 p-4 rounded-xl bg-[var(--bg-2)] border border-[var(--border-subtle)]">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-muted)] mb-2">
                    Risk Factors
                  </p>
                  <ul className="space-y-1">
                    {riskScore.factors.map((f) => (
                      <li key={f} className="text-xs text-[var(--negative)] flex items-center gap-1.5">
                        <span className="w-1 h-1 rounded-full bg-[var(--negative)] shrink-0" />
                        {f.replace(/_/g, " ")}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Current MRR */}
              <div className="mb-5 p-4 rounded-xl bg-[var(--bg-2)] border border-[var(--border-subtle)]">
                <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-muted)]">
                  Current MRR Contribution
                </p>
                <p className="text-2xl font-bold tabular text-[var(--text-primary)] mt-1">
                  ₹{(detail.current_amount_paise / 100).toLocaleString("en-IN")}
                </p>
              </div>

              {/* Timeline */}
              <h3 className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-muted)] mb-3">
                Movement History
              </h3>
              <ol className="relative border-l border-[var(--border-subtle)] ml-2 space-y-5">
                {detail.timeline.map((entry, i) => (
                  <li key={i} className="ml-4">
                    <div
                      className="absolute -left-1.5 w-3 h-3 rounded-full border-2"
                      style={{
                        backgroundColor: "var(--bg-1)",
                        borderColor: "var(--border-default)",
                      }}
                    />
                    <p className="text-[10px] text-[var(--text-muted)] mb-0.5">{entry.period_month}</p>
                    <div className="flex items-center gap-2 mb-0.5">
                      <Badge variant={TYPE_VARIANT[entry.movement_type] ?? "neutral"}>
                        {entry.movement_type}
                      </Badge>
                      <span
                        className="text-sm font-semibold tabular"
                        style={{ color: entry.delta_paise >= 0 ? "var(--positive)" : "var(--negative)" }}
                      >
                        {fmtRupees(entry.delta_paise)}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-muted)]">
                      MRR: ₹{(entry.amount_paise / 100).toLocaleString("en-IN")}
                    </p>
                  </li>
                ))}
              </ol>
            </>
          )}
        </div>
      </div>
    </>
  );
}
