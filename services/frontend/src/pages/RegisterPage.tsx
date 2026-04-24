import { useState } from "react";
import { CheckCircle2, Copy, Check } from "lucide-react";
import { register } from "../api/auth";
import AuthShell from "../components/AuthShell";

interface Props {
  onSuccess: (token: string, merchantId: string, name: string, email: string) => void;
  onLoginClick: () => void;
  onBackClick?: () => void;
}

interface SuccessInfo {
  apiKey: string;
  webhookSecret: string;
  webhookUrl: string;
}

export default function RegisterPage({ onSuccess, onLoginClick, onBackClick }: Props) {
  const [form, setForm] = useState({
    company_name: "",
    name: "",
    email: "",
    password: "",
    razorpay_key_id: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<SuccessInfo | null>(null);
  const [pendingSession, setPendingSession] = useState<{
    token: string;
    merchantId: string;
    name: string;
    email: string;
  } | null>(null);
  const [copiedField, setCopiedField] = useState<"apiKey" | "webhookSecret" | "webhookUrl" | null>(null);

  function field(key: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((current) => ({ ...current, [key]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await register({
        company_name: form.company_name.trim(),
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
        razorpay_key_id: form.razorpay_key_id.trim() || undefined,
      });
      setPendingSession({
        token: data.access_token,
        merchantId: data.merchant_id,
        name: data.name,
        email: data.email,
      });
      setSuccess({
        apiKey: data.api_key,
        webhookSecret: data.webhook_secret,
        webhookUrl: data.webhook_url,
      });
    } catch (err: any) {
      const msg = err?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function handleCopy(fieldName: "apiKey" | "webhookSecret" | "webhookUrl") {
    if (!success) return;
    const value =
      fieldName === "apiKey"
        ? success.apiKey
        : fieldName === "webhookSecret"
          ? success.webhookSecret
          : success.webhookUrl;
    navigator.clipboard.writeText(value);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(null), 1800);
  }

  function handleContinue() {
    if (!pendingSession) return;
    onSuccess(
      pendingSession.token,
      pendingSession.merchantId,
      pendingSession.name,
      pendingSession.email,
    );
  }

  if (success) {
    return (
      <AuthShell
        title="Your workspace is live."
        subtitle="These are the exact credentials to drop into Razorpay so subscription events start flowing into RazorScope."
        eyebrow="Account created"
        badge="Ready to connect"
        sideTitle="Next best move"
        sideDescription="For the fastest setup, use Basic Mode. Copy the webhook URL and secret into Razorpay and your dashboard will begin filling with new events."
        sideChildren={
          <div className="space-y-3">
            <div className="rounded-2xl border border-emerald-300/20 bg-emerald-300/10 p-4 text-sm text-emerald-100">
              Webhook-only gets you future analytics immediately.
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
              When you are ready for historical reporting, add Razorpay API credentials from Settings to run a backfill.
            </div>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="rounded-3xl border border-emerald-300/20 bg-emerald-300/10 p-4 text-emerald-100">
            <p className="text-sm font-medium flex items-center gap-2">
              <CheckCircle2 size={15} className="text-[var(--positive)] shrink-0" />
              Account created successfully
            </p>
            <p className="mt-2 text-sm text-emerald-50/90">
              Save these credentials for your Razorpay webhook setup.
            </p>
          </div>

          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.24em] text-slate-400">API Key</label>
            <div className="flex gap-2">
              <code className="flex-1 break-all rounded-2xl border border-white/10 bg-white/5 px-4 py-3 font-mono text-xs text-cyan-100">
                {success.apiKey}
              </code>
              <button
                type="button"
                onClick={() => handleCopy("apiKey")}
                className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs transition-colors ${copiedField === "apiKey" ? "border-emerald-300/30 bg-emerald-300/10 text-emerald-200" : "border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"}`}
              >
                {copiedField === "apiKey" ? <Check size={12} /> : <Copy size={12} />}
                {copiedField === "apiKey" ? "Copied" : "Copy"}
              </button>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.24em] text-slate-400">Webhook URL</label>
            <div className="flex gap-2">
              <code className="flex-1 break-all rounded-2xl border border-white/10 bg-white/5 px-4 py-3 font-mono text-xs text-cyan-100">
                {success.webhookUrl}
              </code>
              <button
                type="button"
                onClick={() => handleCopy("webhookUrl")}
                className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs transition-colors ${copiedField === "webhookUrl" ? "border-emerald-300/30 bg-emerald-300/10 text-emerald-200" : "border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"}`}
              >
                {copiedField === "webhookUrl" ? <Check size={12} /> : <Copy size={12} />}
                {copiedField === "webhookUrl" ? "Copied" : "Copy"}
              </button>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.24em] text-slate-400">Webhook Secret</label>
            <div className="flex gap-2">
              <code className="flex-1 break-all rounded-2xl border border-white/10 bg-white/5 px-4 py-3 font-mono text-xs text-cyan-100">
                {success.webhookSecret}
              </code>
              <button
                type="button"
                onClick={() => handleCopy("webhookSecret")}
                className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs transition-colors ${copiedField === "webhookSecret" ? "border-emerald-300/30 bg-emerald-300/10 text-emerald-200" : "border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"}`}
              >
                {copiedField === "webhookSecret" ? <Check size={12} /> : <Copy size={12} />}
                {copiedField === "webhookSecret" ? "Copied" : "Copy"}
              </button>
            </div>
          </div>

          <p className="rounded-2xl border border-amber-300/20 bg-amber-300/10 px-4 py-3 text-sm text-amber-100">
            In Razorpay, create a webhook with the URL above and use the same webhook secret shown here.
          </p>

          <button
            type="button"
            onClick={handleContinue}
            className="w-full rounded-xl bg-[var(--brand)] py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110"
          >
            Go to dashboard
          </button>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Create your revenue workspace."
      subtitle="Launch fast with webhook-only setup, then layer in Razorpay credentials later for historical backfill."
      eyebrow="New workspace"
      badge="Two-step onboarding"
      sideTitle="Built for the real rollout"
      sideDescription="Start simple for speed. Upgrade the connection when your team wants past plus future analytics on the same timeline."
      sideChildren={
        <div className="space-y-3">
          <div className="rounded-2xl border border-cyan-300/15 bg-cyan-300/5 p-4">
            <div className="flex items-center justify-between">
              <p className="font-medium text-white">Basic Mode</p>
              <span className="metric-pill bg-cyan-300/10 text-cyan-100">Fastest</span>
            </div>
            <p className="mt-2 text-sm text-slate-300">
              Copy webhook URL and secret into Razorpay. Start collecting new events immediately.
            </p>
          </div>
          <div className="rounded-2xl border border-amber-300/15 bg-amber-300/5 p-4">
            <div className="flex items-center justify-between">
              <p className="font-medium text-white">Advanced Mode</p>
              <span className="metric-pill bg-amber-300/10 text-amber-100">Later</span>
            </div>
            <p className="mt-2 text-sm text-slate-300">
              Save Razorpay API credentials in Settings to run backfill and unlock historical analytics.
            </p>
          </div>
        </div>
      }
      footer={
        <p>
          Already have an account?{" "}
          <button onClick={onLoginClick} className="font-medium text-[var(--brand)] hover:underline">
            Sign in
          </button>
        </p>
      }
      onBackClick={onBackClick}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.24em] text-slate-400">Company name</label>
            <input
              type="text"
              required
              autoFocus
              value={form.company_name}
              onChange={field("company_name")}
              className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-300/60"
              placeholder="Acme Inc."
            />
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.24em] text-slate-400">Your name</label>
            <input
              type="text"
              required
              value={form.name}
              onChange={field("name")}
              className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-300/60"
              placeholder="Jane Smith"
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.24em] text-slate-400">Email</label>
          <input
            type="email"
            required
            value={form.email}
            onChange={field("email")}
            className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-300/60"
            placeholder="you@company.com"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.24em] text-slate-400">Password</label>
          <input
            type="password"
            required
            minLength={8}
            value={form.password}
            onChange={field("password")}
            className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-300/60"
            placeholder="Minimum 8 characters"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.24em] text-slate-400">
            Razorpay Key ID <span className="normal-case tracking-normal text-slate-500">(optional, can be added later)</span>
          </label>
          <input
            type="text"
            value={form.razorpay_key_id}
            onChange={field("razorpay_key_id")}
            className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-300/60"
            placeholder="rzp_live_..."
          />
        </div>

        {error ? (
          <p className="rounded-2xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={loading || !form.company_name || !form.name || !form.email || !form.password}
          className="w-full rounded-xl bg-[var(--brand)] py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Creating account..." : "Create account"}
        </button>
      </form>
    </AuthShell>
  );
}
