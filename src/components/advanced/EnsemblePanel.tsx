import React, { useState } from "react";
import { Users, TrendingUp, TrendingDown, Activity, Zap } from "lucide-react";
import { apiFetch } from "../../lib/api";

interface EnsembleResult {
  weights: Record<string, number>;
  specialists: Record<string, { total_episodes: number; rolling_sharpe: number; recent_returns: number[] }>;
  episodesRun?: number;
}

export const EnsemblePanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EnsembleResult | null>(null);
  const [episodes, setEpisodes] = useState(5);
  const [error, setError] = useState("");

  const trainEnsemble = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await apiFetch(`/ensemble/train?episodes=${episodes}&pair=BTC%2FUSDT`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message || "Training failed");
    } finally {
      setLoading(false);
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await apiFetch("/ensemble/status");
      const data = await res.json();
      if (data.initialized) setResult(data);
    } catch {}
  };

  React.useEffect(() => { fetchStatus(); }, []);

  const agentColors: Record<string, string> = {
    momentum: "#f59e0b",
    mean_reversion: "#06b6d4",
    sentiment: "#a78bfa",
  };

  const agentIcons: Record<string, React.ReactNode> = {
    momentum: <TrendingUp size={14} />,
    mean_reversion: <TrendingDown size={14} />,
    sentiment: <Activity size={14} />,
  };

  return (
    <div className="space-y-4">
      <div className="dash-card">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-violet-500/15 flex items-center justify-center">
            <Users size={18} className="text-violet-400" />
          </div>
          <div>
            <h2 className="text-white font-semibold text-base">Multi-Agent Ensemble RL</h2>
            <p className="text-slate-500 text-xs">3 specialized PPO agents with adaptive weighting</p>
          </div>
        </div>

        <div className="flex items-center gap-3 mb-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Episodes</label>
            <input
              type="number"
              className="dash-input w-24"
              value={episodes}
              onChange={e => setEpisodes(Number(e.target.value))}
              min={1}
              max={50}
            />
          </div>
          <button className="btn-primary mt-4" onClick={trainEnsemble} disabled={loading}>
            {loading ? <span className="flex items-center gap-2"><span className="spinner" />Training…</span> : "Train Ensemble"}
          </button>
        </div>

        {error && <div className="text-red-400 text-sm p-3 bg-red-500/10 rounded-lg border border-red-500/20 mb-3">{error}</div>}

        {result?.weights && (
          <>
            <h3 className="text-white text-sm font-semibold mb-3">Agent Weights (Adaptive)</h3>
            <div className="grid grid-cols-3 gap-3 mb-4">
              {Object.entries(result.weights).map(([name, weight]) => (
                <div key={name} className="stat-card">
                  <div className="flex items-center gap-2 mb-2">
                    <span style={{ color: agentColors[name] }}>{agentIcons[name]}</span>
                    <span className="text-xs text-slate-400 capitalize">{name.replace("_", " ")}</span>
                  </div>
                  <p className="font-bold text-lg" style={{ color: agentColors[name] }}>
                    {(weight * 100).toFixed(1)}%
                  </p>
                  <div className="w-full bg-white/5 rounded-full h-1.5 mt-2">
                    <div
                      className="h-1.5 rounded-full transition-all"
                      style={{ width: `${weight * 100}%`, background: agentColors[name] }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {result.specialists && (
              <>
                <h3 className="text-white text-sm font-semibold mb-3">Specialist Performance</h3>
                <div className="grid grid-cols-3 gap-3">
                  {Object.entries(result.specialists).map(([name, spec]) => (
                    <div key={name} className="stat-card">
                      <span className="text-xs text-slate-400 capitalize block mb-1">{name.replace("_", " ")}</span>
                      <div className="flex justify-between text-xs mt-1">
                        <span className="text-slate-500">Episodes</span>
                        <span className="text-white">{spec.total_episodes}</span>
                      </div>
                      <div className="flex justify-between text-xs mt-1">
                        <span className="text-slate-500">Rolling Sharpe</span>
                        <span style={{ color: spec.rolling_sharpe >= 0 ? "#10b981" : "#ef4444" }}>
                          {spec.rolling_sharpe.toFixed(3)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
};
