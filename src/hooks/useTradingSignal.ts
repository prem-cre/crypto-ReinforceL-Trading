import { useState } from 'react';
import type { TradingSignal } from '../types/trading';

const API_BASE = 'http://localhost:8000/api';

interface TradingSignalOptions {
  exchange?: string;
  leverage?: number;
  capital?: number;
}

export const useTradingSignal = () => {
  const [tradingSignal, setTradingSignal] = useState<TradingSignal | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateTradingSignal = async (pair: string, options?: TradingSignalOptions) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE}/signal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pair,
          leverage: options?.leverage ?? 10,
          capital: options?.capital ?? 100
        })
      });

      if (!response.ok) throw new Error('Failed to generate signal from server');
      const data = await response.json();
      
      setTradingSignal({
        timestamp: data.timestamp,
        pair: data.pair,
        type: data.type,
        price: data.price,
        size: data.size,
        confidence: data.confidence,
        reason: data.reason
      });
    } catch (error) {
      setError('Failed to generate trading signal');
      console.error('Error generating trading signal:', error);
    } finally {
      setLoading(false);
    }
  };

  return {
    tradingSignal,
    loading,
    error,
    generateTradingSignal
  };
};
