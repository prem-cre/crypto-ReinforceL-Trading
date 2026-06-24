import React from 'react';
import { BarChart2, LineChart, Brain, Zap, TrendingUp, Shield } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const cards = [
  {
    icon: BarChart2,
    color: "from-violet-500 to-purple-600",
    bg: "rgba(139,92,246,0.08)",
    border: "rgba(139,92,246,0.2)",
    title: "Backtesting",
    desc: "Walk-forward validation with Sharpe, Sortino & Calmar ratios. Compare strategy vs buy-and-hold.",
    action: "Start Backtest",
    tab: "backtest",
  },
  {
    icon: LineChart,
    color: "from-cyan-500 to-blue-600",
    bg: "rgba(6,182,212,0.08)",
    border: "rgba(6,182,212,0.2)",
    title: "Live Trading",
    desc: "Real-time PPO signals with Kelly-fraction position sizing and 15% drawdown circuit breaker.",
    action: "Start Trading",
    tab: "live",
  },
  {
    icon: Brain,
    color: "from-emerald-500 to-teal-600",
    bg: "rgba(16,185,129,0.08)",
    border: "rgba(16,185,129,0.2)",
    title: "RL Learning",
    desc: "Monitor PPO actor-critic training, episode rewards, exploration rate and policy convergence.",
    action: "View Metrics",
    tab: "learning",
  },
];

const stats = [
  { icon: Zap, label: "RL Algorithm", value: "PPO Actor-Critic" },
  { icon: TrendingUp, label: "Signal Source", value: "Gemini + RAG" },
  { icon: Shield, label: "Risk Model", value: "Kelly + VaR 95%" },
  { icon: BarChart2, label: "Validation", value: "Walk-Forward 4-Fold" },
];

export const Welcome: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium mb-4"
          style={{ background: "rgba(139,92,246,0.12)", color: "#a78bfa", border: "1px solid rgba(139,92,246,0.2)" }}>
          <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
          PPO RL Model Active
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">Crypto RL Trading Bot</h1>
        <p className="text-slate-400 max-w-xl">
          Autonomous trading powered by Proximal Policy Optimization with LLM-grounded signal rationale,
          real-time RAG from CryptoPanic &amp; Reddit, and production MLOps.
        </p>
      </div>

      {/* Stat strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {stats.map(({ icon: Icon, label, value }) => (
          <div key={label} className="dash-card py-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ background: "rgba(139,92,246,0.12)" }}>
              <Icon size={16} className="text-violet-400" />
            </div>
            <div>
              <p className="text-xs text-slate-500">{label}</p>
              <p className="text-sm font-semibold text-white">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {cards.map(({ icon: Icon, color, bg, border, title, desc, action, tab }) => (
          <div
            key={tab}
            className="hero-card"
            style={{ background: bg, borderColor: border }}
          >
            <div className={`hero-icon bg-gradient-to-br ${color}`}>
              <Icon size={20} className="text-white" />
            </div>
            <h3 className="text-white font-semibold text-base">{title}</h3>
            <p className="text-slate-400 text-sm flex-1">{desc}</p>
            <button
              className="btn-primary w-full justify-center mt-2"
              onClick={() => navigate(`/dashboard?tab=${tab}`)}
            >
              {action}
            </button>
          </div>
        ))}
      </div>

      {/* Architecture note */}
      <div className="dash-card">
        <div className="accent-bar w-16" />
        <h3 className="text-white font-semibold mb-3">Tech Stack</h3>
        <div className="flex flex-wrap gap-2">
          {["PyTorch PPO", "FastAPI", "Neon pgvector", "Gemini 2.0 Flash", "W&B MLOps",
            "HF Hub", "KS Drift Detection", "Kelly Sizing", "Walk-Forward CV"].map(tag => (
            <span key={tag} className="px-2.5 py-1 rounded-full text-xs font-medium"
              style={{ background: "rgba(255,255,255,0.05)", color: "#9ca3af", border: "1px solid rgba(255,255,255,0.08)" }}>
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
