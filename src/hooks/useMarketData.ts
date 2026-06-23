import { useState, useEffect } from 'react';
import { TradingPair, MarketData } from '../types/trading';
import { apiFetch } from '../lib/api';

export const useMarketData = (_exchange?: any) => {
  const [tradingPairs, setTradingPairs] = useState<TradingPair[]>([]);
  const [marketData, setMarketData] = useState<Record<string, MarketData>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTradingPairs = async () => {
      try {
        const response = await apiFetch('/pairs');
        if (!response.ok) throw new Error('Failed to fetch trading pairs');
        const pairs = await response.json();
        setTradingPairs(pairs.slice(0, 10));
      } catch (error) {
        console.error('Error fetching trading pairs:', error);
      }
    };

    fetchTradingPairs();
  }, []);

  useEffect(() => {
    if (tradingPairs.length === 0) return;

    const updateMarketData = async () => {
      try {
        const newMarketData: Record<string, MarketData> = {};

        for (const pair of tradingPairs) {
          const response = await apiFetch(`/market-data/${encodeURIComponent(pair.symbol)}`);
          if (response.ok) {
            const data = await response.json();
            newMarketData[pair.symbol] = {
              symbol: data.symbol,
              price: data.price,
              high: data.high,
              low: data.low,
              volume: data.volume,
              priceChange24h: 0,
              volume24h: data.volume,
            };
          }
        }

        setMarketData(newMarketData);
        setLoading(false);
      } catch (error) {
        console.error('Error updating market data:', error);
      }
    };

    updateMarketData();
    const interval = setInterval(updateMarketData, 5000);

    return () => clearInterval(interval);
  }, [tradingPairs]);

  return { tradingPairs, marketData, loading };
};
