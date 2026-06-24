import React from 'react';
import { Brain, Zap, Target, TrendingUp } from 'lucide-react';

export interface LearningMetricsProps {
  episodeRewards: number[];
  explorationRate: number;
  learningRate: number;
  totalEpisodes: number;
  currentEpisode: number;
  averageReward: number;
  bestReward: number;
}

export const LearningMetrics: React.FC<LearningMetricsProps> = ({
  episodeRewards, explorationRate, learningRate,
  totalEpisodes, currentEpisode, averageReward, bestReward,
}) => {
  const progress = totalEpisodes > 0 ? Math.round((currentEpisode / totalEpisodes) * 100) : 0;

  const stats = [
    { label: "Episodes", value: `${currentEpisode} / ${totalEpisodes || "—"}`, icon: Brain, color: "#a78bfa" },
    { label: "Exploration ε", value: `${explorationRate.toFixed(3)}`, icon: Zap, color: "#f59e0b" },
    { label: "Avg Reward", value: averageReward.toFixed(3), icon: TrendingUp, color: "#10b981" },
    { label: "Best Reward", value: bestReward.toFixed(3), icon: Target, color: "#60a5fa" },
  ];

  const maxReward = episodeRewards.length > 0 ? Math.max(...episodeRewards) : 1;
  const minReward = episodeRewards.length > 0 ? Math.min(...episodeRewards) : 0;
  const range = maxReward - minReward || 1;

  return (
    <div className="space-y-5">
      <div className="metrics-grid">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="stat-card">
            <div className="flex items-center justify-between mb-3">
              <span className="stat-label">{label}</span>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${color}18` }}>
                <Icon size={15} style={{ color }} />
              </div>
            </div>
            <p className="stat-value" style={{ fontSize: 20, color }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Training progress bar */}
      <div className="dash-card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white font-semibold">Training Progress</h3>
          <span className="text-sm text-slate-400">{progress}%</span>
        </div>
        <div className="h-2 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${progress}%`, background: "linear-gradient(90deg, #7c3aed, #06b6d4)" }}
          />
        </div>
        <div className="flex justify-between mt-2 text-xs text-slate-500">
          <span>Learning rate: {learningRate.toExponential(2)}</span>
          <span>{currentEpisode} episodes done</span>
        </div>
      </div>

      {/* Reward chart (sparkline) */}
      <div className="dash-card">
        <h3 className="text-white font-semibold mb-4">Episode Rewards</h3>
        {episodeRewards.length === 0 ? (
          <div className="text-slate-500 text-sm text-center py-10">
            No training data yet — rewards will appear here once the agent starts learning.
          </div>
        ) : (
          <div className="flex items-end gap-0.5 h-24">
            {episodeRewards.slice(-80).map((r, i) => {
              const h = Math.max(4, ((r - minReward) / range) * 100);
              const isPos = r >= 0;
              return (
                <div
                  key={i}
                  className="flex-1 rounded-sm transition-all"
                  style={{
                    height: `${h}%`,
                    background: isPos ? "rgba(16,185,129,0.5)" : "rgba(239,68,68,0.4)",
                    minWidth: 2,
                  }}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
