import { useState, useEffect } from 'react';
import { TradingPair, MarketData } from '../types/trading';
import { apiFetch } from '../lib/api';

const FALLBACK_PAIRS: TradingPair[] = [
  { symbol: 'BTC/USDT', name: 'Bitcoin' },
  { symbol: 'ETH/USDT', name: 'Ethereum' },
  { symbol: 'BNB/USDT', name: 'BNB' },
  { symbol: 'SOL/USDT', name: 'Solana' },
];

export const useMarketData = (_exchange?: any) => {
  const [tradingPairs, setTradingPairs] = useState<TradingPair[]>(FALLBACK_PAIRS);
  const [marketData, setMarketData] = useState<Record<string, MarketData>>({});
  const [loading, setLoading] = useState(false); // never block the UI

  useEffect(() => {
    const fetchTradingPairs = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);
        const response = await apiFetch('/pairs', { signal: controller.signal });
        clearTimeout(timeout);
        if (!response.ok) return;
        const pairs = await response.json();
        if (Array.isArray(pairs) && pairs.length > 0) {
          setTradingPairs(pairs.slice(0, 10));
        }
      } catch {
        // keep fallback pairs, don't block UI
      }
    };
    fetchTradingPairs();
  }, []);

  useEffect(() => {
    if (tradingPairs.length === 0) return;

    const updateMarketData = async () => {
      try {
        const newMarketData: Record<string, MarketData> = {};
        for (const pair of tradingPairs.slice(0, 4)) {
          const response = await apiFetch(`/market-data/${encodeURIComponent(pair.symbol)}`);
          if (response.ok) {
            const data = await response.json();
            newMarketData[pair.symbol] = {
              symbol: data.symbol,
              price: data.price,
              high: data.high,
              low: data.low,
              volume: data.volume,
              priceChange24h: data.priceChange24h ?? 0,
              volume24h: data.volume,
            };
          }
        }
        if (Object.keys(newMarketData).length > 0) {
          setMarketData(newMarketData);
        }
      } catch {
        // silent — market data is non-critical
      }
    };

    updateMarketData();
    const interval = setInterval(updateMarketData, 10000);
    return () => clearInterval(interval);
  }, [tradingPairs]);

  return { tradingPairs, marketData, loading };
};
