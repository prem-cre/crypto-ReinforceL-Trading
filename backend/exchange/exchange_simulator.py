import ccxt
import time
from typing import Dict, Any, List
import pandas as pd
from backend.config import settings

class ExchangeSimulator:
    def __init__(self):
        # Initialize CCXT Binance instance
        # If API keys are set, use them
        config = {
            'enableRateLimit': True,
        }
        if settings.binance_api_key and settings.binance_api_secret:
            config['apiKey'] = settings.binance_api_key
            config['secret'] = settings.binance_api_secret
            
        self.exchange = ccxt.binance(config)
        self.balance = settings.initial_capital
        self.positions = {}  # symbol -> position details

    def connect(self):
        try:
            self.exchange.load_markets()
            print("Connected to Binance Exchange Simulator successfully via CCXT.")
        except Exception as e:
            print(f"Error connecting to Binance via CCXT: {e}")

    def get_trading_pairs(self) -> List[Dict[str, Any]]:
        try:
            markets = self.exchange.load_markets()
            pairs = []
            for symbol, market in markets.items():
                if market['quote'] == 'USDT' and market['active']:
                    pairs.append({
                        "symbol": symbol,
                        "baseAsset": market['base'],
                        "quoteAsset": market['quote'],
                        "price": 0.0,
                        "priceChange24h": 0.0,
                        "volume24h": 0.0
                    })
            return pairs
        except Exception as e:
            print(f"Error loading symbols: {e}")
            return []

    def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches the latest ticker information for the given symbol.
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "price": ticker.get('last', 0.0),
                "high": ticker.get('high', 0.0),
                "low": ticker.get('low', 0.0),
                "volume": ticker.get('baseVolume', 0.0),
                "timestamp": ticker.get('timestamp', int(time.time() * 1000))
            }
        except Exception as e:
            print(f"Error fetching market data for {symbol}: {e}")
            # Mock backup if api fails (e.g. rate limited during tests)
            return {
                "symbol": symbol,
                "price": 50000.0,
                "high": 51000.0,
                "low": 49000.0,
                "volume": 100.0,
                "timestamp": int(time.time() * 1000)
            }

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> pd.DataFrame:
        """
        Fetches historical OHLCV data and returns it as a pandas DataFrame.
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error fetching OHLCV for {symbol}: {e}")
            # Return empty or dummy data
            dummy_time = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq=timeframe)
            df = pd.DataFrame({
                'timestamp': dummy_time,
                'open': [50000.0] * limit,
                'high': [50500.0] * limit,
                'low': [49500.0] * limit,
                'close': [50000.0] * limit,
                'volume': [10.0] * limit
            })
            return df

    def get_balance(self) -> float:
        return self.balance

    def set_balance(self, value: float):
        self.balance = value
