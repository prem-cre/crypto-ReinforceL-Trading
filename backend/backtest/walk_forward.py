"""Walk-forward validation engine.

Splits historical OHLCV data into train/test windows and evaluates
the RL agent on out-of-sample windows — essential for credible backtest results.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from backend.metrics.performance import compute_all

logger = logging.getLogger(__name__)


def _split_windows(
    df: pd.DataFrame,
    train_pct: float = 0.7,
    n_splits: int = 4,
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    n = len(df)
    window = n // n_splits
    splits = []
    for i in range(n_splits):
        start = i * window
        mid = start + int(window * train_pct)
        end = start + window
        if end > n:
            end = n
        if mid >= end:
            continue
        splits.append((df.iloc[start:mid], df.iloc[mid:end]))
    return splits


def run_walk_forward(
    agent,
    df_indicators: pd.DataFrame,
    env_cls,
    initial_balance: float = 10000.0,
    n_splits: int = 4,
) -> Dict[str, Any]:
    splits = _split_windows(df_indicators, n_splits=n_splits)
    all_trades: List[Dict[str, Any]] = []
    all_equity: List[float] = [initial_balance]
    split_results = []

    for i, (train_df, test_df) in enumerate(splits):
        env = env_cls(test_df, initial_balance=initial_balance)
        obs = env.reset()
        done = False
        window_trades = []
        window_equity = [initial_balance]

        while not done:
            action, _, _ = agent.select_action(obs)
            obs, _reward, done, info = env.step(action)
            if info.get("trade"):
                window_trades.append(info["trade"])
            window_equity.append(info.get("portfolio_value", initial_balance))

        benchmark_prices = test_df["close"].tolist() if "close" in test_df.columns else []
        split_metrics = compute_all(window_trades, window_equity, initial_balance, benchmark_prices)
        split_metrics["split"] = i + 1
        split_metrics["rows"] = len(test_df)
        split_results.append(split_metrics)
        all_trades.extend(window_trades)

        # Chain equity curves
        if len(all_equity) > 1:
            scale = window_equity[0] / all_equity[-1] if all_equity[-1] else 1
            all_equity.extend([v / scale for v in window_equity[1:]])
        else:
            all_equity.extend(window_equity[1:])

    benchmark_prices_full = df_indicators["close"].tolist() if "close" in df_indicators.columns else []
    combined = compute_all(all_trades, all_equity, initial_balance, benchmark_prices_full)
    combined["splits"] = split_results
    combined["equityCurve"] = [
        {"step": i, "equity": round(v, 2)} for i, v in enumerate(all_equity)
    ]
    combined["trades"] = all_trades
    return combined
