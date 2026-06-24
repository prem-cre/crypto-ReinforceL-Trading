"""Multi-Agent Ensemble RL — three specialized PPO agents with adaptive weighting.

Agent 1 (Momentum):  Rewarded for trend-following trades (long in uptrend, short in downtrend).
Agent 2 (MeanRevert): Rewarded for counter-trend entries at extremes (RSI oversold/overbought).
Agent 3 (Sentiment):  Rewarded proportionally to sentiment alignment (Phase 2 RAG score).

A meta-learner combines their action distributions using softmax-weighted votes
derived from each agent's recent rolling Sharpe ratio.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from torch.distributions import Categorical

from backend.rl.rl_agent import ActorCritic

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Specialist reward shapers
# ---------------------------------------------------------------------------

def momentum_reward(base_reward: float, obs: np.ndarray, action: int) -> float:
    """Bonus when action aligns with trend direction (obs[0] = trend)."""
    trend = obs[0]  # 1=UP, -1=DOWN, 0=SIDEWAYS
    if action == 0 and trend > 0:      # BUY in uptrend
        return base_reward + 0.3
    if action == 1 and trend < 0:      # SELL in downtrend
        return base_reward + 0.3
    if action == 2:                    # HOLD penalised in strong trend
        return base_reward - 0.1 * abs(trend)
    return base_reward


def mean_reversion_reward(base_reward: float, obs: np.ndarray, action: int) -> float:
    """Bonus when action is counter-trend at RSI extremes (obs[8] = rsi_scaled)."""
    rsi_scaled = obs[8]  # (rsi-50)/50 → >0.3 overbought, <-0.3 oversold
    if action == 1 and rsi_scaled > 0.3:   # SELL when overbought
        return base_reward + 0.4
    if action == 0 and rsi_scaled < -0.3:  # BUY when oversold
        return base_reward + 0.4
    return base_reward


def sentiment_reward(base_reward: float, obs: np.ndarray, action: int,
                     sentiment_score: float = 0.0) -> float:
    """Bonus when action aligns with sentiment direction."""
    if sentiment_score > 0.2 and action == 0:    # positive sentiment + BUY
        return base_reward + 0.3 * sentiment_score
    if sentiment_score < -0.2 and action == 1:   # negative sentiment + SELL
        return base_reward + 0.3 * abs(sentiment_score)
    return base_reward


REWARD_SHAPERS = {
    "momentum": momentum_reward,
    "mean_reversion": mean_reversion_reward,
    "sentiment": sentiment_reward,
}


# ---------------------------------------------------------------------------
# Specialist Agent wrapper
# ---------------------------------------------------------------------------

class SpecialistAgent:
    """Thin wrapper around ActorCritic with its own reward shaper and perf tracker."""

    def __init__(self, name: str, state_size: int, action_size: int = 3,
                 lr: float = 0.001, gamma: float = 0.99):
        self.name = name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.policy = ActorCritic(state_size, action_size).to(self.device)
        self.policy_old = ActorCritic(state_size, action_size).to(self.device)
        self.policy_old.load_state_dict(self.policy.state_dict())
        self.optimizer = torch.optim.Adam(self.policy.parameters(), lr=lr)

        self.gamma = gamma
        self.eps_clip = 0.2
        self.k_epochs = 10

        # Experience buffer
        self.states: List[torch.Tensor] = []
        self.actions: List[torch.Tensor] = []
        self.logprobs: List[torch.Tensor] = []
        self.rewards: List[float] = []
        self.dones: List[bool] = []

        # Performance tracking for weight calculation
        self.recent_returns: List[float] = []
        self.total_episodes = 0

        self.reward_shaper = REWARD_SHAPERS.get(name, lambda r, *a, **k: r)

    def get_action_probs(self, state: np.ndarray) -> np.ndarray:
        state_t = torch.FloatTensor(state).to(self.device).unsqueeze(0)
        with torch.no_grad():
            probs, _ = self.policy_old(state_t)
        return probs.cpu().numpy().flatten()

    def select_action(self, state: np.ndarray) -> Tuple[int, float, float]:
        state_t = torch.FloatTensor(state).to(self.device).unsqueeze(0)
        with torch.no_grad():
            probs, value = self.policy_old(state_t)
        dist = Categorical(probs)
        action = dist.sample()
        return int(action.item()), float(dist.log_prob(action).item()), float(value.item())

    def store(self, state: np.ndarray, action: int, logprob: float,
              reward: float, done: bool) -> None:
        self.states.append(torch.FloatTensor(state))
        self.actions.append(torch.tensor(action))
        self.logprobs.append(torch.tensor(logprob))
        self.rewards.append(reward)
        self.dones.append(done)

    def learn(self) -> float:
        if not self.states:
            return 0.0
        old_states = torch.stack(self.states).to(self.device).detach()
        old_actions = torch.stack(self.actions).to(self.device).detach()
        old_logprobs = torch.stack(self.logprobs).to(self.device).detach()

        returns: List[float] = []
        disc = 0.0
        for r, d in zip(reversed(self.rewards), reversed(self.dones)):
            if d:
                disc = 0.0
            disc = r + self.gamma * disc
            returns.insert(0, disc)
        returns_t = torch.FloatTensor(returns).to(self.device)
        returns_t = (returns_t - returns_t.mean()) / (returns_t.std() + 1e-7)

        total_loss = 0.0
        for _ in range(self.k_epochs):
            probs, vals = self.policy(old_states)
            vals = vals.squeeze()
            dist = Categorical(probs)
            logp = dist.log_prob(old_actions)
            entropy = dist.entropy()
            ratios = torch.exp(logp - old_logprobs)
            adv = returns_t - vals.detach()
            s1 = ratios * adv
            s2 = torch.clamp(ratios, 1 - self.eps_clip, 1 + self.eps_clip) * adv
            loss = (-torch.min(s1, s2)
                    + 0.5 * torch.nn.MSELoss()(vals, returns_t)
                    - 0.01 * entropy)
            self.optimizer.zero_grad()
            loss.mean().backward()
            self.optimizer.step()
            total_loss += loss.mean().item()

        self.policy_old.load_state_dict(self.policy.state_dict())
        self.states.clear()
        self.actions.clear()
        self.logprobs.clear()
        self.rewards.clear()
        self.dones.clear()
        self.total_episodes += 1
        return total_loss / self.k_epochs

    def rolling_sharpe(self, window: int = 20) -> float:
        if len(self.recent_returns) < 2:
            return 0.0
        tail = self.recent_returns[-window:]
        mean_r = np.mean(tail)
        std_r = np.std(tail, ddof=1)
        return float(mean_r / std_r) if std_r > 1e-8 else 0.0


# ---------------------------------------------------------------------------
# Ensemble Agent
# ---------------------------------------------------------------------------

class EnsembleAgent:
    """Combines three specialist PPO agents via adaptive softmax-weighted voting."""

    def __init__(self, state_size: int = 10, action_size: int = 3,
                 lr: float = 0.001, gamma: float = 0.99):
        self.state_size = state_size
        self.action_size = action_size
        self.specialists: Dict[str, SpecialistAgent] = {
            name: SpecialistAgent(name, state_size, action_size, lr, gamma)
            for name in ["momentum", "mean_reversion", "sentiment"]
        }
        self.weights: Dict[str, float] = {n: 1.0 / 3 for n in self.specialists}
        self._weight_history: List[Dict[str, float]] = []

    def _update_weights(self) -> None:
        """Softmax over rolling Sharpe ratios → adaptive weights."""
        sharpes = {n: a.rolling_sharpe() for n, a in self.specialists.items()}
        vals = np.array(list(sharpes.values()))
        # Temperature-scaled softmax
        temp = 1.0
        exp_v = np.exp((vals - vals.max()) / temp)
        softmax = exp_v / (exp_v.sum() + 1e-8)
        for i, name in enumerate(sharpes):
            self.weights[name] = float(softmax[i])
        self._weight_history.append(dict(self.weights))

    def select_action(self, state: np.ndarray) -> Tuple[int, float, float, Dict[str, Any]]:
        """Weighted vote across all specialists → single action."""
        self._update_weights()
        combined_probs = np.zeros(self.action_size)
        agent_votes: Dict[str, int] = {}

        for name, agent in self.specialists.items():
            probs = agent.get_action_probs(state)
            combined_probs += self.weights[name] * probs
            agent_votes[name] = int(np.argmax(probs))

        combined_probs /= combined_probs.sum() + 1e-8
        dist = Categorical(torch.FloatTensor(combined_probs))
        action = dist.sample()

        meta = {
            "weights": dict(self.weights),
            "votes": agent_votes,
            "combined_probs": combined_probs.tolist(),
            "action_names": {0: "BUY", 1: "SELL", 2: "HOLD"},
        }
        return int(action.item()), float(dist.log_prob(action).item()), 0.0, meta

    def train_episode(self, env, shaped_rewards: bool = True,
                      sentiment_score: float = 0.0) -> Dict[str, Any]:
        """Run one episode, training all three specialists with shaped rewards."""
        obs = env.reset()
        done = False
        episode_rewards = {n: 0.0 for n in self.specialists}
        step = 0

        while not done:
            action, logprob, _, _ = self.select_action(obs)
            next_obs, base_reward, done, info = env.step(action)

            for name, agent in self.specialists.items():
                if name == "sentiment":
                    shaped_r = agent.reward_shaper(base_reward, obs, action,
                                                   sentiment_score=sentiment_score)
                else:
                    shaped_r = agent.reward_shaper(base_reward, obs, action)
                agent.store(obs, action, logprob, shaped_r if shaped_rewards else base_reward, done)
                episode_rewards[name] += shaped_r

            obs = next_obs
            step += 1

        losses = {}
        for name, agent in self.specialists.items():
            losses[name] = agent.learn()
            agent.recent_returns.append(episode_rewards[name])

        return {
            "episode_rewards": episode_rewards,
            "losses": losses,
            "weights": dict(self.weights),
            "steps": step,
        }

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "weights": dict(self.weights),
            "weight_history": self._weight_history[-50:],
            "specialists": {
                name: {
                    "total_episodes": a.total_episodes,
                    "rolling_sharpe": a.rolling_sharpe(),
                    "recent_returns": a.recent_returns[-20:],
                }
                for name, a in self.specialists.items()
            },
        }
