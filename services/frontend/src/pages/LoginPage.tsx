import { useState } from "react";
import { login } from "../api/auth";
import AuthShell from "../components/AuthShell";

interface Props {
  onSuccess: (token: string, merchantId: string, name: string, email: string) => void;
  onRegisterClick: () => void;
  onBackClick?: () => void;
}

export default function LoginPage({ onSuccess, onRegisterClick, onBackClick }: Props) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function field(key: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((current) => ({ ...current, [key]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await login({ email: form.email.trim(), password: form.password });
      onSuccess(data.access_token, data.merchant_id, data.name, data.email);
    } catch (err: any) {
      const msg = err?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Invalid email or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Sign in and pick the story back up."
      subtitle="Drop back into your Razorpay workspace, watch live subscription movement, and keep revenue operations moving."
      eyebrow="Existing workspace"
      badge="Secure session"
      sideTitle="What is waiting inside"
      sideDescription="Your dashboard keeps the moving parts on one screen: MRR changes, cohorts, benchmarks, CRM signals, and security controls."
      sideChildren={
        <div className="space-y-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm font-medium text-white">Live feed</p>
            <div className="mt-3 flex items-end gap-2">
              {[28, 36, 48, 62, 54, 70].map((height, index) => (
                <div
                  key={height}
                  className="chart-bar flex-1 rounded-t-xl bg-gradient-to-t from-[#34d399] via-[#7ff7cb] to-[#b2fce4]"
                  style={{ height: `${height}px`, animationDelay: `${index * 120}ms` }}
                />
              ))}
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Closing MRR</p>
              <p className="mt-2 text-2xl font-semibold text-white">₹48,000</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Retention</p>
              <p className="mt-2 text-2xl font-semibold text-cyan-200">92%</p>
            </div>
          </div>
        </div>
      }
      footer={
        <p>
          No account yet?{" "}
          <button onClick={onRegisterClick} className="font-medium text-[var(--brand)] hover:underline">
            Create one
          </button>
        </p>
      }
      onBackClick={onBackClick}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.24em] text-slate-400">Email</label>
          <input
            type="email"
            required
            autoFocus
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
            value={form.password}
            onChange={field("password")}
            className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-300/60"
            placeholder="Enter your password"
          />
        </div>

        {error ? (
          <p className="rounded-2xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={loading || !form.email || !form.password}
          className="w-full rounded-xl bg-[var(--brand)] py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </AuthShell>
  );
}
