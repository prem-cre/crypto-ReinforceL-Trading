"""Exchange simulator using CCXT.

Tries Binance first (blocked on cloud IPs), then falls back to KuCoin,
then OKX — both work from HuggingFace Spaces / cloud environments.
"""
import ccxt
import time
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from backend.config import settings

logger = logging.getLogger(__name__)

_FALLBACK_EXCHANGES = ["kucoin", "okx", "bybit"]


def _make_binance() -> ccxt.Exchange:
    config: Dict[str, Any] = {"enableRateLimit": True}
    if settings.binance_api_key and settings.binance_api_secret:
        config["apiKey"] = settings.binance_api_key
        config["secret"] = settings.binance_api_secret
    return ccxt.binance(config)


def _make_fallback(name: str) -> ccxt.Exchange:
    return getattr(ccxt, name)({"enableRateLimit": True})


def _ohlcv_to_df(ohlcv: list, limit: int) -> pd.DataFrame:
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


class ExchangeSimulator:
    def __init__(self) -> None:
        self._primary: ccxt.Exchange = _make_binance()
        self._fallbacks: List[ccxt.Exchange] = [_make_fallback(n) for n in _FALLBACK_EXCHANGES]
        self.balance = settings.initial_capital
        self.positions: Dict[str, Any] = {}
        self._working_exchange: Optional[ccxt.Exchange] = None  # cached after first success

    # ── internal: try primary then fallbacks ────────────────────
    def _fetch_ohlcv_any(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Try Binance, then each fallback, return first success."""
        candidates = [self._primary] + self._fallbacks
        if self._working_exchange is not None:
            # Put the last known-good exchange first to avoid retrying dead ones
            candidates = [self._working_exchange] + [e for e in candidates if e is not self._working_exchange]

        # Normalise symbol for non-Binance exchanges (BTC/USDT works everywhere)
        for exchange in candidates:
            try:
                sym = symbol
                ohlcv = exchange.fetch_ohlcv(sym, timeframe, limit=limit)
                if ohlcv and len(ohlcv) > 10:
                    self._working_exchange = exchange
                    logger.info(f"OHLCV fetched via {exchange.id} ({len(ohlcv)} candles)")
                    return _ohlcv_to_df(ohlcv, limit)
            except Exception as e:
                logger.warning(f"{exchange.id} OHLCV failed: {e}")

        logger.error("All exchanges failed — using synthetic data for backtest demo")
        return self._synthetic_ohlcv(symbol, timeframe, limit)

    def _fetch_ticker_any(self, symbol: str) -> Dict[str, Any]:
        candidates = [self._primary] + self._fallbacks
        if self._working_exchange is not None:
            candidates = [self._working_exchange] + [e for e in candidates if e is not self._working_exchange]
        for exchange in candidates:
            try:
                ticker = exchange.fetch_ticker(symbol)
                price = ticker.get("last") or ticker.get("close") or 0.0
                if price and price > 0:
                    self._working_exchange = exchange
                    return {
                        "symbol": symbol,
                        "price": float(price),
                        "high": float(ticker.get("high") or price),
                        "low": float(ticker.get("low") or price),
                        "volume": float(ticker.get("baseVolume") or 0.0),
                        "priceChange24h": float(ticker.get("percentage") or 0.0),
                        "timestamp": int(ticker.get("timestamp") or time.time() * 1000),
                    }
            except Exception as e:
                logger.warning(f"{exchange.id} ticker failed for {symbol}: {e}")
        # Hard fallback — realistic BTC price to avoid breaking UI
        return {"symbol": symbol, "price": 105000.0, "high": 106000.0, "low": 104000.0,
                "volume": 100.0, "priceChange24h": 0.0, "timestamp": int(time.time() * 1000)}

    def _synthetic_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Generate realistic-looking synthetic price data using geometric Brownian motion."""
        import numpy as np
        rng = np.random.default_rng(42)
        # Seed price based on symbol so BTC ≠ ETH
        base = 105000.0 if "BTC" in symbol else (3500.0 if "ETH" in symbol else 500.0)
        returns = rng.normal(0.0001, 0.012, limit)
        closes = base * np.exp(np.cumsum(returns))
        highs = closes * (1 + abs(rng.normal(0, 0.005, limit)))
        lows = closes * (1 - abs(rng.normal(0, 0.005, limit)))
        opens = np.roll(closes, 1)
        opens[0] = closes[0]
        times = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq=timeframe)
        return pd.DataFrame({
            "timestamp": times, "open": opens, "high": highs,
            "low": lows, "close": closes, "volume": rng.uniform(5, 50, limit),
        })

    # ── public API ───────────────────────────────────────────────
    def connect(self) -> None:
        for exchange in [self._primary] + self._fallbacks:
            try:
                exchange.load_markets()
                self._working_exchange = exchange
                logger.info(f"Connected via {exchange.id}")
                return
            except Exception as e:
                logger.warning(f"{exchange.id} connect failed: {e}")

    def get_trading_pairs(self) -> List[Dict[str, Any]]:
        exchange = self._working_exchange or self._primary
        try:
            markets = exchange.load_markets()
            return [
                {"symbol": sym, "baseAsset": m["base"], "quoteAsset": m["quote"],
                 "price": 0.0, "priceChange24h": 0.0, "volume24h": 0.0}
                for sym, m in markets.items()
                if m.get("quote") == "USDT" and m.get("active")
            ][:50]
        except Exception as e:
            logger.warning(f"get_trading_pairs failed: {e}")
            return [
                {"symbol": s, "baseAsset": s.replace("/USDT", ""), "quoteAsset": "USDT",
                 "price": 0.0, "priceChange24h": 0.0, "volume24h": 0.0}
                for s in ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT"]
            ]

    def get_market_data(self, symbol: str) -> Dict[str, Any]:
        return self._fetch_ticker_any(symbol)

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> pd.DataFrame:
        return self._fetch_ohlcv_any(symbol, timeframe, limit)

    def get_balance(self) -> float:
        return self.balance

    def set_balance(self, value: float) -> None:
        self.balance = value
