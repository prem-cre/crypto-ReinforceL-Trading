"""TradingBot: orchestrates exchange → analyzer → RL agent → paper trades.

Phase 1 changes:
- Accepts an optional async DB sessionmaker so trades/signals are persisted to Postgres.
- No more global, per-process in-memory lists as the source of truth (those are now caches).
- Same public surface so the FastAPI layer barely changes.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from backend.analysis.market_analyzer import MarketAnalyzer
from backend.config import settings
from backend.exchange.exchange_simulator import ExchangeSimulator
from backend.rl.rl_agent import RLAgent
from backend.rl.trading_env import TradingEnvironment

logger = logging.getLogger(__name__)


class TradingBot:
    def __init__(self, persist_fn: Optional[Callable[[str, Dict[str, Any]], "asyncio.Future"]] = None) -> None:
        self.exchange = ExchangeSimulator()
        self.analyzer = MarketAnalyzer()
        self.agent = RLAgent(state_size=settings.state_size, lr=settings.learning_rate, gamma=settings.gamma)

        self.is_running = False
        self.mode = "paper"
        self.trades: List[Dict[str, Any]] = []  # in-memory cache for WS broadcasts
        self.signals: List[Dict[str, Any]] = []
        self.active_symbol = settings.pairs_list[0] if settings.pairs_list else "BTC/USDT"
        self.timeframe = settings.timeframe

        self.balance = settings.initial_capital
        self.position: Optional[Dict[str, Any]] = None

        # Optional persistence hook injected by main.py at startup.
        # Signature: async fn(kind: "trade"|"signal", payload: dict) -> None
        self._persist = persist_fn

    # ─── Lifecycle ──────────────────────────────────────────────
    def connect(self) -> None:
        self.exchange.connect()

    def stop(self) -> None:
        self.is_running = False

    def get_status(self) -> Dict[str, Any]:
        return {
            "botStatus": "RUNNING" if self.is_running else "STOPPED",
            "activeSymbol": self.active_symbol,
            "mode": self.mode,
            "balance": self.balance,
            "timeframe": self.timeframe,
            "position": self.position,
            "modelVersion": self.agent.model_version or "untrained",
        }

    def get_trades(self) -> List[Dict[str, Any]]:
        return self.trades[-200:]

    def get_signals(self) -> List[Dict[str, Any]]:
        return self.signals[-200:]

    # ─── Signal generation ──────────────────────────────────────
    async def get_trading_signal(self, symbol: str) -> Dict[str, Any]:
        df = self.exchange.fetch_ohlcv(symbol, timeframe=self.timeframe, limit=100)
        df_indicators = self.analyzer.calculate_indicators(df)
        market_state = self.analyzer.get_market_state(df_indicators)

        last_row = df_indicators.iloc[-1]
        close = float(last_row["close"])

        pos_type_val = 0.0
        pos_pnl_val = 0.0
        if self.position:
            if self.position["type"] == "LONG":
                pos_type_val = 1.0
                pos_pnl_val = (close - self.position["entry_price"]) / self.position["entry_price"]
            else:
                pos_type_val = -1.0
                pos_pnl_val = (self.position["entry_price"] - close) / self.position["entry_price"]

        rsi = float(last_row["rsi"])
        macd_hist = float(last_row["macd_hist"])
        trend_val = 1 if market_state["trend"] == "UP" else (-1 if market_state["trend"] == "DOWN" else 0)
        vol_val = 1.0 if market_state["volatility"] == "HIGH" else (0.0 if market_state["volatility"] == "LOW" else 0.5)
        mom_val = 1 if market_state["momentum"] == "STRONG" else (-1 if market_state["momentum"] == "WEAK" else 0)
        regime_val = 1 if market_state["regime"] == "BULL" else -1

        obs = np.array(
            [
                trend_val,
                vol_val,
                0.5,
                mom_val,
                regime_val,
                pos_type_val,
                pos_pnl_val,
                0.0,
                (rsi - 50.0) / 50.0,
                macd_hist / close if close > 0 else 0,
            ],
            dtype=np.float32,
        )

        action, _logprob, _val = self.agent.select_action(obs)
        action_names = ["BUY", "SELL", "HOLD"]
        rec_action = action_names[action]
        confidence = 0.85 if rec_action != "HOLD" else 0.5

        signal = {
            "timestamp": int(time.time() * 1000),
            "pair": symbol,
            "type": rec_action,
            "price": close,
            "size": 0.1,
            "confidence": confidence,
            "reason": (
                f"RL Agent selected {rec_action} based on Market Trend={market_state['trend']}, "
                f"RSI={rsi:.1f}, Regime={market_state['regime']}"
            ),
        }
        self.signals.append(signal)
        await self._maybe_persist("signal", signal)
        return signal

    # ─── Backtest ───────────────────────────────────────────────
    async def execute_backtest(self, config: Dict[str, Any]) -> Dict[str, Any]:
        symbol = config.get("pair", "BTC/USDT")
        timeframe = config.get("timeframe", "1h")
        initial_balance = float(config.get("initialBalance", 10000.0))

        df = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=500)
        df_indicators = self.analyzer.calculate_indicators(df)

        env = TradingEnvironment(
            df_indicators,
            initial_balance=initial_balance,
            stop_loss_pct=settings.stop_loss_distance,
            take_profit_pct=settings.take_profit_distance,
        )

        obs = env.reset()
        done = False
        step_count = 0
        backtest_trades: List[Dict[str, Any]] = []
        equity_curve: List[Dict[str, Any]] = []

        while not done:
            action, _, _ = self.agent.select_action(obs)
            obs, _reward, done, info = env.step(action)

            equity_curve.append(
                {
                    "timestamp": int(df_indicators.iloc[step_count]["timestamp"].timestamp() * 1000),
                    "equity": info["equity"],
                }
            )

            if info["trade_executed"]:
                backtest_trades.append(
                    {
                        "timestamp": int(df_indicators.iloc[step_count]["timestamp"].timestamp() * 1000),
                        "pair": symbol,
                        "type": "SELL" if info["position_type"] is None and info["pnl"] != 0 else ("BUY" if action == 0 else "SELL"),
                        "price": float(df_indicators.iloc[step_count]["close"]),
                        "size": float(info["position_size"]),
                        "pnl": float(info["pnl"]),
                    }
                )

            step_count += 1
            if step_count >= len(df_indicators) - 1:
                break

        total_pnl = float(env.realized_pnl)
        pnl_pct = (total_pnl / initial_balance) * 100.0

        return {
            "totalPnL": pnl_pct,
            "winRate": float(env.win_count / env.trade_count * 100) if env.trade_count > 0 else 0.0,
            "totalTrades": env.trade_count,
            "averagePnL": float(total_pnl / env.trade_count) if env.trade_count > 0 else 0.0,
            "trades": backtest_trades,
            "equityCurve": equity_curve,
        }

    # ─── Live paper-trading loop ────────────────────────────────
    async def run_loop(self) -> None:
        self.is_running = True
        logger.info(f"Trading loop started for {self.active_symbol} in {self.mode} mode.")

        while self.is_running:
            try:
                signal = await self.get_trading_signal(self.active_symbol)
                action = signal["type"]
                price = signal["price"]

                if action == "BUY" and (not self.position or self.position["type"] == "SHORT"):
                    if self.position and self.position["type"] == "SHORT":
                        pnl = self.position["size"] * (self.position["entry_price"] - price)
                        self.balance += pnl
                        await self._record_trade("BUY_TO_COVER", price, self.position["size"], pnl)
                        self.position = None

                    size = (self.balance * 0.95) / price
                    self.position = {
                        "type": "LONG",
                        "size": size,
                        "entry_price": price,
                        "stop_loss": price * (1 - settings.stop_loss_distance),
                        "take_profit": price * (1 + settings.take_profit_distance),
                    }
                    await self._record_trade("BUY_LONG", price, size, 0.0)

                elif action == "SELL" and (not self.position or self.position["type"] == "LONG"):
                    if self.position and self.position["type"] == "LONG":
                        pnl = self.position["size"] * (price - self.position["entry_price"])
                        self.balance += pnl
                        await self._record_trade("SELL_CLOSE", price, self.position["size"], pnl)
                        self.position = None

                    size = (self.balance * 0.95) / price
                    self.position = {
                        "type": "SHORT",
                        "size": size,
                        "entry_price": price,
                        "stop_loss": price * (1 + settings.stop_loss_distance),
                        "take_profit": price * (1 - settings.take_profit_distance),
                    }
                    await self._record_trade("SELL_SHORT", price, size, 0.0)

                await asyncio.sleep(15)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in trading loop: {e}")
                await asyncio.sleep(5)

        self.is_running = False

    async def _record_trade(self, side: str, price: float, size: float, pnl: float) -> None:
        trade = {
            "timestamp": int(time.time() * 1000),
            "pair": self.active_symbol,
            "type": side,
            "price": price,
            "size": size,
            "pnl": pnl,
        }
        self.trades.append(trade)
        await self._maybe_persist("trade", trade)

    async def _maybe_persist(self, kind: str, payload: Dict[str, Any]) -> None:
        if not self._persist:
            return
        try:
            await self._persist(kind, payload)
        except Exception as e:
            logger.warning(f"persist({kind}) failed: {e}")
