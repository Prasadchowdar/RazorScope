import { useState } from "react";
import { Plus, Copy, Check, X } from "lucide-react";
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from "../hooks/useSecurity";
import Badge from "./Badge";
import type { ApiKey } from "../api/security";

const inputCls = "w-full rounded-lg px-3 py-2 text-sm bg-[var(--bg-0)] border border-[var(--border-default)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--brand)] focus:border-[var(--brand)] transition-colors";

function relTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86_400_000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  return `${days}d ago`;
}

function Modal({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-md mx-4 rounded-2xl p-6 shadow-2xl border border-[var(--border-strong)]"
        style={{ background: "var(--bg-1)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

export default function ApiKeyManager() {
  const keys = useApiKeys();
  const createKey = useCreateApiKey();
  const revokeKey = useRevokeApiKey();

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "viewer">("admin");
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    const result = await createKey.mutateAsync({ name: newName.trim(), role: newRole });
    setRevealedKey(result.raw_key);
    setNewName("");
    setShowCreate(false);
  }

  async function handleRevoke(key: ApiKey) {
    if (!confirm(`Revoke key "${key.name}"? Any apps using it will stop working.`)) return;
    await revokeKey.mutateAsync(key.id);
  }

  function copyKey() {
    if (!revealedKey) return;
    navigator.clipboard.writeText(revealedKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const activeKeys = (keys.data ?? []).filter((k) => !k.revoked_at);
  const revokedKeys = (keys.data ?? []).filter((k) => k.revoked_at);

  return (
    <div className="rounded-xl overflow-hidden bg-[var(--bg-2)] border border-[var(--border-subtle)]">
      <div className="px-6 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">API Keys</h2>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">Named keys with RBAC — shown once at creation</p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-semibold hover:brightness-110 transition-all"
          style={{ background: "var(--brand)", color: "#020d07" }}
        >
          <Plus size={12} /> New Key
        </button>
      </div>

      {/* Reveal modal */}
      {revealedKey && (
        <Modal onClose={() => { setRevealedKey(null); setCopied(false); }}>
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">Copy your API key</h3>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">This key will not be shown again.</p>
            </div>
            <button type="button" onClick={() => { setRevealedKey(null); setCopied(false); }}
              aria-label="Close" className="w-6 h-6 flex items-center justify-center rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-2)] transition-colors">
              <X size={13} />
            </button>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-[rgba(127,247,203,0.2)] bg-[var(--bg-2)] px-3 py-2.5 mb-4">
            <code className="text-xs text-[var(--brand-2)] font-mono flex-1 break-all">{revealedKey}</code>
          </div>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={copyKey}
              className={`flex items-center gap-1.5 text-xs px-4 py-2 rounded-lg border transition-colors ${
                copied
                  ? "border-[rgba(52,211,153,0.3)] bg-[var(--positive-dim)] text-[var(--positive)]"
                  : "border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--border-strong)]"
              }`}>
              {copied ? <Check size={12} /> : <Copy size={12} />}
              {copied ? "Copied!" : "Copy"}
            </button>
            <button type="button" onClick={() => { setRevealedKey(null); setCopied(false); }}
              className="text-xs px-4 py-2 rounded-lg font-semibold hover:brightness-110 transition-all"
              style={{ background: "var(--brand)", color: "#020d07" }}>
              Done
            </button>
          </div>
        </Modal>
      )}

      {/* Create form modal */}
      {showCreate && (
        <Modal onClose={() => setShowCreate(false)}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Create API Key</h3>
            <button type="button" onClick={() => setShowCreate(false)} aria-label="Close"
              className="w-6 h-6 flex items-center justify-center rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-2)] transition-colors">
              <X size={13} />
            </button>
          </div>
          <form onSubmit={handleCreate} className="space-y-3">
            <div>
              <label className="block text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--text-muted)] mb-1.5">Key Name</label>
              <input autoFocus value={newName} onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Production Dashboard" className={inputCls} />
            </div>
            <div>
              <label className="block text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--text-muted)] mb-1.5">Role</label>
              <select title="Role" value={newRole} onChange={(e) => setNewRole(e.target.value as "admin" | "viewer")} className={inputCls}>
                <option value="admin">Admin — full read/write</option>
                <option value="viewer">Viewer — read only</option>
              </select>
            </div>
            <div className="flex gap-2 pt-1">
              <button type="button" onClick={() => setShowCreate(false)}
                className="flex-1 text-xs px-4 py-2 rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)] transition-colors">
                Cancel
              </button>
              <button type="submit" disabled={!newName.trim() || createKey.isPending}
                className="flex-1 text-xs px-4 py-2 rounded-lg font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
                style={{ background: "var(--brand)", color: "#020d07" }}>
                {createKey.isPending ? "Creating…" : "Create"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      <div className="p-6 space-y-4">
        {keys.isPending ? (
          Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-14 rounded-lg animate-pulse bg-[var(--surface-1)]" />
          ))
        ) : activeKeys.length === 0 ? (
          <p className="text-sm text-[var(--text-muted)] text-center py-4">No active API keys. Create one above.</p>
        ) : (
          <div className="divide-y divide-[var(--border-subtle)]">
            {activeKeys.map((k) => (
              <div key={k.id} className="flex items-center justify-between py-3 gap-4">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[var(--text-primary)] truncate">{k.name}</p>
                  <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                    <code className="text-[10px] font-mono text-[var(--text-muted)]">{k.key_prefix}</code>
                    <Badge variant={k.role === "admin" ? "brand" : "neutral"}>{k.role}</Badge>
                    {k.last_used_at && (
                      <span className="text-[10px] text-[var(--text-muted)]">used {relTime(k.last_used_at)}</span>
                    )}
                  </div>
                </div>
                <button type="button" onClick={() => handleRevoke(k)} disabled={revokeKey.isPending}
                  className="text-xs px-3 py-1.5 rounded-lg border border-[rgba(248,113,113,0.3)] text-[var(--negative)] hover:bg-[var(--negative-dim)] disabled:opacity-40 transition-colors shrink-0">
                  Revoke
                </button>
              </div>
            ))}
          </div>
        )}

        {revokedKeys.length > 0 && (
          <details className="text-xs text-[var(--text-muted)]">
            <summary className="cursor-pointer hover:text-[var(--text-secondary)] transition-colors">
              {revokedKeys.length} revoked key{revokedKeys.length > 1 ? "s" : ""}
            </summary>
            <div className="mt-2 space-y-1 opacity-50">
              {revokedKeys.map((k) => (
                <div key={k.id} className="flex justify-between items-center">
                  <span className="font-medium">{k.name} <code className="ml-1 font-mono text-[10px]">{k.key_prefix}</code></span>
                  <span>revoked {relTime(k.revoked_at!)}</span>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
