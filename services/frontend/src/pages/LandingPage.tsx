import { TrendingUp, Zap, Grid3X3 } from "lucide-react";
import SetupGuide from "../components/SetupGuide";

interface LandingPageProps {
  onGetStarted: () => void;
  onSignIn: () => void;
}

const featureCards = [
  {
    icon: TrendingUp,
    title: "Revenue movement that tells a story",
    body: "See new, churned, reactivated, and expansion MRR move in one clean stream instead of stitching exports together.",
  },
  {
    icon: Zap,
    title: "Dual-mode onboarding",
    body: "Start with webhook-only setup for speed, then unlock historical backfill when the team is ready to connect API credentials.",
  },
  {
    icon: Grid3X3,
    title: "Built for operators, not analysts only",
    body: "MRR, cohorts, benchmarks, CRM, and audit trails sit in one product so finance and growth read from the same surface.",
  },
];

const steps = [
  {
    label: "Create workspace",
    body: "Set up your merchant in minutes and get a ready-to-use webhook URL plus a matching secret.",
  },
  {
    label: "Connect Razorpay",
    body: "Paste the webhook into Razorpay. Optionally add API credentials to import historical subscription data.",
  },
  {
    label: "See the full picture",
    body: "Track net new MRR, plan movement, cohorts, and pipeline signals as events start flowing in.",
  },
];

const stats = [
  { value: "Webhook-first", label: "Start with future events only" },
  { value: "Backfill-ready", label: "Layer in historical data later" },
  { value: "Real-time", label: "Kafka to dashboard in one stream" },
];

export default function LandingPage({ onGetStarted, onSignIn }: LandingPageProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[var(--bg-0)] text-white">
      <div className="orb orb-cyan" />
      <div className="orb orb-rose" />
      <div className="orb orb-amber" />
      <div className="noise-overlay" />

      <div className="relative mx-auto max-w-7xl px-4 pb-20 pt-6 sm:px-6 lg:px-8">
        <header className="landing-surface stagger-fade delay-1 flex items-center justify-between px-5 py-4 sm:px-6">
          <div>
            <p className="text-2xl font-semibold tracking-tight text-white">RazorScope</p>
            <p className="text-sm text-slate-400">Subscription analytics for Razorpay teams</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onSignIn}
              className="rounded-full border border-white/12 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:border-white/20 hover:bg-white/10"
            >
              Sign in
            </button>
            <button
              onClick={onGetStarted}
              className="rounded-full bg-[var(--brand)] px-5 py-2 text-sm font-medium text-slate-950 transition hover:brightness-110"
            >
              Start free
            </button>
          </div>
        </header>

        <section className="grid gap-8 pt-8 lg:grid-cols-[1.02fr_0.98fr] lg:pt-10">
          <div className="space-y-8">
            <div className="stagger-fade delay-2 max-w-2xl space-y-6">
              <span className="metric-pill">Webhook-native revenue intelligence</span>
              <div className="space-y-5">
                <h1 className="text-balance text-5xl font-semibold leading-[1.03] tracking-tight text-white sm:text-6xl lg:text-7xl">
                  The animated revenue command center your Razorpay data deserves.
                </h1>
                <p className="max-w-xl text-base leading-8 text-slate-300 sm:text-lg">
                  RazorScope turns subscription events into a living story of growth, churn, retention,
                  plan movement, and operator signals. Plug in fast, then deepen the sync when you want
                  full historical context.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <button
                  onClick={onGetStarted}
                  className="rounded-full bg-[var(--brand)] px-6 py-3 text-base font-semibold text-slate-950 transition hover:brightness-110"
                >
                  Create workspace
                </button>
                <button
                  onClick={onSignIn}
                  className="rounded-full border border-white/14 bg-white/5 px-6 py-3 text-base font-medium text-white transition hover:border-white/25 hover:bg-white/10"
                >
                  View live dashboard
                </button>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              {stats.map((stat, index) => (
                <div
                  key={stat.label}
                  className={`glass-card reveal-rise p-5 ${index === 0 ? "delay-2" : index === 1 ? "delay-3" : "delay-4"}`}
                >
                  <p className="text-lg font-semibold text-white">{stat.value}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="stagger-fade delay-3">
            <div className="landing-surface dashboard-float relative overflow-hidden p-5 sm:p-6">
              <div className="scan-line" />
              <div className="landing-grid absolute inset-0 opacity-35" />
              <div className="hero-glow absolute right-[-7rem] top-[-7rem] h-64 w-64 rounded-full bg-emerald-400/15 blur-3xl" />

              <div className="relative space-y-5">
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.32em] text-slate-400">Live merchant</p>
                    <p className="mt-2 text-xl font-semibold text-white">tiqo growth workspace</p>
                  </div>
                  <div className="rounded-full bg-emerald-400/15 px-3 py-1 text-xs font-medium text-emerald-200">
                    Events flowing
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="glass-card p-4">
                    <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Net New MRR</p>
                    <p className="mt-3 text-3xl font-semibold text-emerald-300">+INR 4,000</p>
                  </div>
                  <div className="glass-card p-4">
                    <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Closing MRR</p>
                    <p className="mt-3 text-3xl font-semibold text-white">INR 48,000</p>
                  </div>
                  <div className="glass-card p-4">
                    <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Retention</p>
                    <p className="mt-3 text-3xl font-semibold text-cyan-200">92%</p>
                  </div>
                </div>

                <div className="glass-card p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-white">MRR Movement</p>
                      <p className="mt-1 text-sm text-slate-400">Last 6 months</p>
                    </div>
                    <span className="metric-pill bg-white/8 text-white/80">Animated preview</span>
                  </div>

                  <div className="mt-6 flex h-48 items-end gap-3">
                    {[36, 56, 44, 72, 64, 96].map((height, index) => (
                      <div key={height} className="flex flex-1 flex-col items-center gap-3">
                        <div
                          className="chart-bar w-full rounded-t-2xl bg-gradient-to-t from-[#34d399] via-[#7ff7cb] to-[#b2fce4] shadow-[0_0_40px_rgba(127,247,203,0.20)]"
                          style={{ height: `${height}%`, animationDelay: `${index * 140}ms` }}
                        />
                        <span className="text-xs text-slate-500">
                          {["Nov", "Dec", "Jan", "Feb", "Mar", "Apr"][index]}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                  <div className="glass-card p-5">
                    <p className="text-sm font-medium text-white">Connection modes</p>
                    <div className="mt-4 space-y-3">
                      <div className="rounded-2xl border border-cyan-300/15 bg-cyan-300/5 p-4">
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-white">Basic Mode</p>
                          <span className="metric-pill bg-cyan-300/10 text-cyan-100">Webhook only</span>
                        </div>
                        <p className="mt-2 text-sm text-slate-300">
                          Copy URL and secret into Razorpay. Start collecting future events immediately.
                        </p>
                      </div>
                      <div className="rounded-2xl border border-amber-300/15 bg-amber-300/5 p-4">
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-white">Advanced Mode</p>
                          <span className="metric-pill bg-amber-300/10 text-amber-100">Backfill</span>
                        </div>
                        <p className="mt-2 text-sm text-slate-300">
                          Add Razorpay API credentials to import historical subscriptions and unlock full context.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="glass-card p-5">
                    <p className="text-sm font-medium text-white">Signal stack</p>
                    <div className="mt-4 space-y-3">
                      {["Webhooks", "Kafka", "Metric worker", "MRR + cohorts", "CRM + audit log"].map((item, index) => (
                        <div key={item} className="flex items-center gap-3 text-sm text-slate-300">
                          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/8 text-xs text-white">
                            {index + 1}
                          </span>
                          {item}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-5 pt-10 lg:grid-cols-3">
          {featureCards.map((card, index) => (
            <article
              key={card.title}
              className={`landing-surface reveal-rise p-6 ${index === 0 ? "delay-2" : index === 1 ? "delay-3" : "delay-4"}`}
            >
              <card.icon size={20} className="text-[var(--brand)] mb-3" />
              <p className="section-kicker">Why teams switch</p>
              <h2 className="mt-3 text-2xl font-semibold text-white">{card.title}</h2>
              <p className="mt-4 text-sm leading-7 text-slate-300">{card.body}</p>
            </article>
          ))}
        </section>

        <section className="pt-10">
          <SetupGuide
            audience="public"
            onPrimaryAction={onGetStarted}
            onSecondaryAction={onSignIn}
          />
        </section>

        <section className="grid gap-6 pt-10 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="landing-surface reveal-rise delay-2 p-7">
            <p className="section-kicker">How it works</p>
            <h2 className="mt-3 text-3xl font-semibold text-white">
              Start lightweight. Grow into the full operating system.
            </h2>
            <p className="mt-4 max-w-xl text-sm leading-7 text-slate-300">
              The onboarding path is intentionally split. New teams can get signal fast with webhooks,
              while finance and growth teams can later add secure API credentials for backfill.
            </p>
          </div>

          <div className="space-y-4">
            {steps.map((step, index) => (
              <div
                key={step.label}
                className={`landing-surface reveal-rise flex gap-4 p-5 ${index === 0 ? "delay-2" : index === 1 ? "delay-3" : "delay-4"}`}
              >
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white/8 text-sm font-semibold text-white">
                  0{index + 1}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">{step.label}</h3>
                  <p className="mt-2 text-sm leading-7 text-slate-300">{step.body}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="pt-10">
          <div className="landing-surface reveal-rise delay-3 relative overflow-hidden px-6 py-8 sm:px-8">
            <div className="hero-glow absolute inset-y-0 right-[-10rem] w-80 rounded-full bg-[var(--brand)]/10 blur-3xl" />
            <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-2xl">
                <p className="section-kicker">Ready to move</p>
                <h2 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">
                  Put your Razorpay revenue story on a screen your team will actually watch.
                </h2>
                <p className="mt-4 text-sm leading-7 text-slate-300 sm:text-base">
                  Create a workspace, connect Razorpay in basic mode, then deepen the sync when you are ready
                  for historical backfill and long-range reporting.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <button
                  onClick={onGetStarted}
                  className="rounded-full bg-[var(--brand)] px-6 py-3 text-base font-semibold text-slate-950 transition hover:brightness-110"
                >
                  Build my workspace
                </button>
                <button
                  onClick={onSignIn}
                  className="rounded-full border border-white/14 bg-white/5 px-6 py-3 text-base font-medium text-white transition hover:border-white/25 hover:bg-white/10"
                >
                  Sign in
                </button>
              </div>
            </div>
          </div>
        </section>
        <footer className="pt-10 pb-6 text-center text-xs text-[var(--text-muted)]">
          © {new Date().getFullYear()} RazorScope. Subscription analytics for Razorpay teams.
        </footer>
      </div>
    </div>
  );
}
