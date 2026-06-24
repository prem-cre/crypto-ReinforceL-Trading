"""Tests for the Multi-Agent Ensemble RL system."""
import numpy as np
import pytest

from backend.rl.ensemble_agent import (
    EnsembleAgent,
    SpecialistAgent,
    momentum_reward,
    mean_reversion_reward,
    sentiment_reward,
)


class TestRewardShapers:
    def test_momentum_buy_uptrend(self):
        obs = np.zeros(10, dtype=np.float32)
        obs[0] = 1.0  # UP trend
        assert momentum_reward(0.0, obs, 0) > 0  # BUY in uptrend → bonus

    def test_momentum_sell_downtrend(self):
        obs = np.zeros(10, dtype=np.float32)
        obs[0] = -1.0  # DOWN trend
        assert momentum_reward(0.0, obs, 1) > 0  # SELL in downtrend → bonus

    def test_mean_reversion_buy_oversold(self):
        obs = np.zeros(10, dtype=np.float32)
        obs[8] = -0.5  # RSI oversold
        assert mean_reversion_reward(0.0, obs, 0) > 0  # BUY when oversold

    def test_mean_reversion_sell_overbought(self):
        obs = np.zeros(10, dtype=np.float32)
        obs[8] = 0.5  # RSI overbought
        assert mean_reversion_reward(0.0, obs, 1) > 0  # SELL when overbought

    def test_sentiment_positive_buy(self):
        obs = np.zeros(10, dtype=np.float32)
        assert sentiment_reward(0.0, obs, 0, sentiment_score=0.8) > 0

    def test_sentiment_negative_sell(self):
        obs = np.zeros(10, dtype=np.float32)
        assert sentiment_reward(0.0, obs, 1, sentiment_score=-0.8) > 0


class TestSpecialistAgent:
    def test_creates_and_selects_action(self):
        agent = SpecialistAgent("momentum", state_size=10)
        state = np.random.randn(10).astype(np.float32)
        action, logprob, value = agent.select_action(state)
        assert action in [0, 1, 2]

    def test_get_action_probs(self):
        agent = SpecialistAgent("mean_reversion", state_size=10)
        probs = agent.get_action_probs(np.random.randn(10).astype(np.float32))
        assert probs.shape == (3,)
        assert abs(probs.sum() - 1.0) < 1e-5

    def test_rolling_sharpe_empty(self):
        agent = SpecialistAgent("sentiment", state_size=10)
        assert agent.rolling_sharpe() == 0.0


class TestEnsembleAgent:
    def test_creates_three_specialists(self):
        ens = EnsembleAgent(state_size=10)
        assert len(ens.specialists) == 3
        assert set(ens.specialists.keys()) == {"momentum", "mean_reversion", "sentiment"}

    def test_initial_weights_equal(self):
        ens = EnsembleAgent(state_size=10)
        for w in ens.weights.values():
            assert abs(w - 1/3) < 1e-5

    def test_select_action_returns_valid(self):
        ens = EnsembleAgent(state_size=10)
        state = np.random.randn(10).astype(np.float32)
        action, logprob, value, meta = ens.select_action(state)
        assert action in [0, 1, 2]
        assert "weights" in meta
        assert "votes" in meta
        assert len(meta["combined_probs"]) == 3

    def test_get_metrics(self):
        ens = EnsembleAgent(state_size=10)
        m = ens.get_metrics()
        assert "weights" in m
        assert "specialists" in m
