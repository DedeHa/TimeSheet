"""Unit tests for ci_stats.py (PRO-380 statistical enhancement).

Tests all pure statistical functions: compute_rolling_stats,
compute_bollinger_bands, compute_normal_distribution.
Standard-library only.
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import ci_stats  # noqa: E402


def test_rolling_mean_known_values():
    """compute_rolling_stats returns correct rolling mean for 20-run window."""
    values = list(range(1, 26))  # [1..25]
    results = ci_stats.compute_rolling_stats(values, window=20)
    assert len(results) == 6
    assert results[0]["start"] == 1
    assert results[0]["end"] == 20
    assert results[0]["mean"] == 10.5
    assert results[-1]["start"] == 6
    assert results[-1]["end"] == 25
    assert results[-1]["mean"] == 15.5


def test_rolling_mean_exactly_20_values():
    """compute_rolling_stats with exactly 20 values returns 1 result."""
    values = list(range(1, 21))
    results = ci_stats.compute_rolling_stats(values, window=20)
    assert len(results) == 1
    assert results[0]["start"] == 1
    assert results[0]["end"] == 20


def test_rolling_mean_under_20_values():
    """compute_rolling_stats with fewer than window values returns empty list."""
    values = list(range(1, 15))
    results = ci_stats.compute_rolling_stats(values, window=20)
    assert results == []


def test_rolling_mean_empty():
    """compute_rolling_stats with empty list returns empty list."""
    results = ci_stats.compute_rolling_stats([], window=20)
    assert results == []


def test_rolling_mean_uses_stdev():
    """compute_rolling_stats uses sample stddev (statistics.stdev)."""
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0] * 3
    results = ci_stats.compute_rolling_stats(values, window=20)
    expected_stdev = statistics.stdev(values[:20])
    assert abs(results[0]["stddev"] - expected_stdev) < 1e-10


def test_bollinger_constant_values():
    """compute_bollinger_bands with all equal values → upper = lower = mean."""
    values = [5.0] * 25
    results = ci_stats.compute_bollinger_bands(values, window=20, k=2)
    assert len(results) == 6
    for r in results:
        assert r["upper"] == r["lower"] == r["mean"] == 5.0


def test_bollinger_bounds_contain_mean():
    """compute_bollinger_bands bounds contain the mean for all windows."""
    values = list(range(1, 51))
    results = ci_stats.compute_bollinger_bands(values, window=20, k=2)
    for r in results:
        assert r["lower"] <= r["mean"] <= r["upper"]


def test_bollinger_under_20_values():
    """compute_bollinger_bands with fewer than window values returns empty list."""
    results = ci_stats.compute_bollinger_bands([1, 2, 3], window=20, k=2)
    assert results == []


def test_bollinger_k_parameter():
    """compute_bollinger_bands respects k parameter."""
    values = list(range(1, 26))
    results_k1 = ci_stats.compute_bollinger_bands(values, window=20, k=1)
    results_k2 = ci_stats.compute_bollinger_bands(values, window=20, k=2)
    assert len(results_k1) == 6
    assert len(results_k2) == 6
    # k=2 bounds should be wider than k=1
    range_k1 = results_k1[0]["upper"] - results_k1[0]["lower"]
    range_k2 = results_k2[0]["upper"] - results_k2[0]["lower"]
    assert range_k2 > range_k1


def test_normal_dist_params_known_dataset():
    """compute_normal_distribution returns correct μ and σ."""
    values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    result = ci_stats.compute_normal_distribution(values)
    assert round(result["mean"], 10) == round(statistics.mean(values), 10)
    assert round(result["stddev"], 10) == round(statistics.stdev(values), 10)
    assert len(result["curve"]) > 0


def test_normal_dist_empty():
    """compute_normal_distribution with empty list returns zeroed result."""
    result = ci_stats.compute_normal_distribution([])
    assert result["mean"] == 0.0
    assert result["stddev"] == 0.0
    assert result["curve"] == []


def test_normal_dist_single_value():
    """compute_normal_distribution with one value returns curve with single point."""
    result = ci_stats.compute_normal_distribution([5.0])
    assert result["mean"] == 5.0
    assert result["stddev"] == 0.0
    assert len(result["curve"]) == 1
    assert result["curve"][0]["x"] == 5.0
    assert result["curve"][0]["y"] == 1.0


def test_normal_dist_curve_range():
    """compute_normal_distribution curve spans μ − 3σ to μ + 3σ."""
    values = list(range(1, 101))
    result = ci_stats.compute_normal_distribution(values)
    curve = result["curve"]
    mu = result["mean"]
    sigma = result["stddev"]
    assert curve[0]["x"] <= mu - 3 * sigma
    assert curve[-1]["x"] >= mu + 3 * sigma


def test_schema_version():
    """Verify metrics.json schema_version stays v1.0 after integration."""
    import json
    from pathlib import Path

    metrics_path = Path(__file__).resolve().parents[3] / "data" / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert data.get("schema_version") == "v1.0"
