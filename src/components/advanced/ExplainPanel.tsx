import React, { useState } from "react";
import { Eye, ArrowUp, ArrowDown, BarChart3 } from "lucide-react";
import { apiFetch } from "../../lib/api";

interface FeatureImportance {
  feature: string;
  value: number;
  shap_value: number;
  direction: string;
  abs_importance: number;
}

interface Explanation {
  action: string;
  action_probs: Record<string, number>;
  feature_importance: FeatureImportance[];
  top_drivers: { feature: string; impact: number; direction: string }[];
  pair?: string;
  market_state?: Record<string, string>;
}

interface GlobalRanking {
  rank: number;
  feature: string;
  mean_abs_shap: number;
}

export const ExplainPanel: React.FC = () => {
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [globalRanking, setGlobalRanking] = useState<GlobalRanking[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingGlobal, setLoadingGlobal] = useState(false);
  const [error, setError] = useState("");

  const explain = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await apiFetch("/explain?pair=BTC%2FUSDT");
      if (!res.ok) throw new Error(await res.text());
      setExplanation(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const explainGlobal = async () => {
    setLoadingGlobal(true);
    try {
      const res = await apiFetch("/explain/summary?pair=BTC%2FUSDT");
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setGlobalRanking(data.global_ranking || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoadingGlobal(false);
    }
  };

  const actionColors: Record<string, string> = { BUY: "#10b981", SELL: "#ef4444", HOLD: "#f59e0b" };

  return (
    <div className="space-y-4">
      <div className="dash-card">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-amber-500/15 flex items-center justify-center">
            <Eye size={18} className="text-amber-400" />
          </div>
          <div>
            <h2 className="text-white font-semibold text-base">SHAP Explainability</h2>
            <p className="text-slate-500 text-xs">Feature attribution for RL agent decisions</p>
          </div>
        </div>

        <div className="flex gap-3 mb-4">
          <button className="btn-primary" onClick={explain} disabled={loading}>
            {loading ? <span className="flex items-center gap-2"><span className="spinner" />Analyzing…</span> : "Explain Current Decision"}
          </button>
          <button
            className="px-4 py-2 text-sm rounded-lg border border-white/10 text-slate-300 hover:bg-white/5 transition"
            onClick={explainGlobal}
            disabled={loadingGlobal}
          >
            {loadingGlobal ? "Computing…" : "Global Feature Importance"}
          </button>
        </div>

        {error && <div className="text-red-400 text-sm p-3 bg-red-500/10 rounded-lg border border-red-500/20 mb-3">{error}</div>}

        {explanation && (
          <>
            {/* Decision summary */}
            <div className="stat-card mb-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-slate-400 text-xs">Agent Decision</span>
                <span
                  className="px-3 py-1 rounded-full text-sm font-semibold"
                  style={{
                    background: `${actionColors[explanation.action]}20`,
                    color: actionColors[explanation.action],
                  }}
                >
                  {explanation.action}
                </span>
              </div>
              <div className="flex gap-4">
                {Object.entries(explanation.action_probs).map(([action, prob]) => (
                  <div key={action} className="flex-1">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-500">{action}</span>
                      <span style={{ color: actionColors[action] }}>{(prob * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-white/5 rounded-full h-1.5">
                      <div
                        className="h-1.5 rounded-full transition-all"
                        style={{ width: `${prob * 100}%`, background: actionColors[action] }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top drivers */}
            <h3 className="text-white text-sm font-semibold mb-3">Top Decision Drivers</h3>
            <div className="space-y-2 mb-4">
              {explanation.top_drivers.map((driver, i) => {
                const color = driver.direction === "positive" ? "#10b981" : "#ef4444";
                const maxImpact = Math.max(...explanation.top_drivers.map(d => Math.abs(d.impact)), 0.001);
                const barWidth = (Math.abs(driver.impact) / maxImpact) * 100;
                return (
                  <div key={i} className="flex items-center gap-3">
                    <span className="text-xs text-slate-400 w-28 text-right capitalize">
                      {driver.feature.replace("_", " ")}
                    </span>
                    <div className="flex-1 flex items-center gap-2">
                      {driver.direction === "positive" ? (
                        <ArrowUp size={12} style={{ color }} />
                      ) : (
                        <ArrowDown size={12} style={{ color }} />
                      )}
                      <div className="flex-1 bg-white/5 rounded-full h-2">
                        <div
                          className="h-2 rounded-full transition-all"
                          style={{ width: `${barWidth}%`, background: color }}
                        />
                      </div>
                      <span className="text-xs font-mono w-16 text-right" style={{ color }}>
                        {driver.impact > 0 ? "+" : ""}{driver.impact.toFixed(4)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Full feature importance table */}
            <h3 className="text-white text-sm font-semibold mb-3">All Feature SHAP Values</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">Feature</th>
                    <th className="text-right py-2 px-2">Value</th>
                    <th className="text-right py-2 px-2">SHAP</th>
                    <th className="text-right py-2 px-2">Direction</th>
                  </tr>
                </thead>
                <tbody>
                  {explanation.feature_importance.map((fi, i) => (
                    <tr key={i} className="border-b border-white/3 hover:bg-white/3">
                      <td className="py-1.5 px-2 text-slate-300 capitalize">{fi.feature.replace("_", " ")}</td>
                      <td className="py-1.5 px-2 text-right font-mono text-white">{fi.value.toFixed(3)}</td>
                      <td
                        className="py-1.5 px-2 text-right font-mono"
                        style={{ color: fi.direction === "positive" ? "#10b981" : "#ef4444" }}
                      >
                        {fi.shap_value > 0 ? "+" : ""}{fi.shap_value.toFixed(5)}
                      </td>
                      <td className="py-1.5 px-2 text-right">
                        {fi.direction === "positive" ? (
                          <ArrowUp size={12} className="inline text-emerald-400" />
                        ) : (
                          <ArrowDown size={12} className="inline text-red-400" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* Global feature ranking */}
        {globalRanking.length > 0 && (
          <div className="mt-5">
            <h3 className="text-white text-sm font-semibold mb-3 flex items-center gap-2">
              <BarChart3 size={14} className="text-amber-400" />
              Global Feature Importance (across 20 states)
            </h3>
            <div className="space-y-2">
              {globalRanking.map(item => {
                const maxShap = globalRanking[0]?.mean_abs_shap || 0.001;
                const barWidth = (item.mean_abs_shap / maxShap) * 100;
                return (
                  <div key={item.rank} className="flex items-center gap-3">
                    <span className="text-xs text-slate-500 w-5 text-right">#{item.rank}</span>
                    <span className="text-xs text-slate-300 w-28 capitalize">{item.feature.replace("_", " ")}</span>
                    <div className="flex-1 bg-white/5 rounded-full h-2">
                      <div
                        className="h-2 rounded-full"
                        style={{ width: `${barWidth}%`, background: `hsl(${40 + item.rank * 25}, 70%, 55%)` }}
                      />
                    </div>
                    <span className="text-xs font-mono text-slate-400 w-16 text-right">
                      {item.mean_abs_shap.toFixed(5)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
