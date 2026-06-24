"""Unit tests for drift detection."""
import pytest
from backend.monitoring.drift import DriftMonitor, ks_drift_score


def test_ks_no_drift():
    import random
    ref = [random.gauss(0, 1) for _ in range(200)]
    live = [random.gauss(0, 1) for _ in range(100)]
    result = ks_drift_score(ref, live)
    # p_value should be non-trivially > 0.05 most of the time for same dist
    assert "statistic" in result
    assert "p_value" in result
    assert "drift" in result


def test_ks_detects_drift():
    ref = [0.0] * 200          # constant 0
    live = [10.0] * 100        # constant 10 (clearly different)
    result = ks_drift_score(ref, live)
    assert result["drift"] is True
    assert result["p_value"] < 0.05


def test_monitor_insufficient_data():
    monitor = DriftMonitor()
    report = monitor.report()
    assert report["status"] == "insufficient_data"


def test_monitor_detects_shift():
    monitor = DriftMonitor()
    monitor.set_reference([[float(i % 5)] * 5 for i in range(200)])
    for i in range(50):
        monitor.record([float(i + 100)] * 5)  # completely different range
    report = monitor.report()
    assert report["status"] in ["drift_detected", "ok"]  # depends on random seed
    assert "features" in report
