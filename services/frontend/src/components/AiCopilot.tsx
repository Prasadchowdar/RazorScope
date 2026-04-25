import { useState } from "react";
import { Copy, Check, Sparkles } from "lucide-react";
import {
  queryAnalytics,
  runChurnDefender,
  generateMonthlyBrief,
  type QueryResponse,
  type AgenticChurnDefenderResponse,
  type AgenticChurnPreview,
} from "../api/agents";
import { useAuth } from "../context/AuthContext";
import RiskBadge from "./RiskBadge";

const inputCls = "w-full rounded-lg px-3 py-2 text-sm bg-[var(--bg-0)] border border-[var(--border-default)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--brand)] focus:border-[var(--brand)] transition-colors";

function currentMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function paise(p: number) {
  return `₹${(p / 100).toLocaleString("en-IN")}`;
}

// ─── NL Analytics Copilot ────────────────────────────────────────────────────

function CopilotCard() {
  const { accessToken } = useAuth();
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!accessToken || !question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await queryAnalytics(accessToken, question.trim());
      setResult(data);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Query failed. Try rephrasing your question.");
    } finally {
      setLoading(false);
    }
  }

  const suggestions = [
    "Show churn by plan last 3 months",
    "Top 5 countries by MRR this year",
    "New vs churned subscribers per month in 2025",
  ];

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-2)] p-6 space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">Ask RazorScope</h3>
        <p className="text-xs text-[var(--text-muted)] mt-0.5">
          Ask anything about your MRR, subscribers, or cohorts in plain English.
        </p>
      </div>

      <form onSubmit={handleAsk} className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What's my churn rate by plan this quarter?"
          className={inputCls}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="shrink-0 rounded-xl px-4 py-2 text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
          style={{ background: "var(--brand)", color: "#020d07" }}
        >
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>

      {!result && !error && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setQuestion(s)}
              className="rounded-full border border-[var(--border-subtle)] bg-[var(--surface-1)] px-3 py-1 text-xs text-[var(--text-secondary)] hover:border-[var(--border-default)] hover:text-[var(--text-primary)] transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {error && <p className="text-sm text-[var(--negative)]">{error}</p>}

      {result && (
        <div className="space-y-3">
          <p className="text-sm text-[var(--brand-2)] italic">{result.summary}</p>

          {result.rows.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border border-[var(--border-subtle)]">
              <table className="w-full text-sm">
                <thead className="bg-[var(--bg-1)] text-[10px] uppercase tracking-[0.06em] text-[var(--text-muted)]">
                  <tr>
                    {result.columns.map((col) => (
                      <th key={col} className="px-4 py-2.5 text-left font-medium">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]">
                  {result.rows.map((row, i) => (
                    <tr key={i} className="hover:bg-[var(--surface-1)] transition-colors">
                      {row.map((cell, j) => (
                        <td key={j} className="px-4 py-2.5 text-xs text-[var(--text-secondary)]">
                          {cell === null ? "—" : String(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-[var(--text-muted)]">No data returned.</p>
          )}

          <details className="text-xs text-[var(--text-muted)]">
            <summary className="cursor-pointer hover:text-[var(--text-secondary)] transition-colors">View SQL</summary>
            <pre className="mt-2 overflow-x-auto rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-1)] p-3 text-xs text-[var(--text-secondary)] font-mono leading-relaxed">
              {result.sql}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}

// ─── Churn Defender ───────────────────────────────────────────────────────────

function ChurnDefenderCard() {
  const { accessToken } = useAuth();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgenticChurnDefenderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  async function handleRun() {
    if (!accessToken) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await runChurnDefender(accessToken);
      setResult(data);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to run Churn Defender.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-2)] p-6 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Churn Defender</h3>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Multi-step AI agent: scores at-risk subscribers, retrieves CRM context, drafts
            personalized retention emails, and creates CRM tasks — replacing your weekly CSM review.
          </p>
        </div>
        <button
          type="button"
          onClick={handleRun}
          disabled={loading}
          className="shrink-0 rounded-xl px-4 py-2 text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
          style={{ background: "var(--negative)", color: "#020d07" }}
        >
          {loading ? "Scanning…" : "Run"}
        </button>
      </div>

      {error && <p className="text-sm text-[var(--negative)]">{error}</p>}

      {result && (
        <div className="space-y-3">
          {result.found === 0 ? (
            <div className="rounded-lg border border-[rgba(52,211,153,0.2)] bg-[var(--positive-dim)] px-4 py-3 text-sm text-[var(--positive)]">
              No at-risk subscribers found in the last 3 months.
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-[var(--negative-dim)] border border-[rgba(248,113,113,0.2)] px-2.5 py-1 text-xs font-medium text-[var(--negative)]">
                  {result.found} at-risk
                </span>
                <span className="rounded-full bg-[var(--positive-dim)] border border-[rgba(52,211,153,0.2)] px-2.5 py-1 text-xs font-medium text-[var(--positive)]">
                  {result.tasks_created} CRM tasks created
                </span>
              </div>
              <div className="space-y-2">
                {result.previews.map((p) => (
                  <ChurnPreviewCard
                    key={p.razorpay_sub_id}
                    preview={p}
                    isExpanded={expanded === p.razorpay_sub_id}
                    onToggle={() =>
                      setExpanded(expanded === p.razorpay_sub_id ? null : p.razorpay_sub_id)
                    }
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function ChurnPreviewCard({
  preview,
  isExpanded,
  onToggle,
}: {
  preview: AgenticChurnPreview;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(`Subject: ${preview.draft_subject}\n\n${preview.draft_body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div className="rounded-lg border border-[var(--border-subtle)] overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[var(--surface-1)] transition-colors"
      >
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-[var(--text-primary)]">{preview.customer_name}</p>
              <RiskBadge score={0} label={preview.risk_label as "high" | "medium" | "low"} />
            </div>
            <p className="text-xs text-[var(--text-muted)]">
              {preview.plan_id} · {paise(preview.current_mrr_paise)}/mo · {preview.tool_calls_made} tool calls
            </p>
          </div>
        </div>
        <span className="text-xs text-[var(--text-muted)]">{isExpanded ? "▲" : "▼"}</span>
      </button>

      {isExpanded && (
        <div className="border-t border-[var(--border-subtle)] bg-[var(--bg-1)] px-4 py-3 space-y-3">
          {preview.draft_subject ? (
            <>
              <p className="text-xs font-semibold text-[var(--text-secondary)]">Subject: {preview.draft_subject}</p>
              <p className="text-xs text-[var(--text-secondary)] whitespace-pre-wrap">{preview.draft_body}</p>
            </>
          ) : (
            <p className="text-xs text-[var(--text-muted)] italic">No email draft generated.</p>
          )}

          {preview.reasoning_steps.length > 0 && (
            <details className="text-xs">
              <summary className="cursor-pointer text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors">
                {preview.tool_calls_made} tool calls · View reasoning trace
              </summary>
              <ol className="mt-2 space-y-1.5 pl-4 list-decimal">
                {preview.reasoning_steps.map((step, i) => (
                  <li key={i} className="text-[var(--text-muted)]">
                    <span className="font-mono text-[var(--brand-2)]">{step.tool_name}</span>
                    <pre className="mt-0.5 overflow-x-auto rounded bg-[var(--bg-0)] px-2 py-1 text-[10px] text-[var(--text-muted)] leading-relaxed">
                      {JSON.stringify(step.tool_input, null, 2)}
                    </pre>
                  </li>
                ))}
              </ol>
            </details>
          )}

          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleCopy}
              disabled={!preview.draft_subject}
              className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors disabled:opacity-40 ${
                copied
                  ? "border-[rgba(52,211,153,0.3)] bg-[var(--positive-dim)] text-[var(--positive)]"
                  : "border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
              }`}
            >
              {copied ? <Check size={11} /> : <Copy size={11} />}
              {copied ? "Copied!" : "Copy email"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Monthly Brief Generator ─────────────────────────────────────────────────

function MonthlyBriefCard() {
  const { accessToken } = useAuth();
  const [month, setMonth] = useState(currentMonth());
  const [loading, setLoading] = useState(false);
  const [brief, setBrief] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!accessToken) return;
    setLoading(true);
    setError(null);
    setBrief(null);
    try {
      const data = await generateMonthlyBrief(accessToken, month);
      setBrief(data.brief);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to generate brief.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    if (!brief) return;
    await navigator.clipboard.writeText(brief);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-2)] p-6 space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">Monthly Brief</h3>
        <p className="text-xs text-[var(--text-muted)] mt-0.5">
          Generate an investor-quality narrative summary of any month's performance — replacing
          the 2-hour founder update ritual.
        </p>
      </div>

      <form onSubmit={handleGenerate} className="flex items-end gap-3">
        <div>
          <label className="block text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--text-muted)] mb-1.5">Month</label>
          <input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="rounded-lg px-3 py-2 text-sm bg-[var(--bg-0)] border border-[var(--border-default)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--brand)] focus:border-[var(--brand)] transition-colors"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !month}
          className="rounded-xl px-4 py-2 text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
          style={{ background: "var(--brand)", color: "#020d07" }}
        >
          {loading ? "Generating…" : "Generate Brief"}
        </button>
      </form>

      {error && <p className="text-sm text-[var(--negative)]">{error}</p>}

      {brief && (
        <div className="space-y-2">
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleCopy}
              className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors ${
                copied
                  ? "border-[rgba(52,211,153,0.3)] bg-[var(--positive-dim)] text-[var(--positive)]"
                  : "border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
              }`}
            >
              {copied ? <Check size={11} /> : <Copy size={11} />}
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          <pre className="whitespace-pre-wrap rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-1)] p-4 text-sm text-[var(--text-secondary)] font-sans leading-relaxed">
            {brief}
          </pre>
        </div>
      )}
    </div>
  );
}

// ─── Main export ─────────────────────────────────────────────────────────────

export default function AiCopilot() {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-[rgba(127,247,203,0.2)] bg-[var(--brand-dim)] px-5 py-4">
        <p className="text-sm text-[var(--brand)]">
          <Sparkles size={14} className="inline mr-1.5 -mt-0.5" />
          <span className="font-semibold">AI Copilot</span> — Three agents that replace real workflows:
          an analyst who writes SQL, a CSM who reviews at-risk subscribers, and a founder who
          writes monthly updates.
        </p>
      </div>
      <CopilotCard />
      <ChurnDefenderCard />
      <MonthlyBriefCard />
    </div>
  );
}
