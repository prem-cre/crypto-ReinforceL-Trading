export interface TradingPair {
  symbol: string;
  baseAsset?: string;
  quoteAsset?: string;
  price?: number;
  priceChange24h?: number;
  volume24h?: number;
}

export interface MarketData {
  symbol: string;
  price: number;
  timestamp?: number;
  volume: number;
  high: number;
  low: number;
  priceChange24h?: number;
  volume24h?: number;
}

export interface SignalCitation {
  url: string;
  title?: string;
  source?: string;
}

// Live signal from the RL backend. (The old mock-data shape with entry/stopLoss
// is kept for components that still consume mock data.)
export interface TradingSignal {
  timestamp: number;
  pair: string;
  type: 'BUY' | 'SELL' | 'HOLD' | 'LONG' | 'SHORT';
  price?: number;
  size?: number;
  confidence?: number;
  reason?: string;

  // Phase 2 LLM/RAG fields (optional)
  rationale?: string;
  citations?: SignalCitation[];
  sentiment_score?: number;

  // Legacy mock-data fields (optional for backwards compat)
  entry?: number;
  stopLoss?: number;
  takeProfit?: number;
  exchange?: string;
  leverage?: number;
  capital?: number;
  technicalAnalysis?: {
    emaStatus: string;
    candlestickPattern: string;
    macd: string;
    volumeInsight: string;
    rsi: string;
    supportResistance: string;
  };
}

export interface Trade {
  id: string;
  timestamp: number;
  pair: string;
  type: 'LONG' | 'SHORT' | 'BUY' | 'SELL' | string;
  price: number;
  size: number;
  pnl?: number;
  status?: 'OPEN' | 'CLOSED';
}

export interface BacktestResult {
  totalPnl: number;
  winRate: number;
  totalTrades: number;
  averagePnl: number;
  trades: Trade[];
  equityCurve: { timestamp: number; equity: number }[];

  // Phase 3 metrics (optional until Phase 3 ships)
  sharpe?: number;
  sortino?: number;
  calmar?: number;
  maxDrawdownPct?: number;
  benchmarkPnlPct?: number;
  alpha?: number;
}
