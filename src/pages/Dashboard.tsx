import React, { useState, useEffect } from "react";
import {
  BarChart3, ArrowDownUp, History, Settings,
  PlayCircle, Brain, LineChart, Zap, Search,
  TrendingUp, TrendingDown, Activity, ChevronDown
} from "lucide-react";
import { TradingSignalCard } from "../components/trading/TradingSignalCard";
import { mockTradingSignal, availablePairs } from "../lib/constants/mockData";
import { useTradingSignal } from "../hooks/useTradingSignal";
import { BacktestConfig } from "../components/backtest/BacktestConfig";
import { BacktestResults } from "../components/backtest/BacktestResults";
import { TradingMetrics } from "../components/trading/TradingMetrics";
import { LearningMetrics } from "../components/learning/LearningMetrics";
import { useBacktest } from '../hooks/useBacktest';
import { WS_URL } from '../lib/api';
import { Welcome } from '../components/welcome/Welcome';
import { SignalRationale } from '../components/SignalRationale';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useMarketData } from '../hooks/useMarketData';

const TABS = [
  { key: "dashboard", label: "Overview", icon: BarChart3 },
  { key: "signals",   label: "Signals",  icon: ArrowDownUp },
  { key: "backtest",  label: "Backtest", icon: PlayCircle },
  { key: "live",      label: "Live Trade",icon: LineChart },
  { key: "learning",  label: "Learning", icon: Brain },
  { key: "history",   label: "History",  icon: History },
  { key: "settings",  label: "Settings", icon: Settings },
];

export function Dashboard() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [selectedPair, setSelectedPair] = useState("BTC/USDT");
  const [pairInput, setPairInput] = useState("");
  const [activeTab, setActiveTab] = useState("dashboard");
  const [showPairDropdown, setShowPairDropdown] = useState(false);
  const [settings, setSettings] = useState({ leverage: 10, capital: 100, exchange: "binance", riskRewardRatio: "2" });

  const { marketData } = useMarketData();
  const { tradingSignal, loading, error, generateTradingSignal } = useTradingSignal();
  const { startBacktest, isRunning, results } = useBacktest();

  const [tradingMetrics, setTradingMetrics] = useState({
    balance: 10000, pnl: 0.0, winRate: 100, totalTrades: 0, openPositions: 0, recentSignals: [] as any[]
  });
  const [learningMetrics, setLearningMetrics] = useState({
    episodeRewards: [] as number[], explorationRate: 0, learningRate: 0.001,
    totalEpisodes: 0, currentEpisode: 0, averageReward: 0, bestReward: 0,
  });

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "initial" || data.type === "update") {
          const status = data.status || {};
          const rl = status.rlStatus || {};
          setTradingMetrics({
            balance: status.balance || 10000,
            pnl: data.performance?.forwardTest?.totalPnL || 0.0,
            winRate: data.performance?.forwardTest?.winRate || 100,
            totalTrades: data.performance?.forwardTest?.totalTrades || 0,
            openPositions: status.position ? 1 : 0,
            recentSignals: data.signals || []
          });
          setLearningMetrics({
            episodeRewards: rl.episodeRewards || [],
            explorationRate: rl.explorationRate || 0,
            learningRate: rl.learningRate || 0.001,
            totalEpisodes: rl.totalEpisodes || 0,
            currentEpisode: rl.totalEpisodes || 0,
            averageReward: rl.averageReward || 0.0,
            bestReward: rl.bestReward || 0.0
          });
        }
      } catch { /* ignore parse errors */ }
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    const tab = searchParams.get('tab');
    if (tab) setActiveTab(tab);
  }, [searchParams]);

  useEffect(() => {
    generateTradingSignal(selectedPair, settings);
  }, []);

  const handleTabChange = (key: string) => {
    setActiveTab(key);
    navigate(`/dashboard?tab=${key}`, { replace: true });
  };

  const handlePairSearch = () => {
    const formatted = pairInput.trim().toUpperCase();
    if (formatted) {
      setSelectedPair(formatted);
      generateTradingSignal(formatted, settings);
      setPairInput("");
    }
  };

  const btcData = marketData["BTC/USDT"];
  const ethData = marketData["ETH/USDT"];

  const renderSignalsContent = () => (
    <div className="space-y-4">
      <div className="dash-card">
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center mb-5">
          <div className="relative flex-1 max-w-xs">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              className="dash-input pl-9"
              placeholder="Enter pair e.g. ETH/USDT"
              value={pairInput}
              onChange={e => setPairInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handlePairSearch()}
            />
          </div>
          <div className="relative">
            <button
              className="dash-select flex items-center gap-2"
              onClick={() => setShowPairDropdown(v => !v)}
            >
              {selectedPair} <ChevronDown size={14} />
            </button>
            {showPairDropdown && (
              <div className="absolute top-full mt-1 left-0 z-50 bg-[#1a1f2e] border border-white/10 rounded-xl shadow-2xl overflow-hidden min-w-[140px]">
                {availablePairs.map(pair => (
                  <button
                    key={pair}
                    className="block w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-white/5 transition-colors"
                    onClick={() => { setSelectedPair(pair); generateTradingSignal(pair, settings); setShowPairDropdown(false); }}
                  >
                    {pair}
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            className="btn-primary"
            onClick={handlePairSearch}
            disabled={loading}
          >
            {loading ? <span className="flex items-center gap-2"><span className="spinner" />Analyzing…</span> : "Generate Signal"}
          </button>
        </div>

        {error && <div className="text-red-400 text-sm mb-3 p-3 bg-red-500/10 rounded-lg border border-red-500/20">{error}</div>}

        {loading ? (
          <div className="flex items-center justify-center py-16 gap-3 text-slate-400">
            <span className="spinner" /> Generating AI signal…
          </div>
        ) : tradingSignal ? (
          <div className="space-y-4">
            <TradingSignalCard signal={tradingSignal} />
            <SignalRationale
              rationale={tradingSignal.rationale}
              citations={tradingSignal.citations}
              sentiment_score={tradingSignal.sentiment_score}
            />
          </div>
        ) : (
          <TradingSignalCard signal={{ ...mockTradingSignal, pair: selectedPair }} />
        )}
      </div>
    </div>
  );

  const renderSettingsContent = () => (
    <div className="dash-card max-w-lg">
      <h2 className="text-lg font-semibold text-white mb-5">Bot Settings</h2>
      <div className="grid grid-cols-2 gap-4 mb-5">
        {[
          { label: "Default Leverage", key: "leverage", type: "number" },
          { label: "Default Capital ($)", key: "capital", type: "number" },
        ].map(({ label, key, type }) => (
          <div key={key}>
            <label className="block text-xs text-slate-400 mb-1.5">{label}</label>
            <input
              className="dash-input"
              type={type}
              value={(settings as any)[key]}
              onChange={e => setSettings({ ...settings, [key]: Number(e.target.value) })}
            />
          </div>
        ))}
      </div>
      <button className="btn-primary" onClick={() => generateTradingSignal(selectedPair, settings)}>
        Save &amp; Apply
      </button>
    </div>
  );

  const activeTabObj = TABS.find(t => t.key === activeTab);

  return (
    <div className="dash-root">
      {/* Sidebar */}
      <aside className="dash-sidebar">
        <div className="px-5 py-5 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center">
              <Zap size={16} className="text-white" />
            </div>
            <div>
              <p className="text-white font-semibold text-sm leading-none">PPO RL Bot</p>
              <p className="text-slate-500 text-xs mt-0.5">Crypto Trader</p>
            </div>
          </div>
        </div>

        {/* Market ticker */}
        <div className="px-3 py-3 border-b border-white/5 space-y-1.5">
          {btcData && (
            <div className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-white/3">
              <span className="text-xs text-slate-400">BTC/USDT</span>
              <span className="text-xs font-mono text-white">${Number(btcData.price).toLocaleString()}</span>
            </div>
          )}
          {ethData && (
            <div className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-white/3">
              <span className="text-xs text-slate-400">ETH/USDT</span>
              <span className="text-xs font-mono text-white">${Number(ethData.price).toLocaleString()}</span>
            </div>
          )}
        </div>

        <nav className="px-3 py-3 flex-1">
          {TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => handleTabChange(key)}
              className={`nav-item ${activeTab === key ? "nav-item-active" : ""}`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </nav>

        <div className="px-4 py-4 border-t border-white/5">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-slate-400">Bot running</span>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="dash-main">
        {/* Top bar */}
        <header className="dash-topbar">
          <div>
            <h1 className="text-white font-semibold text-base">{activeTabObj?.label ?? "Dashboard"}</h1>
            <p className="text-slate-500 text-xs">PPO Reinforcement Learning · Paper Trading</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
              <Activity size={12} className="text-emerald-400" />
              <span className="text-xs text-emerald-400 font-medium">Live</span>
            </div>
            <div className="text-right">
              <p className="text-white text-sm font-semibold">${tradingMetrics.balance.toLocaleString()}</p>
              <p className={`text-xs ${tradingMetrics.pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {tradingMetrics.pnl >= 0 ? "+" : ""}{tradingMetrics.pnl.toFixed(2)}%
              </p>
            </div>
          </div>
        </header>

        <div className="dash-content">
          {activeTab === "dashboard" && <Welcome />}
          {activeTab === "signals"   && renderSignalsContent()}
          {activeTab === "backtest"  && (
            <div className="space-y-4">
              <BacktestConfig onStartBacktest={startBacktest} isLoading={isRunning} />
              {results && (
                <BacktestResults results={{
                  totalPnL: results.totalPnl || 0,
                  averagePnL: results.averagePnl || 0,
                  winRate: results.winRate || 0,
                  totalTrades: results.totalTrades || 0,
                  tradeHistory: results.trades || [],
                  sharpe: results.sharpe,
                  sortino: results.sortino,
                  maxDrawdownPct: results.maxDrawdownPct,
                  benchmarkPnlPct: results.benchmarkPnlPct,
                  alpha: results.alpha,
                }} />
              )}
            </div>
          )}
          {activeTab === "live"     && <TradingMetrics {...tradingMetrics} />}
          {activeTab === "learning" && <LearningMetrics {...learningMetrics} />}
          {activeTab === "history"  && (
            <div className="dash-card text-slate-400 text-sm">
              No trades recorded yet. Trades executed during live sessions appear here.
            </div>
          )}
          {activeTab === "settings" && renderSettingsContent()}
        </div>
      </main>
    </div>
  );
}
