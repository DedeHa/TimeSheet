"""Pure statistical functions for the CI timing benchmark (PRO-380).

Implements FR-19 (rolling stats, Bollinger bands, normal distribution)
and QR-12 (CI timing traceability via verifiable pure functions).

All functions are standard-library only.
"""

from __future__ import annotations

import math
import statistics
from typing import Any


def compute_rolling_stats(
    values: list[float], window: int = 20
) -> list[dict[str, Any]]:
    """Compute rolling mean and sample stddev over a sliding window.

    Returns a list of dicts with keys ``start``, ``end``, ``mean``,
    ``stddev``. Returns an empty list when fewer than ``window`` values
    are provided.
    """
    if len(values) < window:
        return []
    results: list[dict[str, Any]] = []
    for i in range(len(values) - window + 1):
        chunk = values[i : i + window]
        results.append(
            {
                "start": i + 1,
                "end": i + window,
                "mean": statistics.mean(chunk),
                "stddev": statistics.stdev(chunk),
            }
        )
    return results


def compute_bollinger_bands(
    values: list[float], window: int = 20, k: float = 2.0
) -> list[dict[str, Any]]:
    """Compute Bollinger bands (mean ± k·stddev) over a sliding window.

    Returns a list of dicts with keys ``start``, ``end``, ``mean``,
    ``upper``, ``lower``. Returns an empty list when fewer than
    ``window`` values are provided.
    """
    if len(values) < window:
        return []
    results: list[dict[str, Any]] = []
    for i in range(len(values) - window + 1):
        chunk = values[i : i + window]
        mean = statistics.mean(chunk)
        std = statistics.stdev(chunk)
        results.append(
            {
                "start": i + 1,
                "end": i + window,
                "mean": mean,
                "upper": mean + k * std,
                "lower": mean - k * std,
            }
        )
    return results


def compute_normal_distribution(values: list[float]) -> dict[str, Any]:
    """Return normal distribution parameters (μ, σ) and a PDF curve.

    The ``curve`` key contains a list of dicts ``{"x": float, "y": float}``
    sampled from μ − 3σ to μ + 3σ. Returns ``{"mean": 0, "stddev": 0,
    "curve": []}`` for an empty input list.
    """
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "curve": []}
    mu = statistics.mean(values)
    sigma = statistics.stdev(values) if len(values) > 1 else 0.0
    if sigma == 0:
        return {"mean": mu, "stddev": sigma, "curve": [{"x": mu, "y": 1.0}]}

    curve: list[dict[str, float]] = []
    lo = mu - 3 * sigma
    hi = mu + 3 * sigma
    steps = 60
    for j in range(steps + 1):
        x = lo + (hi - lo) * j / steps
        y = (
            1.0
            / (sigma * math.sqrt(2 * math.pi))
            * math.exp(-0.5 * ((x - mu) / sigma) ** 2)
        )
        curve.append({"x": x, "y": y})
    return {"mean": mu, "stddev": sigma, "curve": curve}
