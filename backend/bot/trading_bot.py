import asyncio
from typing import Dict, Any, List
import pandas as pd
import numpy as np
import time
from backend.config import settings
from backend.exchange.exchange_simulator import ExchangeSimulator
from backend.analysis.market_analyzer import MarketAnalyzer
from backend.rl.rl_agent import RLAgent
from backend.rl.trading_env import TradingEnvironment

class TradingBot:
    def __init__(self):
        self.exchange = ExchangeSimulator()
        self.analyzer = MarketAnalyzer()
        self.agent = RLAgent(state_size=10, lr=settings.learning_rate, gamma=settings.gamma)
        
        self.is_running = False
        self.mode = "paper"  # "paper" or "real"
        self.trades = []
        self.signals = []
        self.active_symbol = settings.pairs_list[0] if settings.pairs_list else "BTC/USDT"
        self.timeframe = settings.timeframe
        
        # Paper position tracking
        self.balance = settings.initial_capital
        self.position = None  # None or Dict with 'type' ('LONG'/'SHORT'), 'size', 'entry_price', 'stop_loss', 'take_profit'

    def connect(self):
        self.exchange.connect()

    def get_status(self) -> Dict[str, Any]:
        return {
            "botStatus": "RUNNING" if self.is_running else "STOPPED",
            "activeSymbol": self.active_symbol,
            "mode": self.mode,
            "balance": self.balance,
            "timeframe": self.timeframe,
            "position": self.position
        }

    def get_trades(self) -> List[Dict[str, Any]]:
        return self.trades

    def get_signals(self) -> List[Dict[str, Any]]:
        return self.signals

    async def get_trading_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Generate a live signal for the given symbol using the RL model.
        """
        # 1. Fetch recent OHLCV history
        df = self.exchange.fetch_ohlcv(symbol, timeframe=self.timeframe, limit=100)
        df_indicators = self.analyzer.calculate_indicators(df)
        market_state = self.analyzer.get_market_state(df_indicators)

        # 2. Build current state observation vector
        last_row = df_indicators.iloc[-1]
        close = float(last_row['close'])
        
        pos_type_val = 0.0
        pos_pnl_val = 0.0
        if self.position:
            if self.position['type'] == 'LONG':
                pos_type_val = 1.0
                pos_pnl_val = (close - self.position['entry_price']) / self.position['entry_price']
            else:
                pos_type_val = -1.0
                pos_pnl_val = (self.position['entry_price'] - close) / self.position['entry_price']

        rsi = float(last_row['rsi'])
        macd_hist = float(last_row['macd_hist'])
        
        trend_val = 1 if market_state['trend'] == "UP" else (-1 if market_state['trend'] == "DOWN" else 0)
        vol_val = 1.0 if market_state['volatility'] == "HIGH" else (0.0 if market_state['volatility'] == "LOW" else 0.5)
        mom_val = 1 if market_state['momentum'] == "STRONG" else (-1 if market_state['momentum'] == "WEAK" else 0)
        regime_val = 1 if market_state['regime'] == "BULL" else -1

        obs = np.array([
            trend_val,
            vol_val,
            0.5,  # volume
            mom_val,
            regime_val,
            pos_type_val,
            pos_pnl_val,
            0.0,  # drawdown
            (rsi - 50.0) / 50.0,
            macd_hist / close if close > 0 else 0
        ], dtype=np.float32)

        # 3. Predict action using PPO agent
        action, logprob, val = self.agent.select_action(obs)
        action_names = ["BUY", "SELL", "HOLD"]
        rec_action = action_names[action]
        
        # Simple confidence mapping
        confidence = 0.85 if rec_action != "HOLD" else 0.5

        signal = {
            "timestamp": int(time.time() * 1000),
            "pair": symbol,
            "type": rec_action,
            "price": close,
            "size": 0.1,  # standard fraction
            "confidence": confidence,
            "reason": f"RL Agent selected {rec_action} based on Market Trend={market_state['trend']}, RSI={rsi:.1f}, Regime={market_state['regime']}"
        }
        
        self.signals.append(signal)
        return signal

    async def execute_backtest(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs a historical backtest of the RL PPO model over retrieved OHLCV candles.
        """
        symbol = config.get("pair", "BTC/USDT")
        timeframe = config.get("timeframe", "1h")
        initial_balance = float(config.get("initialBalance", 10000.0))
        
        # Fetch larger candle history for backtest
        df = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=500)
        df_indicators = self.analyzer.calculate_indicators(df)
        
        # Initialize env
        env = TradingEnvironment(
            df_indicators,
            initial_balance=initial_balance,
            stop_loss_pct=settings.stop_loss_distance,
            take_profit_pct=settings.take_profit_distance
        )
        
        obs = env.reset()
        done = False
        step_count = 0
        
        backtest_trades = []
        equity_curve = []
        
        while not done:
            action, _, _ = self.agent.select_action(obs)
            obs, reward, done, info = env.step(action)
            
            # Record equity
            equity_curve.append({
                "timestamp": int(df_indicators.iloc[step_count]['timestamp'].timestamp() * 1000),
                "equity": info["equity"]
            })
            
            # Record any trade execution
            if info["trade_executed"]:
                backtest_trades.append({
                    "timestamp": int(df_indicators.iloc[step_count]['timestamp'].timestamp() * 1000),
                    "pair": symbol,
                    "type": "SELL" if info["position_type"] is None and info["pnl"] != 0 else ("BUY" if action == 0 else "SELL"),
                    "price": float(df_indicators.iloc[step_count]['close']),
                    "size": float(info["position_size"]),
                    "pnl": float(info["pnl"])
                })
            
            step_count += 1
            if step_count >= len(df_indicators) - 1:
                break
                
        # Final result formatting
        total_pnl = float(env.realized_pnl)
        pnl_pct = (total_pnl / initial_balance) * 100.0
        
        return {
            "totalPnL": pnl_pct,
            "winRate": float(env.win_count / env.trade_count * 100) if env.trade_count > 0 else 0.0,
            "totalTrades": env.trade_count,
            "averagePnL": float(total_pnl / env.trade_count) if env.trade_count > 0 else 0.0,
            "trades": backtest_trades,
            "equityCurve": equity_curve
        }

    async def run_loop(self):
        """
        Background task running the execution loop for paper trading.
        """
        self.is_running = True
        print(f"Trading bot loop started for {self.active_symbol} in {self.mode} mode.")
        
        while self.is_running:
            try:
                # Generate signal
                signal = await self.get_trading_signal(self.active_symbol)
                
                # Execute paper trade if signal is BUY or SELL
                action = signal["type"]
                price = signal["price"]
                
                if action == "BUY" and (not self.position or self.position["type"] == "SHORT"):
                    # Close Short if active
                    if self.position and self.position["type"] == "SHORT":
                        pnl = self.position["size"] * (self.position["entry_price"] - price)
                        self.balance += pnl
                        self.trades.append({
                            "timestamp": int(time.time() * 1000),
                            "pair": self.active_symbol,
                            "type": "BUY_TO_COVER",
                            "price": price,
                            "size": self.position["size"],
                            "pnl": pnl
                        })
                        self.position = None
                    
                    # Open Long
                    size = (self.balance * 0.95) / price
                    self.position = {
                        "type": "LONG",
                        "size": size,
                        "entry_price": price,
                        "stop_loss": price * (1 - settings.stop_loss_distance),
                        "take_profit": price * (1 + settings.take_profit_distance)
                    }
                    self.trades.append({
                        "timestamp": int(time.time() * 1000),
                        "pair": self.active_symbol,
                        "type": "BUY_LONG",
                        "price": price,
                        "size": size,
                        "pnl": 0.0
                    })
                    
                elif action == "SELL" and (not self.position or self.position["type"] == "LONG"):
                    # Close Long if active
                    if self.position and self.position["type"] == "LONG":
                        pnl = self.position["size"] * (price - self.position["entry_price"])
                        self.balance += pnl
                        self.trades.append({
                            "timestamp": int(time.time() * 1000),
                            "pair": self.active_symbol,
                            "type": "SELL_CLOSE",
                            "price": price,
                            "size": self.position["size"],
                            "pnl": pnl
                        })
                        self.position = None
                    
                    # Open Short
                    size = (self.balance * 0.95) / price
                    self.position = {
                        "type": "SHORT",
                        "size": size,
                        "entry_price": price,
                        "stop_loss": price * (1 + settings.stop_loss_distance),
                        "take_profit": price * (1 - settings.take_profit_distance)
                    }
                    self.trades.append({
                        "timestamp": int(time.time() * 1000),
                        "pair": self.active_symbol,
                        "type": "SELL_SHORT",
                        "price": price,
                        "size": size,
                        "pnl": 0.0
                    })

                # Sleep interval - check every 15 seconds
                await asyncio.sleep(15)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in trading bot loop: {e}")
                await asyncio.sleep(5)
                
        self.is_running = False

    def stop(self):
        self.is_running = False
