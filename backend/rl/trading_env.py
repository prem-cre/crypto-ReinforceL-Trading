import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

class TradingEnvironment:
    def __init__(
        self,
        df: pd.DataFrame,
        initial_balance: float = 10000.0,
        fee_rate: float = 0.001,  # 0.1% transaction fee
        leverage: int = 1,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.04
    ):
        self.df = df.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.fee_rate = fee_rate
        self.leverage = leverage
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        self.current_step = 0
        self.max_steps = len(df) - 1
        
        # Portfolio state
        self.balance = initial_balance
        self.equity = initial_balance
        self.position_size = 0.0  # units of crypto
        self.position_type = None  # 'LONG', 'SHORT', or None
        self.entry_price = 0.0
        self.max_equity = initial_balance
        self.drawdown = 0.0
        
        # Metrics
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        self.realized_pnl = 0.0

    def reset(self) -> np.ndarray:
        self.current_step = 0
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.position_size = 0.0
        self.position_type = None
        self.entry_price = 0.0
        self.max_equity = self.initial_balance
        self.drawdown = 0.0
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        self.realized_pnl = 0.0
        
        return self._get_observation()

    def _get_observation(self) -> np.ndarray:
        """
        Builds a numeric state vector representing:
        - Trend (UP=1, DOWN=-1, SIDEWAYS=0)
        - Volatility (HIGH=1, MEDIUM=0.5, LOW=0)
        - Volume (HIGH=1, MEDIUM=0.5, LOW=0)
        - Momentum (STRONG=1, WEAK=-1, NEUTRAL=0)
        - Regime (BULL=1, BEAR=-1)
        - Position Type (LONG=1, SHORT=-1, NONE=0)
        - Position PnL pct
        - Current balance normalized
        - Drawdown
        - State window indicators relative changes (RSI value scaled, MACD scaled)
        """
        row = self.df.iloc[self.current_step]
        
        # Market states
        # Trend
        trend_val = 0
        if row.get('close', 0) > row.get('ema', 0) * 1.005:
            trend_val = 1
        elif row.get('close', 0) < row.get('ema', 0) * 0.995:
            trend_val = -1
            
        # Volatility
        atr = row.get('atr', 0)
        close = row.get('close', 1)
        norm_atr = atr / close if close > 0 else 0
        vol_val = 0.5
        if norm_atr > 0.02:
            vol_val = 1.0
        elif norm_atr < 0.005:
            vol_val = 0.0

        # Volume
        volume_val = 0.5  # Medium default
        
        # Momentum
        rsi = row.get('rsi', 50)
        mom_val = 0
        if rsi > 65:
            mom_val = 1
        elif rsi < 35:
            mom_val = -1

        # Regime
        regime_val = 1 if close >= row.get('ema', close) else -1
        
        # Position variables
        pos_type_val = 0.0
        pos_pnl_val = 0.0
        if self.position_type == 'LONG':
            pos_type_val = 1.0
            pos_pnl_val = (close - self.entry_price) / self.entry_price if self.entry_price > 0 else 0
        elif self.position_type == 'SHORT':
            pos_type_val = -1.0
            pos_pnl_val = (self.entry_price - close) / self.entry_price if self.entry_price > 0 else 0
            
        # Scaled RSI and MACD
        rsi_scaled = (rsi - 50.0) / 50.0
        macd_hist = row.get('macd_hist', 0)
        macd_hist_scaled = macd_hist / close if close > 0 else 0
        
        state = np.array([
            trend_val,
            vol_val,
            volume_val,
            mom_val,
            regime_val,
            pos_type_val,
            pos_pnl_val,
            self.drawdown,
            rsi_scaled,
            macd_hist_scaled
        ], dtype=np.float32)
        
        return state

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Executes one step in the environment.
        action: 0 = BUY/LONG, 1 = SELL/SHORT, 2 = HOLD
        """
        row = self.df.iloc[self.current_step]
        close_price = float(row['close'])
        high_price = float(row['high'])
        low_price = float(row['low'])
        
        reward = 0.0
        trade_executed = False
        pnl = 0.0
        
        # 1. Update existing position (Check Stop Loss / Take Profit)
        if self.position_type is not None:
            # Check if SL or TP hit
            sl_hit = False
            tp_hit = False
            execution_price = close_price
            
            if self.position_type == 'LONG':
                sl_price = self.entry_price * (1 - self.stop_loss_pct)
                tp_price = self.entry_price * (1 + self.take_profit_pct)
                if low_price <= sl_price:
                    sl_hit = True
                    execution_price = sl_price
                elif high_price >= tp_price:
                    tp_hit = True
                    execution_price = tp_price
            elif self.position_type == 'SHORT':
                sl_price = self.entry_price * (1 + self.stop_loss_pct)
                tp_price = self.entry_price * (1 - self.take_profit_pct)
                if high_price >= sl_price:
                    sl_hit = True
                    execution_price = sl_price
                elif low_price <= tp_price:
                    tp_hit = True
                    execution_price = tp_price
            
            if sl_hit or tp_hit:
                # Liquidate position
                pnl = self._calculate_pnl(execution_price)
                self.balance += pnl
                self.realized_pnl += pnl
                
                # Apply fee
                fee = (self.position_size * execution_price) * self.fee_rate
                self.balance -= fee
                
                # Update metrics
                self.trade_count += 1
                if pnl > 0:
                    self.win_count += 1
                else:
                    self.loss_count += 1
                
                # Reset position
                self.position_size = 0.0
                self.position_type = None
                self.entry_price = 0.0
                
                reward += (pnl / self.equity) * 10.0  # scaled PnL reward
                trade_executed = True

        # 2. Execute new action
        # 0: BUY/LONG, 1: SELL/SHORT, 2: HOLD
        if action == 0 and self.position_type != 'LONG':
            # If SHORT, close first
            if self.position_type == 'SHORT':
                pnl = self._calculate_pnl(close_price)
                self.balance += pnl
                self.realized_pnl += pnl
                fee = (self.position_size * close_price) * self.fee_rate
                self.balance -= fee
                
                self.trade_count += 1
                if pnl > 0:
                    self.win_count += 1
                else:
                    self.loss_count += 1
                    
                reward += (pnl / self.equity) * 10.0
                self.position_size = 0.0
                self.position_type = None
            
            # Open LONG
            # Use 95% of available balance to account for fees
            margin = self.balance * 0.95
            self.entry_price = close_price
            self.position_size = (margin * self.leverage) / close_price
            self.position_type = 'LONG'
            
            # Apply entry fee
            fee = (self.position_size * close_price) * self.fee_rate
            self.balance -= fee
            trade_executed = True
            
        elif action == 1 and self.position_type != 'SHORT':
            # If LONG, close first
            if self.position_type == 'LONG':
                pnl = self._calculate_pnl(close_price)
                self.balance += pnl
                self.realized_pnl += pnl
                fee = (self.position_size * close_price) * self.fee_rate
                self.balance -= fee
                
                self.trade_count += 1
                if pnl > 0:
                    self.win_count += 1
                else:
                    self.loss_count += 1
                    
                reward += (pnl / self.equity) * 10.0
                self.position_size = 0.0
                self.position_type = None
            
            # Open SHORT
            margin = self.balance * 0.95
            self.entry_price = close_price
            self.position_size = (margin * self.leverage) / close_price
            self.position_type = 'SHORT'
            
            # Apply entry fee
            fee = (self.position_size * close_price) * self.fee_rate
            self.balance -= fee
            trade_executed = True

        # 3. Update equity & drawdown
        current_val = self._get_unrealized_value(close_price)
        self.equity = self.balance + current_val
        self.max_equity = max(self.max_equity, self.equity)
        self.drawdown = (self.max_equity - self.equity) / self.max_equity if self.max_equity > 0 else 0
        
        # Provide small daily/step return reward (differential equity)
        # It encourages the agent to hold profitable positions and close bad ones
        prev_equity = self.equity
        self.current_step += 1
        
        # Check termination
        done = False
        if self.current_step >= self.max_steps:
            done = True
        if self.drawdown > 0.5:  # Lost 50% from peak
            done = True
            reward -= 10.0  # Large drawdown penalty
        if self.equity < self.initial_balance * 0.1:  # Account blown
            done = True
            reward -= 20.0
            
        # Observation for next step
        obs = self._get_observation() if not done else np.zeros(10, dtype=np.float32)
        
        # Final Step Info
        info = {
            "balance": self.balance,
            "equity": self.equity,
            "position_type": self.position_type,
            "position_size": self.position_size,
            "drawdown": self.drawdown,
            "trade_count": self.trade_count,
            "win_rate": self.win_count / self.trade_count if self.trade_count > 0 else 1.0,
            "realized_pnl": self.realized_pnl,
            "trade_executed": trade_executed,
            "pnl": pnl
        }
        
        return obs, reward, done, info

    def _calculate_pnl(self, exit_price: float) -> float:
        if self.position_type == 'LONG':
            return self.position_size * (exit_price - self.entry_price)
        elif self.position_type == 'SHORT':
            return self.position_size * (self.entry_price - exit_price)
        return 0.0

    def _get_unrealized_value(self, current_price: float) -> float:
        if self.position_type == 'LONG':
            # Net asset value = units * current_price
            # PnL = units * (current_price - entry_price)
            # The value added to the balance is the PnL
            return self.position_size * (current_price - self.entry_price)
        elif self.position_type == 'SHORT':
            return self.position_size * (self.entry_price - current_price)
        return 0.0
