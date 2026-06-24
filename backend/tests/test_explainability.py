"""Tests for the SHAP explainability module."""
import numpy as np
import pytest

from backend.explainability.shap_explainer import SHAPExplainer, FEATURE_NAMES, ACTION_NAMES


class TestSHAPExplainer:
    @pytest.fixture
    def explainer(self):
        def dummy_policy(state):
            probs = np.array([0.5, 0.3, 0.2])
            if state[0] > 0:
                probs = np.array([0.7, 0.15, 0.15])
            elif state[0] < 0:
                probs = np.array([0.15, 0.7, 0.15])
            return probs

        return SHAPExplainer(policy_fn=dummy_policy)

    def test_explain_returns_structure(self, explainer):
        state = np.random.randn(10).astype(np.float32)
        result = explainer.explain(state, n_samples=20)
        assert "action" in result
        assert result["action"] in ACTION_NAMES
        assert "action_probs" in result
        assert "feature_importance" in result
        assert len(result["feature_importance"]) == 10
        assert "top_drivers" in result
        assert len(result["top_drivers"]) <= 5

    def test_explain_uptrend_favors_buy(self, explainer):
        state = np.zeros(10, dtype=np.float32)
        state[0] = 1.0  # strong uptrend
        result = explainer.explain(state, n_samples=30)
        assert result["action"] == "BUY"

    def test_explain_downtrend_favors_sell(self, explainer):
        state = np.zeros(10, dtype=np.float32)
        state[0] = -1.0  # strong downtrend
        result = explainer.explain(state, n_samples=30)
        assert result["action"] == "SELL"

    def test_feature_importance_has_shap_values(self, explainer):
        state = np.random.randn(10).astype(np.float32)
        result = explainer.explain(state, n_samples=20)
        for fi in result["feature_importance"]:
            assert "feature" in fi
            assert "shap_value" in fi
            assert "direction" in fi
            assert fi["direction"] in ["positive", "negative"]

    def test_explain_batch(self, explainer):
        states = np.random.randn(5, 10).astype(np.float32)
        results = explainer.explain_batch(states, n_samples=10)
        assert len(results) == 5

    def test_feature_importance_summary(self, explainer):
        states = np.random.randn(10, 10).astype(np.float32)
        summary = explainer.feature_importance_summary(states, n_samples=10)
        assert "global_ranking" in summary
        assert len(summary["global_ranking"]) == 10
        assert summary["global_ranking"][0]["rank"] == 1

    def test_no_policy_returns_uniform(self):
        explainer = SHAPExplainer(policy_fn=None)
        state = np.zeros(10, dtype=np.float32)
        result = explainer.explain(state, n_samples=10)
        for prob in result["action_probs"].values():
            assert abs(prob - 1/3) < 0.1
