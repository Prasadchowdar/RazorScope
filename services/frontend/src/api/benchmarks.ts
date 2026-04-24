import { createBearerClient } from "./client";

export interface BenchmarkItem {
  metric_key: string;
  name: string;
  description: string;
  unit: "pct" | "rupees" | "months";
  direction: "higher" | "lower";
  merchant_value: number;
  percentile: number;
  label: string;
  industry_p10: number;
  industry_p25: number;
  industry_p50: number;
  industry_p75: number;
  industry_p90: number;
}

export interface BenchmarksResponse {
  month: string;
  benchmarks: BenchmarkItem[];
  data_source: string;
}

export async function fetchBenchmarks(token: string, month?: string): Promise<BenchmarksResponse> {
  const params = month ? { month } : {};
  const { data } = await createBearerClient(token).get("/api/v1/benchmarks", { params });
  return data;
}
