import React from 'react';
import { TrendingUp, TrendingDown, DollarSign, Percent, Activity, Layers } from 'lucide-react';
import { Table } from 'antd';
import { TradingSignal } from '../../types/trading';

interface TradingMetricsProps {
  balance: number;
  pnl: number;
  winRate: number;
  totalTrades: number;
  openPositions: number;
  recentSignals: TradingSignal[];
}

export const TradingMetrics: React.FC<TradingMetricsProps> = ({
  balance, pnl, winRate, totalTrades, openPositions, recentSignals,
}) => {
  const stats = [
    { label: "Portfolio Balance", value: `$${balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, icon: DollarSign, sub: "Paper trading account", color: "#60a5fa" },
    { label: "Total PnL", value: `${pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}%`, icon: pnl >= 0 ? TrendingUp : TrendingDown, sub: pnl >= 0 ? "Profit" : "Loss", color: pnl >= 0 ? "#10b981" : "#ef4444" },
    { label: "Win Rate", value: `${winRate.toFixed(1)}%`, icon: Percent, sub: `${totalTrades} trades total`, color: "#a78bfa" },
    { label: "Open Positions", value: String(openPositions), icon: Layers, sub: "Active right now", color: "#f59e0b" },
  ];

  const columns = [
    { title: 'Time',  dataIndex: 'timestamp', key: 'timestamp', render: (t: number) => new Date(t).toLocaleTimeString() },
    { title: 'Pair',  dataIndex: 'pair', key: 'pair', render: (v: string) => <span className="font-mono text-xs">{v}</span> },
    { title: 'Side',  dataIndex: 'type', key: 'type', render: (v: string) => (
      <span className={v === "BUY" ? "badge-buy" : v === "SELL" ? "badge-sell" : "badge-hold"}>{v}</span>
    )},
    { title: 'Price', dataIndex: 'price', key: 'price', render: (v: number) => `$${v?.toLocaleString() ?? "-"}` },
    { title: 'Size',  dataIndex: 'size',  key: 'size',  render: (v: number) => v?.toFixed(4) ?? "-" },
  ];

  return (
    <div className="space-y-5">
      <div className="metrics-grid">
        {stats.map(({ label, value, icon: Icon, sub, color }) => (
          <div key={label} className="stat-card">
            <div className="flex items-center justify-between mb-3">
              <span className="stat-label">{label}</span>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${color}18` }}>
                <Icon size={15} style={{ color }} />
              </div>
            </div>
            <p className="stat-value" style={{ fontSize: 20, color }}>{value}</p>
            <p className="stat-sub">{sub}</p>
          </div>
        ))}
      </div>

      <div className="dash-card">
        <h3 className="text-white font-semibold mb-4">Recent Signals</h3>
        {recentSignals.length === 0 ? (
          <div className="flex items-center gap-2 text-slate-500 text-sm py-8 justify-center">
            <Activity size={16} /> No signals yet — bot is warming up
          </div>
        ) : (
          <Table
            dataSource={recentSignals}
            columns={columns}
            pagination={{ pageSize: 5, size: "small" }}
            rowKey={(r: any) => `${r.timestamp}-${r.pair}-${r.type}`}
            size="small"
          />
        )}
      </div>
    </div>
  );
};
