import { useState } from "react";
import { X, FileText, Mail, Phone, Handshake, Sparkles } from "lucide-react";
import type { LeadWithActivities, Activity } from "../api/crm";
import { useUpdateLead, useDeleteLead, useAddActivity, useEnrichLead } from "../hooks/useCrm";
import TaskList from "./TaskList";
import SequenceBuilder from "./SequenceBuilder";

interface LeadForm {
  name: string;
  email: string;
  company: string;
  phone: string;
  stage_id: string | null;
  plan_interest: string;
  mrr_estimate_paise: number;
  source: string;
  owner: string;
  notes: string;
}

const ACTIVITY_ICONS: Record<string, React.ElementType> = {
  note: FileText, email: Mail, call: Phone, meeting: Handshake,
};

function paise(v: number) { return v === 0 ? "—" : `₹${(v / 100).toLocaleString("en-IN")}`; }

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const inputCls = "w-full rounded-lg px-3 py-2 text-sm bg-[var(--bg-0)] border border-[var(--border-default)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--brand)] focus:border-[var(--brand)] transition-colors";

interface Props {
  lead: LeadWithActivities | undefined;
  loading: boolean;
  stages: { id: string; name: string; color: string }[];
  onClose: () => void;
  onDeleted: () => void;
}

export default function LeadDrawer({ lead, loading, stages, onClose, onDeleted }: Props) {
  const [editing, setEditing] = useState(false);
  const [activityType, setActivityType] = useState("note");
  const [activityBody, setActivityBody] = useState("");
  const [form, setForm] = useState<Partial<LeadForm>>({});

  const updateLead = useUpdateLead();
  const deleteLead = useDeleteLead();
  const addActivity = useAddActivity();
  const enrichLead = useEnrichLead();

  if (!lead && !loading) return null;

  function startEdit() {
    if (!lead) return;
    setForm({
      name: lead.name, email: lead.email ?? "", company: lead.company ?? "",
      phone: lead.phone ?? "", stage_id: lead.stage_id ?? "", plan_interest: lead.plan_interest ?? "",
      mrr_estimate_paise: lead.mrr_estimate_paise, source: lead.source ?? "",
      owner: lead.owner ?? "", notes: lead.notes ?? "",
    });
    setEditing(true);
  }

  async function saveEdit() {
    if (!lead) return;
    const patch: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(form as Record<string, unknown>)) {
      if (v !== undefined) patch[k] = v === "" ? null : v;
    }
    await updateLead.mutateAsync({ leadId: lead.id, patch });
    setEditing(false);
  }

  async function handleDelete() {
    if (!lead || !confirm(`Delete lead "${lead.name}"?`)) return;
    await deleteLead.mutateAsync(lead.id);
    onDeleted();
  }

  async function submitActivity(e: React.FormEvent) {
    e.preventDefault();
    if (!lead || !activityBody.trim()) return;
    await addActivity.mutateAsync({ leadId: lead.id, type: activityType, body: activityBody.trim() });
    setActivityBody("");
  }

  function SectionLabel({ children }: { children: React.ReactNode }) {
    return (
      <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-muted)] mb-3">
        {children}
      </p>
    );
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end" onClick={onClose}>
      <div
        className="relative w-full max-w-lg h-full overflow-y-auto border-l border-[var(--border-subtle)] shadow-2xl"
        style={{ background: "var(--bg-1)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="sticky top-0 z-10 px-6 py-4 flex items-center justify-between border-b border-[var(--border-subtle)]"
          style={{ background: "var(--bg-1)" }}
        >
          <h2 className="text-sm font-semibold text-[var(--text-primary)] truncate">
            {loading ? "Loading…" : (lead?.name ?? "")}
          </h2>
          <div className="flex items-center gap-2">
            {!editing && lead && (
              <>
                <button type="button" onClick={startEdit}
                  className="text-xs px-3 py-1.5 rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)] transition-colors">
                  Edit
                </button>
                <button type="button" onClick={handleDelete}
                  className="text-xs px-3 py-1.5 rounded-lg border border-[rgba(248,113,113,0.3)] text-[var(--negative)] hover:bg-[var(--negative-dim)] transition-colors">
                  Delete
                </button>
              </>
            )}
            {editing && (
              <>
                <button type="button" onClick={saveEdit} disabled={updateLead.isPending}
                  className="text-xs px-3 py-1.5 rounded-lg font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
                  style={{ background: "var(--brand)", color: "#020d07" }}>
                  {updateLead.isPending ? "Saving…" : "Save"}
                </button>
                <button type="button" onClick={() => setEditing(false)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
                  Cancel
                </button>
              </>
            )}
            <button type="button" onClick={onClose} aria-label="Close"
              className="w-7 h-7 flex items-center justify-center rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-2)] transition-colors ml-1">
              <X size={15} />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-6 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-8 rounded-lg animate-pulse bg-[var(--surface-1)]" />
            ))}
          </div>
        ) : lead ? (
          <div className="p-6 space-y-6">
            {/* Details */}
            {editing ? (
              <div className="grid grid-cols-2 gap-3">
                {([
                  ["name", "Name", "text"], ["email", "Email", "email"],
                  ["company", "Company", "text"], ["phone", "Phone", "tel"],
                  ["plan_interest", "Plan Interest", "text"], ["source", "Source", "text"],
                  ["owner", "Owner", "text"],
                ] as [string, string, string][]).map(([key, label, type]) => (
                  <div key={key}>
                    <label className="block text-xs text-[var(--text-muted)] mb-1">{label}</label>
                    <input type={type} title={label} placeholder={label}
                      value={(form as Record<string, unknown>)[key] as string ?? ""}
                      onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                      className={inputCls} />
                  </div>
                ))}
                <div>
                  <label className="block text-xs text-[var(--text-muted)] mb-1">Stage</label>
                  <select title="Stage"
                    value={(form as Record<string, unknown>)["stage_id"] as string ?? ""}
                    onChange={(e) => setForm((f) => ({ ...f, stage_id: e.target.value || null }))}
                    className={inputCls}>
                    <option value="">Unassigned</option>
                    {stages.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-[var(--text-muted)] mb-1">MRR Estimate (paise)</label>
                  <input type="number" title="MRR Estimate" placeholder="0"
                    value={(form as Record<string, unknown>)["mrr_estimate_paise"] as number ?? 0}
                    onChange={(e) => setForm((f) => ({ ...f, mrr_estimate_paise: parseInt(e.target.value) || 0 }))}
                    className={inputCls} />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs text-[var(--text-muted)] mb-1">Notes</label>
                  <textarea rows={3} title="Notes" placeholder="Notes"
                    value={(form as Record<string, unknown>)["notes"] as string ?? ""}
                    onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                    className={`${inputCls} resize-none`} />
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-y-4 text-sm">
                {([
                  ["Company", lead.company], ["Email", lead.email], ["Phone", lead.phone],
                  ["Plan Interest", lead.plan_interest], ["MRR Estimate", paise(lead.mrr_estimate_paise)],
                  ["Source", lead.source], ["Owner", lead.owner],
                  ["Stage", stages.find((s) => s.id === lead.stage_id)?.name ?? "Unassigned"],
                ] as [string, string | null | undefined][]).map(([label, value]) =>
                  value ? (
                    <div key={label}>
                      <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--text-muted)] mb-0.5">{label}</p>
                      <p className="text-sm font-medium text-[var(--text-primary)]">{value}</p>
                    </div>
                  ) : null
                )}
                {lead.notes && (
                  <div className="col-span-2">
                    <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--text-muted)] mb-1">Notes</p>
                    <p className="text-sm text-[var(--text-secondary)] whitespace-pre-wrap">{lead.notes}</p>
                  </div>
                )}
              </div>
            )}

            {/* Log activity */}
            <div className="border-t border-[var(--border-subtle)] pt-5">
              <SectionLabel>Log Activity</SectionLabel>
              <form onSubmit={submitActivity} className="flex flex-col gap-2">
                <div className="flex gap-1.5 flex-wrap">
                  {["note", "email", "call", "meeting"].map((t) => {
                    const Icon = ACTIVITY_ICONS[t] ?? FileText;
                    const active = activityType === t;
                    return (
                      <button key={t} type="button" onClick={() => setActivityType(t)}
                        className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border transition-colors"
                        style={active
                          ? { background: "var(--brand-dim)", color: "var(--brand)", borderColor: "rgba(127,247,203,0.3)" }
                          : { background: "transparent", color: "var(--text-secondary)", borderColor: "var(--border-default)" }
                        }>
                        <Icon size={11} />{t}
                      </button>
                    );
                  })}
                </div>
                <textarea rows={2} value={activityBody}
                  onChange={(e) => setActivityBody(e.target.value)}
                  placeholder="Add a note…"
                  className={`${inputCls} resize-none`} />
                <button type="submit" disabled={!activityBody.trim() || addActivity.isPending}
                  className="self-end text-xs px-4 py-1.5 rounded-lg font-semibold hover:brightness-110 disabled:opacity-40 transition-all"
                  style={{ background: "var(--brand)", color: "#020d07" }}>
                  {addActivity.isPending ? "Saving…" : "Save"}
                </button>
              </form>
            </div>

            {/* Tasks */}
            <div className="border-t border-[var(--border-subtle)] pt-5">
              <TaskList leadId={lead.id} />
            </div>

            {/* Email sequences */}
            <div className="border-t border-[var(--border-subtle)] pt-5">
              <SequenceBuilder leadId={lead.id} />
            </div>

            {/* Enrich */}
            {!editing && (
              <div className="border-t border-[var(--border-subtle)] pt-5 flex items-center justify-between gap-4">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-muted)]">Enrichment</p>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">Auto-fill company data from lead info</p>
                </div>
                <button type="button" onClick={() => enrichLead.mutate(lead.id)} disabled={enrichLead.isPending}
                  className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--brand)] hover:text-[var(--brand)] disabled:opacity-40 transition-colors whitespace-nowrap">
                  <Sparkles size={12} />
                  {enrichLead.isPending ? "Enriching…" : "Enrich Lead"}
                </button>
              </div>
            )}

            {/* Activity timeline */}
            {lead.activities.length > 0 && (
              <div className="border-t border-[var(--border-subtle)] pt-5">
                <SectionLabel>Activity</SectionLabel>
                <div className="space-y-4">
                  {lead.activities.map((a: Activity) => {
                    const Icon = ACTIVITY_ICONS[a.type] ?? FileText;
                    return (
                      <div key={a.id} className="flex gap-3">
                        <div className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 mt-0.5 bg-[var(--surface-1)]">
                          <Icon size={12} className="text-[var(--text-muted)]" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-[var(--text-secondary)] whitespace-pre-wrap break-words">{a.body}</p>
                          <p className="text-xs text-[var(--text-muted)] mt-0.5">{relativeTime(a.created_at)}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
