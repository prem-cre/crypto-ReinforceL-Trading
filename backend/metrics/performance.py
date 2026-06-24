"""Performance metrics for backtesting and live trading evaluation.

Computes Sharpe, Sortino, Calmar, max drawdown, win rate, profit factor,
and buy-and-hold benchmark comparison — the numbers that go on the resume.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np


def _returns_from_equity(equity: List[float]) -> np.ndarray:
    eq = np.array(equity, dtype=float)
    if len(eq) < 2:
        return np.array([])
    return np.diff(eq) / np.maximum(eq[:-1], 1e-10)


def sharpe_ratio(equity_curve: List[float], risk_free: float = 0.0, periods_per_year: int = 252) -> float:
    rets = _returns_from_equity(equity_curve)
    if len(rets) < 2 or np.std(rets) == 0:
        return 0.0
    excess = rets - risk_free / periods_per_year
    return float(np.sqrt(periods_per_year) * np.mean(excess) / np.std(rets, ddof=1))


def sortino_ratio(equity_curve: List[float], risk_free: float = 0.0, periods_per_year: int = 252) -> float:
    rets = _returns_from_equity(equity_curve)
    if len(rets) < 2:
        return 0.0
    downside = rets[rets < 0]
    if len(downside) == 0 or np.std(downside) == 0:
        return float("inf") if np.mean(rets) > 0 else 0.0
    excess = rets - risk_free / periods_per_year
    return float(np.sqrt(periods_per_year) * np.mean(excess) / np.std(downside, ddof=1))


def max_drawdown(equity_curve: List[float]) -> float:
    eq = np.array(equity_curve, dtype=float)
    if len(eq) < 2:
        return 0.0
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / np.maximum(peak, 1e-10)
    return float(np.min(dd))


def calmar_ratio(equity_curve: List[float], periods_per_year: int = 252) -> float:
    rets = _returns_from_equity(equity_curve)
    if len(rets) == 0:
        return 0.0
    annual_return = float(np.mean(rets) * periods_per_year)
    mdd = abs(max_drawdown(equity_curve))
    return annual_return / mdd if mdd > 1e-6 else float("inf")


def compute_all(
    trades: List[Dict[str, Any]],
    equity_curve: List[float],
    initial_balance: float,
    benchmark_prices: Optional[List[float]] = None,
) -> Dict[str, Any]:
    pnls = [t.get("pnl", 0.0) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    total_pnl = sum(pnls)
    win_rate = len(wins) / len(pnls) if pnls else 0.0
    profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float("inf")
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss) if pnls else 0.0

    mdd = max_drawdown(equity_curve)

    # Benchmark: buy-and-hold on the asset for the same period
    benchmark_pnl_pct = 0.0
    if benchmark_prices and len(benchmark_prices) >= 2:
        benchmark_pnl_pct = (benchmark_prices[-1] - benchmark_prices[0]) / benchmark_prices[0]

    return {
        "totalPnl": round(total_pnl, 4),
        "totalPnlPct": round(total_pnl / initial_balance * 100, 2) if initial_balance else 0.0,
        "totalTrades": len(trades),
        "winRate": round(win_rate * 100, 1),
        "profitFactor": round(profit_factor, 2) if profit_factor != float("inf") else 99.0,
        "expectancy": round(expectancy, 4),
        "avgWin": round(avg_win, 4),
        "avgLoss": round(avg_loss, 4),
        "sharpe": round(sharpe_ratio(equity_curve), 3),
        "sortino": round(sortino_ratio(equity_curve), 3),
        "calmar": round(calmar_ratio(equity_curve), 3),
        "maxDrawdownPct": round(mdd * 100, 2),
        "benchmarkPnlPct": round(benchmark_pnl_pct * 100, 2),
        "alpha": round((total_pnl / initial_balance - benchmark_pnl_pct) * 100, 2) if initial_balance else 0.0,
    }
