"""Risk management module — Phase 5.

Provides:
- Kelly-fraction position sizing (capped at 2% account risk)
- Portfolio Value-at-Risk (historical simulation)
- Drawdown circuit breaker (auto-pause beyond max drawdown)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

MAX_RISK_PER_TRADE = 0.02     # 2% of account per trade
MAX_KELLY_FRACTION = 0.25     # cap Kelly at 25%
MAX_DRAWDOWN_PAUSE = 0.15     # pause if drawdown exceeds 15%
VAR_CONFIDENCE = 0.95


class RiskManager:
    def __init__(
        self,
        initial_balance: float = 10000.0,
        max_risk_pct: float = MAX_RISK_PER_TRADE,
        max_drawdown_pct: float = MAX_DRAWDOWN_PAUSE,
    ) -> None:
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.max_risk_pct = max_risk_pct
        self.max_drawdown_pct = max_drawdown_pct
        self._paused = False
        self._trade_returns: List[float] = []

    def record_return(self, pnl: float, balance: float) -> None:
        self._trade_returns.append(pnl / max(balance, 1))
        self.peak_balance = max(self.peak_balance, balance)

    @property
    def current_drawdown(self) -> float:
        return (self.peak_balance - self.initial_balance) / self.peak_balance

    def is_paused(self, current_balance: float) -> bool:
        dd = (self.peak_balance - current_balance) / max(self.peak_balance, 1)
        if dd >= self.max_drawdown_pct:
            if not self._paused:
                logger.warning(f"Circuit breaker triggered: drawdown={dd:.1%}")
            self._paused = True
        else:
            self._paused = False
        return self._paused

    def position_size(
        self,
        balance: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        price: float,
    ) -> float:
        if self.is_paused(balance):
            return 0.0

        # Kelly fraction
        if avg_loss != 0 and win_rate > 0:
            b = abs(avg_win / avg_loss)
            kelly = (win_rate * b - (1 - win_rate)) / b
            kelly = max(0.0, min(kelly, MAX_KELLY_FRACTION))
        else:
            kelly = self.max_risk_pct

        # Cap by max risk per trade
        risk_amount = balance * min(kelly / 2, self.max_risk_pct)
        units = risk_amount / max(price, 1e-10)
        return round(units, 6)

    def portfolio_var(self, balance: float) -> Dict[str, float]:
        if len(self._trade_returns) < 20:
            return {"var_95": 0.0, "cvar_95": 0.0, "samples": len(self._trade_returns)}
        rets = np.array(self._trade_returns)
        var = float(np.percentile(rets, (1 - VAR_CONFIDENCE) * 100))
        cvar = float(np.mean(rets[rets <= var]))
        return {
            "var_95": round(var * balance, 2),
            "cvar_95": round(cvar * balance, 2),
            "samples": len(rets),
        }

    def report(self, balance: float) -> Dict[str, Any]:
        return {
            "paused": self.is_paused(balance),
            "currentDrawdown": round(
                (self.peak_balance - balance) / max(self.peak_balance, 1) * 100, 2
            ),
            "peakBalance": round(self.peak_balance, 2),
            "portfolioVaR": self.portfolio_var(balance),
        }
