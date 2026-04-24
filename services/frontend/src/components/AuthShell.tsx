import type { ReactNode } from "react";

interface AuthShellProps {
  title: string;
  subtitle: string;
  eyebrow?: string;
  badge?: string;
  sideTitle?: string;
  sideDescription?: string;
  sideChildren?: ReactNode;
  footer?: ReactNode;
  onBackClick?: () => void;
  children: ReactNode;
}

export default function AuthShell({
  title,
  subtitle,
  eyebrow,
  badge,
  sideTitle,
  sideDescription,
  sideChildren,
  footer,
  onBackClick,
  children,
}: AuthShellProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[var(--bg-0)] text-slate-100">
      <div className="orb orb-rose" />
      <div className="orb orb-cyan" />
      <div className="orb orb-amber" />
      <div className="noise-overlay" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-7xl items-center px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid w-full gap-8 lg:grid-cols-[1.05fr_0.95fr]">
          <section className="landing-surface stagger-fade delay-1 relative overflow-hidden p-8 sm:p-10">
            <div className="landing-grid absolute inset-0 opacity-40" />
            <div className="hero-glow absolute left-[-8rem] top-[-8rem] h-64 w-64 rounded-full bg-cyan-400/20 blur-3xl" />

            <div className="relative flex h-full flex-col justify-between gap-8">
              <div className="space-y-6">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="metric-pill">RazorScope</span>
                  {badge ? <span className="metric-pill bg-white/10 text-white/80">{badge}</span> : null}
                </div>

                <div className="max-w-xl space-y-4">
                  {eyebrow ? <p className="section-kicker">{eyebrow}</p> : null}
                  <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                    {title}
                  </h1>
                  <p className="max-w-lg text-base leading-7 text-slate-300 sm:text-lg">
                    {subtitle}
                  </p>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="glass-card reveal-rise delay-2 p-5">
                  <p className="text-xs uppercase tracking-[0.32em] text-cyan-200/70">Live Signal</p>
                  <p className="mt-3 text-3xl font-semibold text-white">+4.0k MRR</p>
                  <p className="mt-2 text-sm text-slate-300">
                    Real webhook activity, cohort retention, and revenue movement in one stream.
                  </p>
                </div>
                <div className="glass-card reveal-rise delay-3 p-5">
                  <p className="text-xs uppercase tracking-[0.32em] text-amber-200/70">Time To First Value</p>
                  <p className="mt-3 text-3xl font-semibold text-white">&lt;10 min</p>
                  <p className="mt-2 text-sm text-slate-300">
                    Start with webhook-only. Add API keys later when you want backfill.
                  </p>
                </div>
              </div>

              <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
                <div className="glass-card reveal-rise delay-4 p-5">
                  {sideTitle ? <h2 className="text-lg font-semibold text-white">{sideTitle}</h2> : null}
                  {sideDescription ? (
                    <p className="mt-2 text-sm leading-6 text-slate-300">{sideDescription}</p>
                  ) : null}
                  {sideChildren ? <div className="mt-5">{sideChildren}</div> : null}
                </div>

                <div className="glass-card reveal-rise delay-5 p-5">
                  <p className="text-xs uppercase tracking-[0.32em] text-slate-400">Flow</p>
                  <ul className="mt-4 space-y-3 text-sm text-slate-300">
                    <li className="flex items-center gap-3">
                      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-xs text-white">
                        01
                      </span>
                      Create workspace
                    </li>
                    <li className="flex items-center gap-3">
                      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-xs text-white">
                        02
                      </span>
                      Connect Razorpay
                    </li>
                    <li className="flex items-center gap-3">
                      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-xs text-white">
                        03
                      </span>
                      Watch revenue move
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </section>

          <section className="landing-surface stagger-fade delay-2 relative p-6 sm:p-8">
            <div className="absolute right-6 top-6">
              {onBackClick ? (
                <button
                  onClick={onBackClick}
                  className="rounded-full border border-white/12 bg-white/6 px-4 py-2 text-sm text-slate-200 transition hover:border-white/20 hover:bg-white/10"
                >
                  Back
                </button>
              ) : null}
            </div>

            <div className="mx-auto flex max-w-md flex-col justify-center pt-10 lg:min-h-[720px]">
              {eyebrow ? <p className="section-kicker mb-4">{eyebrow}</p> : null}
              <h2 className="text-3xl font-semibold text-white">{title}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-300">{subtitle}</p>

              <div className="mt-8">{children}</div>

              {footer ? <div className="mt-6 text-sm text-slate-400">{footer}</div> : null}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
