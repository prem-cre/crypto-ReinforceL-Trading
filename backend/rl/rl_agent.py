"""PPO actor-critic RL agent for the trading bot.

Changes from the legacy version:
- safetensors save/load (was: torch.save → was *also* JSON in places)
- Optional load from HuggingFace Hub registry on construction
- Same PPO math, same metrics surface
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from safetensors.torch import load_file as safe_load
from safetensors.torch import save_file as safe_save
from torch.distributions import Categorical

from backend.mlops.model_registry import POLICY_FILENAME, LOCAL_CACHE_DIR, download_production_policy

logger = logging.getLogger(__name__)


class ActorCritic(nn.Module):
    def __init__(self, state_dim: int, action_dim: int):
        super().__init__()
        self.actor = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, action_dim),
            nn.Softmax(dim=-1),
        )
        self.critic = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.actor(state), self.critic(state)


class RLAgent:
    def __init__(
        self,
        state_size: int = 10,
        action_size: int = 3,
        lr: float = 0.001,
        gamma: float = 0.99,
        eps_clip: float = 0.2,
        k_epochs: int = 10,
    ) -> None:
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma
        self.eps_clip = eps_clip
        self.k_epochs = k_epochs

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.policy = ActorCritic(state_size, action_size).to(self.device)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        self.policy_old = ActorCritic(state_size, action_size).to(self.device)
        self.policy_old.load_state_dict(self.policy.state_dict())

        self.states: List[torch.Tensor] = []
        self.actions: List[torch.Tensor] = []
        self.logprobs: List[torch.Tensor] = []
        self.rewards: List[float] = []
        self.dones: List[bool] = []

        self.total_episodes = 0
        self.total_steps = 0
        self.episode_rewards: List[float] = []
        self.loss_history: List[float] = []
        self.model_version: Optional[str] = None

    # ─── Action / training ──────────────────────────────────────
    def select_action(self, state: np.ndarray) -> Tuple[int, float, float]:
        state_t = torch.FloatTensor(state).to(self.device).unsqueeze(0)
        with torch.no_grad():
            action_probs, state_value = self.policy_old(state_t)
        dist = Categorical(action_probs)
        action = dist.sample()
        return int(action.item()), float(dist.log_prob(action).item()), float(state_value.item())

    def store_experience(self, state: np.ndarray, action: int, logprob: float, reward: float, done: bool) -> None:
        self.states.append(torch.FloatTensor(state))
        self.actions.append(torch.tensor(action))
        self.logprobs.append(torch.tensor(logprob))
        self.rewards.append(reward)
        self.dones.append(done)
        self.total_steps += 1

    def clear_buffer(self) -> None:
        self.states.clear()
        self.actions.clear()
        self.logprobs.clear()
        self.rewards.clear()
        self.dones.clear()

    def learn(self) -> float:
        if not self.states:
            return 0.0

        old_states = torch.stack(self.states).to(self.device).detach()
        old_actions = torch.stack(self.actions).to(self.device).detach()
        old_logprobs = torch.stack(self.logprobs).to(self.device).detach()

        returns: List[float] = []
        discounted_reward = 0.0
        for reward, done in zip(reversed(self.rewards), reversed(self.dones)):
            if done:
                discounted_reward = 0.0
            discounted_reward = reward + (self.gamma * discounted_reward)
            returns.insert(0, discounted_reward)

        returns_t = torch.FloatTensor(returns).to(self.device)
        returns_t = (returns_t - returns_t.mean()) / (returns_t.std() + 1e-7)

        epoch_loss = 0.0
        for _ in range(self.k_epochs):
            action_probs, state_values = self.policy(old_states)
            state_values = torch.squeeze(state_values)

            dist = Categorical(action_probs)
            logprobs = dist.log_prob(old_actions)
            entropy = dist.entropy()

            ratios = torch.exp(logprobs - old_logprobs)
            advantages = returns_t - state_values.detach()
            surr1 = ratios * advantages
            surr2 = torch.clamp(ratios, 1 - self.eps_clip, 1 + self.eps_clip) * advantages

            loss = -torch.min(surr1, surr2) + 0.5 * nn.MSELoss()(state_values, returns_t) - 0.01 * entropy

            self.optimizer.zero_grad()
            loss.mean().backward()
            self.optimizer.step()
            epoch_loss += loss.mean().item()

        self.policy_old.load_state_dict(self.policy.state_dict())
        self.clear_buffer()

        avg_loss = epoch_loss / self.k_epochs
        self.loss_history.append(avg_loss)
        return avg_loss

    # ─── Metrics ────────────────────────────────────────────────
    def get_metrics(self) -> Dict[str, Any]:
        avg_reward = float(np.mean(self.episode_rewards[-50:])) if self.episode_rewards else 0.0
        best_reward = float(np.max(self.episode_rewards)) if self.episode_rewards else 0.0
        avg_loss = float(np.mean(self.loss_history[-10:])) if self.loss_history else 0.0
        return {
            "totalEpisodes": self.total_episodes,
            "totalSteps": self.total_steps,
            "averageReward": avg_reward,
            "bestReward": best_reward,
            "averageLoss": avg_loss,
            "learningRate": self.optimizer.param_groups[0]["lr"],
            "modelVersion": self.model_version or "untrained",
        }

    # ─── Persistence ────────────────────────────────────────────
    def save_policy(self, path: Optional[str] = None) -> str:
        path = path or str(LOCAL_CACHE_DIR / POLICY_FILENAME)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        safe_save(self.policy.state_dict(), path)
        return path

    def load_policy(self, path: str) -> bool:
        try:
            state_dict = safe_load(path)
            self.policy.load_state_dict(state_dict)
            self.policy_old.load_state_dict(state_dict)
            self.model_version = os.path.basename(path)
            logger.info(f"Loaded policy from {path}")
            return True
        except Exception as e:
            logger.warning(f"load_policy failed for {path}: {e}")
            return False

    def try_load_from_registry(self, repo_id: str, hf_token: Optional[str]) -> bool:
        path = download_production_policy(repo_id, hf_token)
        if not path:
            return False
        return self.load_policy(path)
