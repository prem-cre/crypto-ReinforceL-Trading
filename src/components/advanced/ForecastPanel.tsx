import React, { useState } from "react";
import { LineChart, Clock, TrendingUp, TrendingDown, Cpu } from "lucide-react";
import { apiFetch } from "../../lib/api";

interface Forecast {
  predictions: Record<string, number>;
  confidence: Record<string, number>;
  trained: boolean;
  pair?: string;
  model?: { total_params: number; architecture: { type: string; layers: number; heads: number; d_model: number; seq_len: number } };
}

interface TrainResult {
  epochs: number;
  final_loss: number;
  samples: number;
  loss_curve: number[];
}

export const ForecastPanel: React.FC = () => {
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [trainResult, setTrainResult] = useState<TrainResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState("");

  const getPrediction = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await apiFetch("/forecast/predict?pair=BTC%2FUSDT");
      if (!res.ok) throw new Error(await res.text());
      setForecast(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const trainModel = async () => {
    setTraining(true);
    setError("");
    try {
      const res = await apiFetch("/forecast/train?pair=BTC%2FUSDT&epochs=20", { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setTrainResult(data);
      await getPrediction();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setTraining(false);
    }
  };

  const horizonColors: Record<string, string> = { "1h": "#10b981", "4h": "#f59e0b", "24h": "#a78bfa" };
  const horizonIcons: Record<string, React.ReactNode> = {
    "1h": <Clock size={14} />,
    "4h": <Clock size={14} />,
    "24h": <Clock size={14} />,
  };

  return (
    <div className="space-y-4">
      <div className="dash-card">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-cyan-500/15 flex items-center justify-center">
            <Cpu size={18} className="text-cyan-400" />
          </div>
          <div>
            <h2 className="text-white font-semibold text-base">Transformer Price Forecasting</h2>
            <p className="text-slate-500 text-xs">Multi-horizon predictions: 1h, 4h, 24h returns</p>
          </div>
        </div>

        <div className="flex gap-3 mb-4">
          <button className="btn-primary" onClick={trainModel} disabled={training}>
            {training ? <span className="flex items-center gap-2"><span className="spinner" />Training…</span> : "Train Transformer"}
          </button>
          <button
            className="px-4 py-2 text-sm rounded-lg border border-white/10 text-slate-300 hover:bg-white/5 transition"
            onClick={getPrediction}
            disabled={loading}
          >
            {loading ? "Loading…" : "Get Predictions"}
          </button>
        </div>

        {error && <div className="text-red-400 text-sm p-3 bg-red-500/10 rounded-lg border border-red-500/20 mb-3">{error}</div>}

        {trainResult && (
          <div className="stat-card mb-4">
            <div className="flex justify-between text-xs">
              <span className="text-slate-400">Training Complete</span>
              <span className="text-emerald-400">{trainResult.epochs} epochs</span>
            </div>
            <div className="flex justify-between text-xs mt-1">
              <span className="text-slate-500">Final Loss</span>
              <span className="text-white font-mono">{trainResult.final_loss.toFixed(6)}</span>
            </div>
            <div className="flex justify-between text-xs mt-1">
              <span className="text-slate-500">Samples</span>
              <span className="text-white">{trainResult.samples}</span>
            </div>
            {trainResult.loss_curve.length > 0 && (
              <div className="mt-3">
                <div className="text-xs text-slate-500 mb-1">Loss Curve</div>
                <div className="flex items-end gap-px h-12">
                  {trainResult.loss_curve.map((l, i) => {
                    const max = Math.max(...trainResult.loss_curve);
                    const h = max > 0 ? (l / max) * 100 : 0;
                    return (
                      <div
                        key={i}
                        className="flex-1 rounded-t"
                        style={{ height: `${h}%`, background: "rgba(6, 182, 212, 0.5)", minWidth: 2 }}
                      />
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {forecast?.predictions && Object.keys(forecast.predictions).length > 0 && (
          <div>
            <h3 className="text-white text-sm font-semibold mb-3">Predicted Returns</h3>
            <div className="grid grid-cols-3 gap-3 mb-4">
              {Object.entries(forecast.predictions).map(([horizon, pct]) => {
                const color = horizonColors[horizon] || "#60a5fa";
                const conf = forecast.confidence?.[horizon] ?? 0;
                return (
                  <div key={horizon} className="stat-card">
                    <div className="flex items-center gap-2 mb-2">
                      <span style={{ color }}>{horizonIcons[horizon]}</span>
                      <span className="text-xs text-slate-400 uppercase">{horizon} Forecast</span>
                    </div>
                    <div className="flex items-center gap-1">
                      {pct >= 0 ? <TrendingUp size={16} style={{ color }} /> : <TrendingDown size={16} style={{ color: "#ef4444" }} />}
                      <p className="font-bold text-lg" style={{ color: pct >= 0 ? color : "#ef4444" }}>
                        {pct >= 0 ? "+" : ""}{pct.toFixed(2)}%
                      </p>
                    </div>
                    <div className="mt-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-500">Confidence</span>
                        <span className="text-slate-300">{(conf * 100).toFixed(0)}%</span>
                      </div>
                      <div className="w-full bg-white/5 rounded-full h-1 mt-1">
                        <div className="h-1 rounded-full" style={{ width: `${conf * 100}%`, background: color }} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {forecast?.model && (
          <div className="stat-card">
            <h4 className="text-xs text-slate-400 mb-2">Model Architecture</h4>
            <div className="grid grid-cols-2 gap-y-1 text-xs">
              <span className="text-slate-500">Type</span>
              <span className="text-white">{forecast.model.architecture.type}</span>
              <span className="text-slate-500">Layers</span>
              <span className="text-white">{forecast.model.architecture.layers}</span>
              <span className="text-slate-500">Attention Heads</span>
              <span className="text-white">{forecast.model.architecture.heads}</span>
              <span className="text-slate-500">d_model</span>
              <span className="text-white">{forecast.model.architecture.d_model}</span>
              <span className="text-slate-500">Parameters</span>
              <span className="text-white">{forecast.model.total_params.toLocaleString()}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
