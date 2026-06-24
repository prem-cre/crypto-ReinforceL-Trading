"""SHAP-based feature attribution for the RL trading agent.

Uses KernelSHAP (model-agnostic) to explain why the PPO agent chose
BUY/SELL/HOLD at any given state. This is critical for:
  1. Regulatory compliance — explainable trading decisions
  2. Debugging — which features are driving bad trades
  3. Resume signal — shows interpretable ML competence

The explainer wraps the PPO policy's action probability output and
returns per-feature SHAP values for each action class.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "trend",           # UP=1, DOWN=-1, SIDEWAYS=0
    "volatility",      # HIGH=1, MED=0.5, LOW=0
    "volume",          # HIGH=1, MED=0.5, LOW=0
    "momentum",        # STRONG=1, WEAK=-1, NEUTRAL=0
    "regime",          # BULL=1, BEAR=-1
    "position_type",   # LONG=1, SHORT=-1, NONE=0
    "position_pnl",    # unrealised PnL %
    "drawdown",        # current drawdown from peak
    "rsi_scaled",      # (RSI-50)/50
    "macd_scaled",     # MACD_hist / close
]

ACTION_NAMES = ["BUY", "SELL", "HOLD"]


class SHAPExplainer:
    """Model-agnostic SHAP explainer for the PPO actor-critic policy."""

    def __init__(self, policy_fn=None, feature_names: Optional[List[str]] = None):
        """
        Args:
            policy_fn: callable(np.ndarray) -> np.ndarray of action probs
            feature_names: names for each state dimension
        """
        self._policy_fn = policy_fn
        self.feature_names = feature_names or FEATURE_NAMES
        self._background: Optional[np.ndarray] = None

    def set_policy(self, policy_fn) -> None:
        self._policy_fn = policy_fn

    def set_background(self, background_states: np.ndarray) -> None:
        """Set background dataset for SHAP (typically 50-100 representative states)."""
        self._background = background_states

    def _model_predict(self, states: np.ndarray) -> np.ndarray:
        """Wrapper that returns action probabilities for a batch of states."""
        if self._policy_fn is None:
            return np.ones((len(states), 3)) / 3.0
        results = []
        for s in states:
            probs = self._policy_fn(s)
            results.append(probs)
        return np.array(results)

    def explain(self, state: np.ndarray, n_samples: int = 100) -> Dict[str, Any]:
        """Compute SHAP values for a single state using permutation-based approximation.

        Uses a fast permutation approach instead of full KernelSHAP to avoid
        the shap library dependency in production.
        """
        if self._background is None:
            self._background = np.random.randn(50, len(state)).astype(np.float32) * 0.1

        base_probs = self._model_predict(state.reshape(1, -1))[0]
        n_features = len(state)
        shap_values = np.zeros((3, n_features))  # (actions, features)

        for _ in range(n_samples):
            perm = np.random.permutation(n_features)
            bg_idx = np.random.randint(len(self._background))
            bg = self._background[bg_idx].copy()

            x_with = bg.copy()
            x_without = bg.copy()

            for feat_idx in perm:
                x_with[feat_idx] = state[feat_idx]
                probs_with = self._model_predict(x_with.reshape(1, -1))[0]
                probs_without = self._model_predict(x_without.reshape(1, -1))[0]
                marginal = probs_with - probs_without
                shap_values[:, feat_idx] += marginal
                x_without[feat_idx] = state[feat_idx]

        shap_values /= n_samples

        chosen_action = int(np.argmax(base_probs))

        # Build ranked feature importance for the chosen action
        action_shap = shap_values[chosen_action]
        ranked_indices = np.argsort(np.abs(action_shap))[::-1]

        feature_importance = []
        for idx in ranked_indices:
            name = self.feature_names[idx] if idx < len(self.feature_names) else f"feature_{idx}"
            feature_importance.append({
                "feature": name,
                "value": round(float(state[idx]), 4),
                "shap_value": round(float(action_shap[idx]), 6),
                "direction": "positive" if action_shap[idx] > 0 else "negative",
                "abs_importance": round(abs(float(action_shap[idx])), 6),
            })

        return {
            "action": ACTION_NAMES[chosen_action],
            "action_probs": {
                ACTION_NAMES[i]: round(float(base_probs[i]), 4)
                for i in range(3)
            },
            "feature_importance": feature_importance,
            "shap_values": {
                ACTION_NAMES[i]: [round(float(v), 6) for v in shap_values[i]]
                for i in range(3)
            },
            "top_drivers": [
                {
                    "feature": feature_importance[i]["feature"],
                    "impact": feature_importance[i]["shap_value"],
                    "direction": feature_importance[i]["direction"],
                }
                for i in range(min(5, len(feature_importance)))
            ],
        }

    def explain_batch(self, states: np.ndarray, n_samples: int = 50) -> List[Dict[str, Any]]:
        """Explain multiple states (e.g., for a backtest trajectory)."""
        return [self.explain(s, n_samples=n_samples) for s in states]

    def feature_importance_summary(self, states: np.ndarray,
                                    n_samples: int = 50) -> Dict[str, Any]:
        """Aggregate SHAP importance across many states → global feature ranking."""
        explanations = self.explain_batch(states, n_samples=n_samples)

        n_features = len(self.feature_names)
        global_importance = np.zeros(n_features)

        for exp in explanations:
            for fi in exp["feature_importance"]:
                idx = self.feature_names.index(fi["feature"]) if fi["feature"] in self.feature_names else -1
                if idx >= 0:
                    global_importance[idx] += fi["abs_importance"]

        global_importance /= max(len(explanations), 1)
        ranked = np.argsort(global_importance)[::-1]

        return {
            "global_ranking": [
                {
                    "rank": i + 1,
                    "feature": self.feature_names[idx],
                    "mean_abs_shap": round(float(global_importance[idx]), 6),
                }
                for i, idx in enumerate(ranked)
            ],
            "n_states_explained": len(explanations),
        }
