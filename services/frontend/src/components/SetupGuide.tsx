interface SetupGuideProps {
  audience: "public" | "private";
  onPrimaryAction?: () => void;
  onSecondaryAction?: () => void;
  onOpenSettings?: () => void;
}

const setupSteps = [
  {
    id: "01",
    title: "Create your workspace",
    body:
      "Sign up in RazorScope and your merchant gets a webhook URL plus a matching webhook secret immediately.",
  },
  {
    id: "02",
    title: "Choose Basic or Advanced mode",
    body:
      "Basic mode is webhook-only for future events. Advanced mode adds Razorpay API credentials so you can backfill historical subscriptions.",
  },
  {
    id: "03",
    title: "Connect Razorpay",
    body:
      "Paste the webhook URL and webhook secret into Razorpay. If you need old data too, save your Razorpay Key ID and Key Secret inside RazorScope Settings.",
  },
  {
    id: "04",
    title: "Verify the feed",
    body:
      "Send a test-mode or live subscription event, then watch MRR, cohorts, benchmarks, and CRM signals update inside the dashboard.",
  },
];

const requirements = [
  "Razorpay account",
  "Webhook URL and webhook secret from RazorScope",
  "Optional Razorpay Key ID and Key Secret for backfill",
  "A test or live subscription event to verify ingestion",
];

export default function SetupGuide({
  audience,
  onPrimaryAction,
  onSecondaryAction,
  onOpenSettings,
}: SetupGuideProps) {
  const isPublic = audience === "public";

  return (
    <section className="landing-surface reveal-rise delay-2 p-6 sm:p-8">
      <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-5">
          <p className="section-kicker">Setup Guide</p>
          <h2 className="text-3xl font-semibold text-white sm:text-4xl">
            How to connect RazorScope with Razorpay without guessing.
          </h2>
          <p className="max-w-xl text-sm leading-7 text-slate-300 sm:text-base">
            This guide is the same story whether you are evaluating RazorScope from the landing page
            or connecting a real workspace after login: start fast with webhooks, then deepen the
            connection when you want historical analytics too.
          </p>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="glass-card p-5">
              <div className="flex items-center justify-between">
                <p className="text-lg font-semibold text-white">Basic Mode</p>
                <span className="metric-pill bg-cyan-300/10 text-cyan-100">Fastest path</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                Copy the webhook URL and webhook secret into Razorpay. New events begin flowing from
                that point forward.
              </p>
            </div>

            <div className="glass-card p-5">
              <div className="flex items-center justify-between">
                <p className="text-lg font-semibold text-white">Advanced Mode</p>
                <span className="metric-pill bg-amber-300/10 text-amber-100">Backfill ready</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                Save your Razorpay Key ID and Key Secret inside RazorScope to run historical backfill
                and see past plus future analytics on one timeline.
              </p>
            </div>
          </div>

          <div className="glass-card p-5">
            <p className="text-sm font-medium text-white">What you need</p>
            <ul className="mt-4 space-y-3 text-sm text-slate-300">
              {requirements.map((item, index) => (
                <li key={item} className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/8 text-xs text-white">
                    {index + 1}
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            {isPublic ? (
              <>
                <button
                  onClick={onPrimaryAction}
                  className="rounded-full bg-[var(--brand)] px-6 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110"
                >
                  Create workspace
                </button>
                <button
                  onClick={onSecondaryAction}
                  className="rounded-full border border-white/14 bg-white/5 px-6 py-3 text-sm font-medium text-white transition hover:border-white/25 hover:bg-white/10"
                >
                  Sign in
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={onOpenSettings}
                  className="rounded-full bg-[var(--brand)] px-6 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110"
                >
                  Open connection settings
                </button>
                <p className="self-center text-sm text-slate-400">
                  Settings is where you copy webhook details and save API credentials.
                </p>
              </>
            )}
          </div>
        </div>

        <div className="space-y-4">
          {setupSteps.map((step, index) => (
            <div
              key={step.id}
              className={`glass-card flex gap-4 p-5 ${index === 0 ? "delay-2" : index === 1 ? "delay-3" : index === 2 ? "delay-4" : "delay-5"} reveal-rise`}
            >
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white/8 text-sm font-semibold text-white">
                {step.id}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">{step.title}</h3>
                <p className="mt-2 text-sm leading-7 text-slate-300">{step.body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
