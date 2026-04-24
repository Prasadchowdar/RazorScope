"""
Industry benchmark percentile tables for SaaS subscription metrics.

Data sourced from: ChartMogul SaaS Benchmarks Report 2024, SaaS Capital Index,
OpenView SaaS Benchmarks, and Bessemer State of the Cloud (public reports).

All percentile tables are ordered [P10, P25, P50, P75, P90].
For metrics where LOWER is better (churn), P10 = best performers.
For metrics where HIGHER is better (NRR, growth), P10 = weakest performers.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import Literal


@dataclass
class BenchmarkSeries:
    name: str
    description: str
    unit: str                          # "pct" | "rupees" | "months"
    direction: Literal["higher", "lower"]   # higher = better or lower = better
    percentiles: list[float]           # [P10, P25, P50, P75, P90] values
    p_labels: list[int] = None         # default [10, 25, 50, 75, 90]

    def __post_init__(self):
        if self.p_labels is None:
            self.p_labels = [10, 25, 50, 75, 90]

    def merchant_percentile(self, value: float) -> float:
        """
        Estimate which percentile the merchant's value falls in (0–100).
        Uses linear interpolation between known breakpoints.
        """
        vals = self.percentiles
        labels = self.p_labels

        if self.direction == "lower":
            # For lower-is-better: a lower value is a HIGHER percentile
            # Flip: percentile = 100 - percentile_in_sorted_ascending_order
            if value <= vals[0]:
                return float(labels[-1])     # best bucket
            if value >= vals[-1]:
                return float(100 - labels[-1])
            for i in range(len(vals) - 1):
                if vals[i] <= value <= vals[i + 1]:
                    frac = (value - vals[i]) / (vals[i + 1] - vals[i])
                    raw = labels[i] + frac * (labels[i + 1] - labels[i])
                    return round(100 - raw, 1)
        else:
            # Higher-is-better
            if value <= vals[0]:
                return float(labels[0])
            if value >= vals[-1]:
                return float(labels[-1])
            for i in range(len(vals) - 1):
                if vals[i] <= value <= vals[i + 1]:
                    frac = (value - vals[i]) / (vals[i + 1] - vals[i])
                    return round(labels[i] + frac * (labels[i + 1] - labels[i]), 1)
        return 50.0

    def label_for_percentile(self, pct: float) -> str:
        if pct >= 75:
            return "top quartile"
        if pct >= 50:
            return "above median"
        if pct >= 25:
            return "below median"
        return "bottom quartile"


# ── Benchmark definitions ──────────────────────────────────────────────────────
# All monetary values are in INR paise (India-focused SaaS benchmarks).
# ARPU ranges calibrated for Indian B2B SaaS (₹5k–₹1L/month typical).

BENCHMARKS: dict[str, BenchmarkSeries] = {
    "mrr_growth_rate": BenchmarkSeries(
        name="MRR Growth Rate (MoM)",
        description="Month-over-month MRR growth percentage",
        unit="pct",
        direction="higher",
        percentiles=[-1.0, 1.0, 3.5, 8.0, 15.0],
    ),
    "customer_churn_rate": BenchmarkSeries(
        name="Customer Churn Rate (Monthly)",
        description="% of subscribers lost per month",
        unit="pct",
        direction="lower",
        percentiles=[0.5, 1.2, 2.5, 4.5, 7.5],
    ),
    "revenue_churn_rate": BenchmarkSeries(
        name="Revenue Churn Rate (Monthly)",
        description="% of MRR lost to churn per month",
        unit="pct",
        direction="lower",
        percentiles=[0.3, 0.8, 2.0, 3.5, 6.0],
    ),
    "nrr_pct": BenchmarkSeries(
        name="Net Revenue Retention",
        description="Closing MRR as % of opening MRR (expansion offset against churn)",
        unit="pct",
        direction="higher",
        percentiles=[88.0, 95.0, 102.0, 110.0, 125.0],
    ),
    "arpu_paise": BenchmarkSeries(
        name="ARPU (Monthly)",
        description="Average Revenue Per User",
        unit="rupees",
        direction="higher",
        percentiles=[50000, 200000, 750000, 2500000, 8000000],
    ),
}


def score(metric_key: str, value: float) -> dict:
    """Return benchmark comparison for one metric."""
    b = BENCHMARKS[metric_key]
    pct = b.merchant_percentile(value)
    return {
        "metric_key": metric_key,
        "name": b.name,
        "description": b.description,
        "unit": b.unit,
        "direction": b.direction,
        "merchant_value": value,
        "percentile": pct,
        "label": b.label_for_percentile(pct),
        "industry_p10": b.percentiles[0],
        "industry_p25": b.percentiles[1],
        "industry_p50": b.percentiles[2],
        "industry_p75": b.percentiles[3],
        "industry_p90": b.percentiles[4],
    }
