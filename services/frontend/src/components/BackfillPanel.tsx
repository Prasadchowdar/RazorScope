import { useEffect, useState } from "react";
import type { BackfillJob } from "../api/backfill";
import { createBackfillJob, listBackfillJobs } from "../api/backfill";
import { useAuth } from "../context/AuthContext";

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  running: "bg-blue-100 text-blue-700",
  done: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

function currentYearMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function oneYearAgo() {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export default function BackfillPanel({
  enabled = true,
  lockedMessage = "Connect Razorpay API credentials to unlock historical backfill.",
}: {
  enabled?: boolean;
  lockedMessage?: string;
}) {
  const { accessToken } = useAuth();
  const [jobs, setJobs] = useState<BackfillJob[]>([]);
  const [fromDate, setFromDate] = useState(oneYearAgo());
  const [toDate, setToDate] = useState(currentYearMonth());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadJobs() {
    if (!accessToken) return;
    try {
      const list = await listBackfillJobs(accessToken);
      setJobs(list);
    } catch {
      // Ignore polling errors to avoid noisy UI churn during temporary failures.
    }
  }

  useEffect(() => {
    loadJobs();
    const id = setInterval(loadJobs, 5000);
    return () => clearInterval(id);
  }, [accessToken]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!enabled) return;

    setError(null);
    setSubmitting(true);
    try {
      await createBackfillJob(accessToken!, fromDate, toDate);
      await loadJobs();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setError(msg ?? "Failed to create backfill job.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-base font-semibold text-gray-800 mb-1">
          Import Historical Data
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Import historical Razorpay subscription data to populate your MRR charts.
          The import runs in the background - check progress below.
        </p>
        {!enabled && (
          <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            {lockedMessage}
          </div>
        )}
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">From (YYYY-MM)</label>
            <input
              type="month"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              disabled={!enabled}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 disabled:bg-gray-50 disabled:text-gray-400"
              required
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">To (YYYY-MM)</label>
            <input
              type="month"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              disabled={!enabled}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 disabled:bg-gray-50 disabled:text-gray-400"
              required
            />
          </div>
          <button
            type="submit"
            disabled={submitting || !enabled}
            className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Starting..." : "Start Import"}
          </button>
        </form>
        {error && <p className="text-sm text-red-500 mt-3">{error}</p>}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700">Import Jobs</h3>
        </div>
        {jobs.length === 0 ? (
          <p className="px-6 py-8 text-sm text-gray-400 text-center">
            No import jobs yet. Start one above.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-6 py-3 text-left">Range</th>
                <th className="px-6 py-3 text-left">Status</th>
                <th className="px-6 py-3 text-left">Progress</th>
                <th className="px-6 py-3 text-left">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {jobs.map((job) => {
                const pct = job.total_pages
                  ? Math.round((job.pages_fetched / job.total_pages) * 100)
                  : job.status === "done"
                    ? 100
                    : 0;

                return (
                  <tr key={job.job_id}>
                    <td className="px-6 py-3 text-gray-600 font-mono text-xs">
                      {job.from_date?.slice(0, 7)} {"->"} {job.to_date?.slice(0, 7)}
                    </td>
                    <td className="px-6 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          STATUS_BADGE[job.status] ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-400">
                          {job.status === "done"
                            ? "Done"
                            : job.status === "failed"
                              ? "Failed"
                              : `${job.pages_fetched} pages`}
                        </span>
                      </div>
                      {job.error_detail && (
                        <p className="text-xs text-red-500 mt-0.5">{job.error_detail}</p>
                      )}
                    </td>
                    <td className="px-6 py-3 text-gray-400 text-xs">
                      {job.created_at ? new Date(job.created_at).toLocaleString() : "-"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
