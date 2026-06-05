import pandas as pd
import numpy as np
import ta
from typing import Dict, Any

class MarketAnalyzer:
    def __init__(self):
        pass

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators on the given DataFrame.
        Expected columns in df: 'open', 'high', 'low', 'close', 'volume'
        """
        df = df.copy()
        if len(df) < 20:
            # Not enough data, fill with defaults
            df['ema'] = df['close']
            df['rsi'] = 50.0
            df['macd'] = 0.0
            df['macd_signal'] = 0.0
            df['macd_hist'] = 0.0
            df['atr'] = 0.0
            df['bb_high'] = df['close']
            df['bb_low'] = df['close']
            df['bb_mid'] = df['close']
            return df

        # EMA
        df['ema'] = ta.trend.ema_indicator(df['close'], window=20)
        
        # MACD
        macd_indicator = ta.trend.MACD(df['close'])
        df['macd'] = macd_indicator.macd()
        df['macd_signal'] = macd_indicator.macd_signal()
        df['macd_hist'] = macd_indicator.macd_diff()

        # RSI
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)

        # ATR (Average True Range)
        df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df['close'], window=20)
        df['bb_high'] = bb.bollinger_hband()
        df['bb_low'] = bb.bollinger_lband()
        df['bb_mid'] = bb.bollinger_mavg()

        # Fill NaNs
        df = df.ffill().bfill()
        return df

    def get_market_state(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Determine current market state (Trend, Volatility, Volume, Momentum, Regime)
        from the last candle of the calculated DataFrame.
        """
        if df.empty:
            return {
                "trend": "SIDEWAYS",
                "volatility": "MEDIUM",
                "volume": "MEDIUM",
                "momentum": "NEUTRAL",
                "regime": "BULL",
                "numeric_volatility": 0.0
            }

        df_with_indicators = self.calculate_indicators(df)
        last_row = df_with_indicators.iloc[-1]
        prev_row = df_with_indicators.iloc[-2] if len(df_with_indicators) > 1 else last_row

        close = float(last_row['close'])
        ema = float(last_row['ema'])
        rsi = float(last_row['rsi'])
        macd_hist = float(last_row['macd_hist'])
        atr = float(last_row['atr'])
        volume = float(last_row['volume'])

        # 1. Trend Classification
        if close > ema * 1.005:
            trend = "UP"
        elif close < ema * 0.995:
            trend = "DOWN"
        else:
            trend = "SIDEWAYS"

        # 2. Volatility Classification
        # We can look at normalized ATR (ATR / close)
        norm_atr = atr / close if close > 0 else 0
        if norm_atr > 0.02:
            volatility = "HIGH"
        elif norm_atr < 0.005:
            volatility = "LOW"
        else:
            volatility = "MEDIUM"

        # 3. Volume Classification
        # Compare current volume with a simple average of volume
        vol_avg = df_with_indicators['volume'].rolling(window=20).mean().iloc[-1]
        if pd.isna(vol_avg) or vol_avg == 0:
            volume_state = "MEDIUM"
        elif volume > vol_avg * 1.5:
            volume_state = "HIGH"
        elif volume < vol_avg * 0.5:
            volume_state = "LOW"
        else:
            volume_state = "MEDIUM"

        # 4. Momentum Classification
        if rsi > 65 or macd_hist > 0:
            momentum = "STRONG"
        elif rsi < 35 or macd_hist < 0:
            momentum = "WEAK"
        else:
            momentum = "NEUTRAL"

        # 5. Regime Classification
        # Standard: bull regime if price above 50 EMA, bear if below
        regime = "BULL" if close >= ema else "BEAR"

        return {
            "trend": trend,
            "volatility": volatility,
            "volume": volume_state,
            "momentum": momentum,
            "regime": regime,
            "numeric_volatility": norm_atr
        }
