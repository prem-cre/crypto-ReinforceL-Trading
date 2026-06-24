import React from 'react';
import { Table } from 'antd';
import { TrendingUp, TrendingDown, BarChart3, Target, Activity, Shield } from 'lucide-react';
import { Trade } from '../../types/trading';

interface BacktestResult {
  totalPnL: number;
  averagePnL: number;
  winRate: number;
  totalTrades: number;
  tradeHistory: Trade[];
  sharpe?: number;
  sortino?: number;
  maxDrawdownPct?: number;
  benchmarkPnlPct?: number;
  alpha?: number;
}

export const BacktestResults: React.FC<{ results: BacktestResult }> = ({ results }) => {
  const {
    totalPnL, winRate, totalTrades, sharpe = 0, sortino = 0,
    maxDrawdownPct = 0, benchmarkPnlPct = 0, alpha = 0, tradeHistory,
  } = results;

  const metrics = [
    { label: "Total PnL", value: `${totalPnL >= 0 ? "+" : ""}${totalPnL.toFixed(2)}%`, icon: totalPnL >= 0 ? TrendingUp : TrendingDown, color: totalPnL >= 0 ? "#10b981" : "#ef4444" },
    { label: "Win Rate", value: `${winRate.toFixed(1)}%`, icon: Target, color: "#a78bfa" },
    { label: "Total Trades", value: String(totalTrades), icon: Activity, color: "#60a5fa" },
    { label: "Sharpe Ratio", value: sharpe.toFixed(2), icon: BarChart3, color: "#f59e0b" },
    { label: "Sortino Ratio", value: sortino.toFixed(2), icon: TrendingUp, color: "#06b6d4" },
    { label: "Max Drawdown", value: `${maxDrawdownPct.toFixed(1)}%`, icon: Shield, color: "#f87171" },
    { label: "Benchmark PnL", value: `${benchmarkPnlPct >= 0 ? "+" : ""}${benchmarkPnlPct.toFixed(2)}%`, icon: BarChart3, color: "#9ca3af" },
    { label: "Alpha vs B&H", value: `${alpha >= 0 ? "+" : ""}${alpha.toFixed(2)}%`, icon: TrendingUp, color: alpha >= 0 ? "#10b981" : "#ef4444" },
  ];

  const columns = [
    { title: 'Pair', dataIndex: 'pair', key: 'pair', render: (v: string) => <span className="font-mono text-xs">{v}</span> },
    { title: 'Side', dataIndex: 'type', key: 'type', render: (v: string) => (
      <span className={v === "BUY" ? "badge-buy" : "badge-sell"}>{v}</span>
    )},
    { title: 'Price', dataIndex: 'price', key: 'price', render: (v: number) => `$${v?.toLocaleString() ?? "-"}` },
    { title: 'Size',  dataIndex: 'size',  key: 'size',  render: (v: number) => v?.toFixed(4) ?? "-" },
    { title: 'PnL',   dataIndex: 'pnl',   key: 'pnl',   render: (v: number) => (
      <span style={{ color: v >= 0 ? "#10b981" : "#ef4444", fontWeight: 600 }}>
        {v >= 0 ? "+" : ""}{v?.toFixed(2) ?? "0.00"}%
      </span>
    )},
  ];

  return (
    <div className="space-y-5">
      <div className="metrics-grid">
        {metrics.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="stat-card">
            <div className="flex items-center justify-between mb-2">
              <span className="stat-label">{label}</span>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${color}18` }}>
                <Icon size={13} style={{ color }} />
              </div>
            </div>
            <p className="font-bold" style={{ fontSize: 18, color }}>{value}</p>
          </div>
        ))}
      </div>

      {tradeHistory.length > 0 && (
        <div className="dash-card">
          <h3 className="text-white font-semibold mb-4">Trade History</h3>
          <Table
            dataSource={tradeHistory}
            columns={columns}
            rowKey={(_, i) => String(i)}
            pagination={{ pageSize: 10, size: "small" }}
            size="small"
          />
        </div>
      )}
    </div>
  );
};
