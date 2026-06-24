import React, { useState } from 'react';
import { Brain, Zap, Target, TrendingUp, Play, RefreshCw } from 'lucide-react';
import { apiFetch } from '../../lib/api';

export interface LearningMetricsProps {
  episodeRewards: number[];
  explorationRate: number;
  learningRate: number;
  totalEpisodes: number;
  currentEpisode: number;
  averageReward: number;
  bestReward: number;
}

export const LearningMetrics: React.FC<LearningMetricsProps> = (wsProps) => {
  const [localRewards, setLocalRewards] = useState<number[]>(wsProps.episodeRewards);
  const [totalEpisodes, setTotalEpisodes] = useState(wsProps.totalEpisodes);
  const [avgReward, setAvgReward] = useState(wsProps.averageReward);
  const [bestReward, setBestReward] = useState(wsProps.bestReward);
  const [training, setTraining] = useState(false);
  const [trainMsg, setTrainMsg] = useState('');
  const [episodes, setEpisodes] = useState(5);
  const [pair, setPair] = useState('BTC/USDT');

  const runTraining = async () => {
    setTraining(true);
    setTrainMsg(`Training ${episodes} episodes on ${pair}…`);
    try {
      const res = await apiFetch(`/train?episodes=${episodes}&pair=${encodeURIComponent(pair)}`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setLocalRewards(prev => [...prev, ...(data.episodeRewards || [])]);
      setTotalEpisodes(data.totalEpisodes || totalEpisodes + episodes);
      setAvgReward(data.averageReward ?? avgReward);
      setBestReward(data.bestReward ?? bestReward);
      setTrainMsg(`Done! Ran ${data.episodesRun} episodes. Model: ${data.modelVersion}`);
    } catch (e: any) {
      setTrainMsg(`Error: ${e.message}`);
    } finally {
      setTraining(false);
    }
  };

  const rewards = localRewards.length > 0 ? localRewards : wsProps.episodeRewards;
  const total = totalEpisodes || wsProps.totalEpisodes;
  const avg = avgReward || wsProps.averageReward;
  const best = bestReward || wsProps.bestReward;

  const maxR = rewards.length > 0 ? Math.max(...rewards) : 1;
  const minR = rewards.length > 0 ? Math.min(...rewards) : 0;
  const range = maxR - minR || 1;

  const stats = [
    { label: "Total Episodes", value: String(total || 0), icon: Brain, color: "#a78bfa" },
    { label: "Avg Reward", value: avg.toFixed(3), icon: TrendingUp, color: "#10b981" },
    { label: "Best Reward", value: best.toFixed(3), icon: Target, color: "#60a5fa" },
    { label: "Learning Rate", value: wsProps.learningRate.toExponential(1), icon: Zap, color: "#f59e0b" },
  ];

  return (
    <div className="space-y-5">
      {/* Train controls */}
      <div className="dash-card">
        <div className="accent-bar w-12" />
        <h2 className="text-white font-semibold mb-4">Train the PPO Agent</h2>
        <p className="text-slate-400 text-sm mb-4">
          Each episode runs the PPO actor-critic agent through 200 historical candles,
          collects experience, and updates the policy via the clipped surrogate objective.
        </p>
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">Episodes</label>
            <select
              className="dash-input w-28"
              style={{ background: "rgba(255,255,255,0.04)", borderColor: "rgba(255,255,255,0.1)", color: "#d1d5db" }}
              value={episodes}
              onChange={e => setEpisodes(Number(e.target.value))}
              disabled={training}
            >
              {[1, 3, 5, 10, 20].map(n => <option key={n} value={n}>{n} episodes</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">Pair</label>
            <select
              className="dash-input w-32"
              style={{ background: "rgba(255,255,255,0.04)", borderColor: "rgba(255,255,255,0.1)", color: "#d1d5db" }}
              value={pair}
              onChange={e => setPair(e.target.value)}
              disabled={training}
            >
              {["BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT"].map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <button className="btn-primary" onClick={runTraining} disabled={training}>
            {training
              ? <><span className="spinner" /> Training…</>
              : <><Play size={14} /> Run Training</>
            }
          </button>
          {localRewards.length > 0 && !training && (
            <button className="btn-secondary" onClick={() => setLocalRewards([])}>
              <RefreshCw size={14} /> Reset chart
            </button>
          )}
        </div>
        {trainMsg && (
          <p className={`mt-3 text-sm ${trainMsg.startsWith('Error') ? 'text-red-400' : 'text-emerald-400'}`}>
            {trainMsg}
          </p>
        )}
      </div>

      {/* Stats */}
      <div className="metrics-grid">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="stat-card">
            <div className="flex items-center justify-between mb-2">
              <span className="stat-label">{label}</span>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${color}18` }}>
                <Icon size={13} style={{ color }} />
              </div>
            </div>
            <p className="font-bold" style={{ fontSize: 20, color }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Reward chart */}
      <div className="dash-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-white font-semibold">Episode Rewards</h3>
          <span className="text-xs text-slate-500">{rewards.length} episodes</span>
        </div>
        {rewards.length === 0 ? (
          <div className="text-slate-500 text-sm text-center py-12">
            Click <strong className="text-slate-400">Run Training</strong> above to start training the PPO agent.
            Rewards will appear here as each episode completes.
          </div>
        ) : (
          <>
            <div className="flex items-end gap-0.5 h-28">
              {rewards.slice(-100).map((r, i) => {
                const h = Math.max(3, ((r - minR) / range) * 100);
                return (
                  <div
                    key={i}
                    title={`Ep ${i + 1}: ${r.toFixed(3)}`}
                    className="flex-1 rounded-sm transition-all"
                    style={{
                      height: `${h}%`,
                      background: r >= 0 ? "rgba(16,185,129,0.55)" : "rgba(239,68,68,0.45)",
                      minWidth: 2,
                    }}
                  />
                );
              })}
            </div>
            <div className="flex justify-between mt-2 text-xs text-slate-500">
              <span>Min: {minR.toFixed(2)}</span>
              <span>Max: {maxR.toFixed(2)}</span>
            </div>
          </>
        )}
      </div>

      {/* What's happening explainer */}
      <div className="dash-card">
        <h3 className="text-white font-semibold mb-3">How training works</h3>
        <div className="space-y-2 text-sm text-slate-400">
          <p>1. <span className="text-slate-300">Fetch candles</span> — 200 1h OHLCV bars from Binance for the selected pair</p>
          <p>2. <span className="text-slate-300">Roll out episode</span> — PPO agent steps through each candle, choosing BUY/SELL/HOLD</p>
          <p>3. <span className="text-slate-300">Compute returns</span> — discounted cumulative reward (γ=0.99)</p>
          <p>4. <span className="text-slate-300">PPO update</span> — K epochs of clipped surrogate loss + value function MSE + entropy bonus</p>
          <p>5. <span className="text-slate-300">Save model</span> — updated weights saved, model version incremented</p>
        </div>
      </div>
    </div>
  );
};
