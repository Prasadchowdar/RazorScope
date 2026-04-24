import { Key, XCircle, UserPlus, Trash2, ArrowRight, RefreshCw, ClipboardList } from "lucide-react";
import { useAuditLog } from "../hooks/useSecurity";
import Badge from "./Badge";
import type { AuditEntry } from "../api/security";

type BadgeVariant = "positive" | "negative" | "neutral";

function getActionMeta(action: string): { icon: React.ElementType; variant: BadgeVariant } {
  if (action.includes("revoked") || action.includes("deleted"))
    return { icon: XCircle, variant: "negative" };
  if (action.includes("created"))
    return { icon: action.includes("key") ? Key : UserPlus, variant: "positive" };
  if (action.includes("deleted"))
    return { icon: Trash2, variant: "negative" };
  if (action.includes("stage_change"))
    return { icon: ArrowRight, variant: "neutral" };
  return { icon: ClipboardList, variant: "neutral" };
}

function relTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function AuditLog() {
  const log = useAuditLog(50);

  return (
    <div className="rounded-xl overflow-hidden bg-[var(--bg-2)] border border-[var(--border-subtle)]">
      <div className="px-6 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Audit Log</h2>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">Recent security and data events</p>
        </div>
        <button
          type="button"
          onClick={() => log.refetch()}
          aria-label="Refresh"
          className="w-7 h-7 flex items-center justify-center rounded-lg text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--surface-1)] transition-colors"
        >
          <RefreshCw size={13} />
        </button>
      </div>

      <div className="divide-y divide-[var(--border-subtle)]">
        {log.isPending ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="px-6 py-3 flex gap-3 items-center">
              <div className="h-4 w-4 rounded animate-pulse bg-[var(--surface-2)]" />
              <div className="h-4 flex-1 rounded animate-pulse bg-[var(--surface-2)]" />
              <div className="h-4 w-16 rounded animate-pulse bg-[var(--surface-2)]" />
            </div>
          ))
        ) : !log.data || log.data.length === 0 ? (
          <div className="px-6 py-8 text-center text-sm text-[var(--text-muted)]">
            No audit entries yet. Events will appear here as you use the system.
          </div>
        ) : (
          log.data.map((entry: AuditEntry) => {
            const { icon: Icon, variant } = getActionMeta(entry.action);
            return (
              <div key={entry.id} className="px-6 py-3 flex items-start gap-3 hover:bg-[var(--surface-1)] transition-colors">
                <div className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 mt-0.5 bg-[var(--surface-1)]">
                  <Icon size={12} className={
                    variant === "positive" ? "text-[var(--positive)]"
                    : variant === "negative" ? "text-[var(--negative)]"
                    : "text-[var(--text-muted)]"
                  } />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant={variant} className="font-mono">{entry.action}</Badge>
                    {entry.resource && (
                      <span className="text-[10px] text-[var(--text-muted)] font-mono truncate max-w-[160px]">
                        {entry.resource}
                      </span>
                    )}
                  </div>
                  {entry.actor_key && (
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">
                      by <code className="font-mono text-[var(--brand-2)]">{entry.actor_key}</code>
                      {entry.ip_addr && <> from {entry.ip_addr}</>}
                    </p>
                  )}
                </div>
                <span className="text-[10px] text-[var(--text-muted)] shrink-0 mt-0.5 tabular">
                  {relTime(entry.created_at)}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
