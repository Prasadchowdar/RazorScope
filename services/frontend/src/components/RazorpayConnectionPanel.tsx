import { useEffect, useState } from "react";
import { Copy, Check } from "lucide-react";
import BackfillPanel from "./BackfillPanel";
import {
  getRazorpayIntegration,
  saveRazorpayCredentials,
  type RazorpayIntegration,
} from "../api/integrations";
import { useAuth } from "../context/AuthContext";

const inputCls = "w-full rounded-lg px-3 py-2 text-sm bg-[var(--bg-0)] border border-[var(--border-default)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--brand)] focus:border-[var(--brand)] transition-colors";

function CopyField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div>
      <label className="block text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--text-muted)] mb-1.5">{label}</label>
      <div className="flex items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-0)] px-3 py-2">
        <code className="flex-1 break-all text-xs text-[var(--brand-2)] font-mono">{value}</code>
        <button
          type="button"
          onClick={handleCopy}
          aria-label="Copy"
          className={`shrink-0 flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs transition-colors ${
            copied
              ? "border-[rgba(52,211,153,0.3)] bg-[var(--positive-dim)] text-[var(--positive)]"
              : "border-[var(--border-default)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
          }`}
        >
          {copied ? <Check size={11} /> : <Copy size={11} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}

export default function RazorpayConnectionPanel() {
  const { accessToken } = useAuth();
  const [integration, setIntegration] = useState<RazorpayIntegration | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [keyId, setKeyId] = useState("");
  const [keySecret, setKeySecret] = useState("");

  async function loadIntegration() {
    if (!accessToken) return;
    setLoading(true);
    try {
      const data = await getRazorpayIntegration(accessToken);
      setIntegration(data);
      setKeyId(data.mode_advanced.razorpay_key_id ?? "");
      setError(null);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to load Razorpay connection details.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadIntegration(); }, [accessToken]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!accessToken) return;
    setSaving(true); setError(null); setSuccess(null);
    try {
      const data = await saveRazorpayCredentials(accessToken, keyId.trim(), keySecret.trim());
      setIntegration(data);
      setKeyId(data.mode_advanced.razorpay_key_id);
      setKeySecret("");
      setSuccess("Razorpay API credentials saved. Historical backfill is now unlocked.");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to save Razorpay API credentials.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="rounded-xl h-64 animate-pulse bg-[var(--bg-2)] border border-[var(--border-subtle)]" />;
  }

  if (!integration) {
    return (
      <div className="rounded-xl border border-[rgba(248,113,113,0.3)] p-4 text-sm bg-[var(--negative-dim)] text-[var(--negative)]">
        {error ?? "Unable to load Razorpay connection details."}
      </div>
    );
  }

  const isConnected = integration.mode_advanced.has_api_credentials;

  return (
    <div className="space-y-5">
      <div className="rounded-xl overflow-hidden bg-[var(--bg-2)] border border-[var(--border-subtle)]">
        <div className="px-6 py-4 border-b border-[var(--border-subtle)]">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Connect Razorpay</h2>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            Choose the lightweight webhook-only setup, or add API credentials to unlock historical backfill.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 p-6">
          {/* Basic Mode */}
          <section className="rounded-xl border border-[rgba(127,247,203,0.2)] p-5 bg-[var(--brand-dim)]">
            <div className="flex items-start justify-between gap-3 mb-4">
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">Basic Mode</h3>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Copy the webhook URL and secret into Razorpay. New events start flowing immediately.
                </p>
              </div>
              <span className="rounded-full px-2.5 py-1 text-[10px] font-semibold shrink-0 bg-[var(--brand-dim)] text-[var(--brand)] border border-[rgba(127,247,203,0.2)]">
                Webhook-only
              </span>
            </div>
            <div className="space-y-3">
              <CopyField label="Webhook URL" value={integration.mode_basic.webhook_url} />
              <CopyField label="Webhook Secret" value={integration.mode_basic.webhook_secret} />
            </div>
          </section>

          {/* Advanced Mode */}
          <section
            className="rounded-xl border p-5"
            style={{
              borderColor: isConnected ? "rgba(52,211,153,0.25)" : "var(--border-default)",
              background: isConnected ? "rgba(52,211,153,0.05)" : "var(--bg-1)",
            }}
          >
            <div className="flex items-start justify-between gap-3 mb-4">
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">Advanced Mode</h3>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Save Razorpay API credentials to run backfill and see past analytics.
                </p>
              </div>
              <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold shrink-0 ${
                isConnected
                  ? "bg-[var(--positive-dim)] text-[var(--positive)] border border-[rgba(52,211,153,0.2)]"
                  : "bg-[var(--warning-dim)] text-[var(--warning)] border border-[rgba(251,191,36,0.2)]"
              }`}>
                {isConnected ? "Connected" : "Not Connected"}
              </span>
            </div>
            <form onSubmit={handleSave} className="space-y-3">
              <div>
                <label className="block text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--text-muted)] mb-1.5">Razorpay Key ID</label>
                <input value={keyId} onChange={(e) => setKeyId(e.target.value)} placeholder="rzp_live_..." autoComplete="off" className={inputCls} />
              </div>
              <div>
                <label className="block text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--text-muted)] mb-1.5">Razorpay Key Secret</label>
                <input type="password" value={keySecret} onChange={(e) => setKeySecret(e.target.value)}
                  placeholder={isConnected ? "••••••••••••••••" : "Enter your Razorpay key secret"}
                  autoComplete="new-password" className={inputCls} />
              </div>
              <button type="submit" disabled={saving || !keyId.trim() || !keySecret.trim()}
                className="rounded-xl px-4 py-2 text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
                style={{ background: "var(--positive)", color: "#020d07" }}>
                {saving ? "Saving…" : isConnected ? "Update API Credentials" : "Save API Credentials"}
              </button>
              {success && <p className="text-xs text-[var(--positive)]">{success}</p>}
              {error && <p className="text-xs text-[var(--negative)]">{error}</p>}
            </form>
          </section>
        </div>
      </div>

      <BackfillPanel
        enabled={integration.mode_advanced.backfill_ready}
        lockedMessage="Save your Razorpay Key ID and Key Secret above to run historical backfill."
      />
    </div>
  );
}
