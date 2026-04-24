import type { Lead, Stage } from "../api/crm";

function paise(v: number) {
  return v === 0 ? "—" : `₹${(v / 100).toLocaleString("en-IN")}`;
}

function initials(name: string): string {
  return name.split(" ").slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("");
}

interface Props {
  leads: Lead[];
  stages: Stage[];
  onLeadClick: (leadId: string) => void;
  onAddLead: () => void;
}

export default function LeadsTable({ leads, stages, onLeadClick, onAddLead }: Props) {
  const stageMap = Object.fromEntries(stages.map((s) => [s.id, s]));

  return (
    <div className="rounded-xl overflow-hidden bg-[var(--bg-2)] border border-[var(--border-subtle)]">
      <div className="px-6 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">All Leads ({leads.length})</h3>
        <button
          onClick={onAddLead}
          className="text-xs px-3 py-1.5 rounded-lg font-semibold hover:brightness-110 transition-all"
          style={{ background: "var(--brand)", color: "#020d07" }}
        >
          + Add Lead
        </button>
      </div>

      {leads.length === 0 ? (
        <p className="px-6 py-10 text-sm text-[var(--text-muted)] text-center">
          No leads yet. Add your first lead to get started.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[var(--bg-1)]">
                {["Name", "Company", "Stage", "Plan", "MRR Est.", "Source", "Owner"].map((h, i) => (
                  <th
                    key={h}
                    className={`px-6 py-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-muted)] border-b border-[var(--border-subtle)] ${i === 4 ? "text-right" : "text-left"}`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {leads.map((lead) => {
                const stage = lead.stage_id ? stageMap[lead.stage_id] : null;
                return (
                  <tr
                    key={lead.id}
                    onClick={() => onLeadClick(lead.id)}
                    className="cursor-pointer hover:bg-[var(--surface-1)] transition-colors"
                  >
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-2.5">
                        <div
                          className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold shrink-0"
                          style={{ background: "var(--brand-dim)", color: "var(--brand)" }}
                        >
                          {initials(lead.name)}
                        </div>
                        <div>
                          <p className="font-medium text-[var(--text-primary)]">{lead.name}</p>
                          {lead.email && (
                            <p className="text-xs text-[var(--text-muted)]">{lead.email}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-3 text-[var(--text-secondary)] text-sm">{lead.company ?? "—"}</td>
                    <td className="px-6 py-3">
                      {stage ? (
                        <span
                          className="inline-flex items-center text-xs px-2.5 py-1 rounded-full font-medium"
                          style={{
                            backgroundColor: stage.color + "22",
                            color: stage.color,
                          }}
                        >
                          {stage.name}
                        </span>
                      ) : (
                        <span className="text-xs text-[var(--text-muted)]">Unassigned</span>
                      )}
                    </td>
                    <td className="px-6 py-3 text-[var(--text-secondary)] text-sm">{lead.plan_interest ?? "—"}</td>
                    <td className="px-6 py-3 text-right font-semibold tabular text-[var(--text-primary)]">
                      {paise(lead.mrr_estimate_paise)}
                    </td>
                    <td className="px-6 py-3">
                      {lead.source ? (
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-[var(--surface-1)] text-[var(--text-secondary)] border border-[var(--border-subtle)]">
                          {lead.source}
                        </span>
                      ) : <span className="text-[var(--text-muted)]">—</span>}
                    </td>
                    <td className="px-6 py-3 text-[var(--text-secondary)] text-sm">{lead.owner ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
