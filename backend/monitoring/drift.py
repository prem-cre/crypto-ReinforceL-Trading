"""Feature drift detection using Kolmogorov-Smirnov test.

Compares live feature distributions against a reference window captured
at training time. Reports per-feature drift scores for the /api/monitoring/drift
endpoint.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "trend", "volatility", "volume_ratio", "momentum", "regime",
    "position_type", "unrealized_pnl", "drawdown", "rsi_norm", "macd_norm",
]

DRIFT_THRESHOLD = 0.05  # p-value below this = significant drift


def ks_drift_score(reference: List[float], live: List[float]) -> Dict[str, float]:
    if len(reference) < 10 or len(live) < 10:
        return {"statistic": 0.0, "p_value": 1.0, "drift": False}
    stat, p_value = stats.ks_2samp(reference, live)
    return {
        "statistic": round(float(stat), 4),
        "p_value": round(float(p_value), 4),
        "drift": bool(p_value < DRIFT_THRESHOLD),
    }


class DriftMonitor:
    def __init__(self) -> None:
        self._reference: Optional[np.ndarray] = None
        self._live_buffer: List[np.ndarray] = []
        self._max_buffer = 500

    def set_reference(self, observations: List[List[float]]) -> None:
        self._reference = np.array(observations)
        logger.info(f"Drift reference set: {self._reference.shape}")

    def record(self, obs: List[float]) -> None:
        self._live_buffer.append(np.array(obs))
        if len(self._live_buffer) > self._max_buffer:
            self._live_buffer.pop(0)

    def report(self) -> Dict[str, Any]:
        if self._reference is None or len(self._live_buffer) < 20:
            return {"status": "insufficient_data", "features": {}}

        live = np.array(self._live_buffer)
        n_features = min(self._reference.shape[1], live.shape[1], len(FEATURE_NAMES))
        results: Dict[str, Any] = {}
        any_drift = False

        for i in range(n_features):
            name = FEATURE_NAMES[i]
            score = ks_drift_score(
                self._reference[:, i].tolist(),
                live[:, i].tolist(),
            )
            results[name] = score
            if score["drift"]:
                any_drift = True

        return {
            "status": "drift_detected" if any_drift else "ok",
            "live_samples": len(self._live_buffer),
            "reference_samples": len(self._reference),
            "features": results,
        }


# Process-wide singleton
drift_monitor = DriftMonitor()
