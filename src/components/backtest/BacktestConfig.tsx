import React, { useState } from 'react';
import { PlayCircle } from 'lucide-react';
import { availablePairs } from '../../lib/constants/mockData';

export interface BacktestConfig {
  pair: string;
  timeframe: string;
  startDate: Date;
  endDate: Date;
  initialBalance: number;
}

interface BacktestConfigProps {
  onStartBacktest: (config: BacktestConfig) => void;
  isLoading?: boolean;
}

export const BacktestConfig: React.FC<BacktestConfigProps> = ({ onStartBacktest, isLoading = false }) => {
  const [pair, setPair] = useState('BTC/USDT');
  const [timeframe, setTimeframe] = useState('1h');
  const [initialBalance, setInitialBalance] = useState(10000);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const end = new Date();
    const start = new Date();
    start.setFullYear(start.getFullYear() - 1);
    onStartBacktest({ pair, timeframe, startDate: start, endDate: end, initialBalance });
  };

  const selectClass = "dash-input appearance-none";

  return (
    <div className="dash-card">
      <div className="accent-bar w-12" />
      <h2 className="text-white font-semibold mb-5">Backtest Configuration</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-xs text-slate-400 mb-1.5">Trading Pair</label>
          <select className={selectClass} value={pair} onChange={e => setPair(e.target.value)}
            style={{ background: "rgba(255,255,255,0.04)", borderColor: "rgba(255,255,255,0.1)", color: "#d1d5db" }}>
            {availablePairs.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1.5">Timeframe</label>
          <select className={selectClass} value={timeframe} onChange={e => setTimeframe(e.target.value)}
            style={{ background: "rgba(255,255,255,0.04)", borderColor: "rgba(255,255,255,0.1)", color: "#d1d5db" }}>
            {[["1m","1 Minute"],["5m","5 Minutes"],["15m","15 Minutes"],["1h","1 Hour"],["4h","4 Hours"],["1d","1 Day"]].map(([v,l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1.5">Initial Balance (USDT)</label>
          <input
            className="dash-input"
            type="number"
            min={100}
            step={100}
            value={initialBalance}
            onChange={e => setInitialBalance(Number(e.target.value))}
          />
        </div>
        <div className="sm:col-span-3 pt-1">
          <button type="submit" className="btn-primary" disabled={isLoading}>
            {isLoading ? (
              <><span className="spinner" /> Running backtest…</>
            ) : (
              <><PlayCircle size={15} /> Start Backtest</>
            )}
          </button>
          <p className="text-xs text-slate-500 mt-2">Runs on last 500 candles of live market data from the exchange.</p>
        </div>
      </form>
    </div>
  );
};
