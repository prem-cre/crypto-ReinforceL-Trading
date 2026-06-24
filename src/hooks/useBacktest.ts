import { useState } from 'react';
import type { BacktestResult } from '../types/trading';
import type { BacktestConfig } from '../components/backtest/BacktestConfig';
import { apiFetch } from '../lib/api';

export const useBacktest = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<BacktestResult>();

  const startBacktest = async (config: BacktestConfig) => {
    try {
      setIsRunning(true);

      const response = await apiFetch('/backtest', {
        method: 'POST',
        body: JSON.stringify({
          pair: config.pair,
          timeframe: config.timeframe,
          initialBalance: config.initialBalance,
        }),
      });

      if (!response.ok) throw new Error('Failed to run backtest on backend');
      const data = await response.json();

      setResults({
        totalPnl: data.totalPnL,
        winRate: data.winRate,
        totalTrades: data.totalTrades,
        averagePnl: data.averagePnL,
        trades: data.trades,
        equityCurve: data.equityCurve,
        sharpe: data.sharpe,
        sortino: data.sortino,
        maxDrawdownPct: data.maxDrawdownPct,
        benchmarkPnlPct: data.benchmarkPnlPct,
        alpha: data.alpha,
      });
    } catch (error) {
      console.error('Backtest error:', error);
    } finally {
      setIsRunning(false);
    }
  };

  return {
    startBacktest,
    isRunning,
    results,
  };
};
