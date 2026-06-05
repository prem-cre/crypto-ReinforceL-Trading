import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
import numpy as np
from typing import Dict, Any, List, Tuple

class ActorCritic(nn.Module):
    def __init__(self, state_dim: int, action_dim: int):
        super(ActorCritic, self).__init__()
        
        # Shared layer or separate? Separate is usually more stable
        self.actor = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, action_dim),
            nn.Softmax(dim=-1)
        )
        
        self.critic = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        action_probs = self.actor(state)
        state_value = self.critic(state)
        return action_probs, state_value

class RLAgent:
    def __init__(
        self,
        state_size: int = 10,
        action_size: int = 3,
        lr: float = 0.001,
        gamma: float = 0.99,
        eps_clip: float = 0.2,
        k_epochs: int = 10
    ):
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
        
        # Experience buffer
        self.states: List[torch.Tensor] = []
        self.actions: List[torch.Tensor] = []
        self.logprobs: List[torch.Tensor] = []
        self.rewards: List[float] = []
        self.dones: List[bool] = []
        
        # Metrics tracking
        self.total_episodes = 0
        self.total_steps = 0
        self.episode_rewards = []
        self.loss_history = []

    def select_action(self, state: np.ndarray) -> Tuple[int, float, float]:
        """
        Select action using old policy. Returns (action_index, log_prob, state_value)
        """
        state_t = torch.FloatTensor(state).to(self.device).unsqueeze(0)
        with torch.no_grad():
            action_probs, state_value = self.policy_old(state_t)
        
        dist = Categorical(action_probs)
        action = dist.sample()
        
        return int(action.item()), float(dist.log_prob(action).item()), float(state_value.item())

    def store_experience(self, state: np.ndarray, action: int, logprob: float, reward: float, done: bool):
        self.states.append(torch.FloatTensor(state))
        self.actions.append(torch.tensor(action))
        self.logprobs.append(torch.tensor(logprob))
        self.rewards.append(reward)
        self.dones.append(done)
        self.total_steps += 1

    def clear_buffer(self):
        self.states = []
        self.actions = []
        self.logprobs = []
        self.rewards = []
        self.dones = []

    def learn(self) -> float:
        """
        Optimize policy using PPO update rules.
        """
        if not self.states:
            return 0.0
        
        # Convert lists to tensors
        old_states = torch.stack(self.states).to(self.device).detach()
        old_actions = torch.stack(self.actions).to(self.device).detach()
        old_logprobs = torch.stack(self.logprobs).to(self.device).detach()
        
        # Compute rewards-to-go (targets for critic)
        returns = []
        discounted_reward = 0
        for reward, done in zip(reversed(self.rewards), reversed(self.dones)):
            if done:
                discounted_reward = 0
            discounted_reward = reward + (self.gamma * discounted_reward)
            returns.insert(0, discounted_reward)
        
        # Normalize returns
        returns = torch.FloatTensor(returns).to(self.device)
        returns = (returns - returns.mean()) / (returns.std() + 1e-7)
        
        # Train for K epochs
        epoch_loss = 0.0
        for _ in range(self.k_epochs):
            # Evaluating old actions and values
            action_probs, state_values = self.policy(old_states)
            state_values = torch.squeeze(state_values)
            
            dist = Categorical(action_probs)
            logprobs = dist.log_prob(old_actions)
            dist_entropy = dist.entropy()
            
            # Finding the ratio (pi_theta / pi_theta__old)
            ratios = torch.exp(logprobs - old_logprobs)
            
            # Finding Surrogate Loss
            advantages = returns - state_values.detach()
            surr1 = ratios * advantages
            surr2 = torch.clamp(ratios, 1 - self.eps_clip, 1 + self.eps_clip) * advantages
            
            # Final loss = Actor loss + Critic loss - Entropy loss
            # Using MSE loss for Critic
            loss = -torch.min(surr1, surr2) + 0.5 * nn.MSELoss()(state_values, returns) - 0.01 * dist_entropy
            
            # Take gradient step
            self.optimizer.zero_grad()
            loss.mean().backward()
            self.optimizer.step()
            
            epoch_loss += loss.mean().item()
            
        # Update old policy
        self.policy_old.load_state_dict(self.policy.state_dict())
        
        # Clear buffer
        self.clear_buffer()
        
        avg_loss = epoch_loss / self.k_epochs
        self.loss_history.append(avg_loss)
        return avg_loss

    def get_metrics(self) -> Dict[str, Any]:
        avg_reward = np.mean(self.episode_rewards[-50:]) if self.episode_rewards else 0.0
        best_reward = np.max(self.episode_rewards) if self.episode_rewards else 0.0
        avg_loss = np.mean(self.loss_history[-10:]) if self.loss_history else 0.0

        return {
            "totalEpisodes": self.total_episodes,
            "totalSteps": self.total_steps,
            "averageReward": float(avg_reward),
            "bestReward": float(best_reward),
            "averageLoss": float(avg_loss),
            "learningRate": self.optimizer.param_groups[0]['lr']
        }

    def save_model(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save(self.policy.state_dict(), path)

    def load_model(self, path: str):
        if os.path.exists(path):
            self.policy.load_state_dict(torch.load(path, map_location=self.device))
            self.policy_old.load_state_dict(self.policy.state_dict())
            print(f"Model loaded successfully from {path}")
        else:
            print(f"Model path {path} not found. Starting with initial model.")
