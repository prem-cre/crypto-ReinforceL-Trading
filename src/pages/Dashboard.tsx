import React, { useState, useEffect } from "react";
import { Layout, Typography, Tabs, Card, Space, Select as AntSelect, Input as AntInput } from "antd";
import { 
  BarChart3, 
  ArrowDownUp, 
  History, 
  Settings,
  PlayCircle,
  Brain,
  LineChart
} from "lucide-react";
import { TradingSignalCard } from "../components/trading/TradingSignalCard";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Select } from "../components/ui/select";
import { mockTradingSignal, availablePairs } from "../lib/constants/mockData";
import { useTradingSignal } from "../hooks/useTradingSignal";
import { BacktestConfig } from "../components/backtest/BacktestConfig";
import { BacktestResults } from "../components/backtest/BacktestResults";
import { TradingMetrics } from "../components/trading/TradingMetrics";
import { LearningMetrics } from "../components/learning/LearningMetrics";
import { useBacktest } from '../hooks/useBacktest';
import { WS_URL } from '../lib/api';
import { Welcome } from '../components/welcome/Welcome';
import { SignalRationale } from '../components/SignalRationale';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useMarketData } from '../hooks/useMarketData';

const { Header, Content } = Layout;
const { Title } = Typography;

export function Dashboard() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [selectedPair, setSelectedPair] = useState("BTCUSDT");
  const [pairInput, setPairInput] = useState("");
  const [activeTab, setActiveTab] = useState("dashboard");
  const [settings, setSettings] = useState({
    leverage: 10,
    capital: 100,
    exchange: "binance",
    riskRewardRatio: "2",
  });

  const { marketData, loading: marketLoading } = useMarketData();
  const {
    tradingSignal,
    loading,
    error,
    generateTradingSignal
  } = useTradingSignal();

  const { startBacktest, isRunning, results } = useBacktest();

  // State fields driven by the backend WebSocket connection
  const [tradingMetrics, setTradingMetrics] = useState({
    balance: 10000,
    pnl: 0.0,
    winRate: 100,
    totalTrades: 0,
    openPositions: 0,
    recentSignals: [] as any[]
  });

  const [learningMetrics, setLearningMetrics] = useState({
    episodeRewards: [] as number[],
    explorationRate: 0,
    learningRate: 0.001,
    totalEpisodes: 0,
    currentEpisode: 0,
    averageReward: 0,
    bestReward: 0,
  });

  // Connect WebSocket to FastAPI backend
  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "initial" || data.type === "update") {
          const status = data.status || {};
          const rl = status.rlStatus || {};
          
          setTradingMetrics({
            balance: status.balance || (Number(marketData?.price) || 10000),
            pnl: data.performance?.forwardTest?.totalPnL || 0.0,
            winRate: data.performance?.forwardTest?.winRate || 100,
            totalTrades: data.performance?.forwardTest?.totalTrades || 0,
            openPositions: status.position ? 1 : 0,
            recentSignals: data.signals || []
          });

          setLearningMetrics({
            episodeRewards: rl.episodeRewards || [],
            explorationRate: rl.explorationRate || 0,
            learningRate: rl.learningRate || 0.001,
            totalEpisodes: rl.totalEpisodes || 0,
            currentEpisode: rl.totalEpisodes || 0,
            averageReward: rl.averageReward || 0.0,
            bestReward: rl.bestReward || 0.0
          });
        }
      } catch (err) {
        console.error("Error parsing websocket message:", err);
      }
    };

    ws.onerror = (err) => {
      console.error("Dashboard WebSocket error:", err);
    };

    return () => {
      ws.close();
    };
  }, [marketData]);

  useEffect(() => {
    const tab = searchParams.get('tab');
    if (tab) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  const handleTabChange = (key: string) => {
    setActiveTab(key);
    navigate(`/dashboard?tab=${key}`, { replace: true });
  };

  const handlePairSearch = () => {
    if (pairInput.trim() !== "") {
      const formattedPair = pairInput.toUpperCase();
      setSelectedPair(formattedPair);
      generateTradingSignal(formattedPair, settings);
      setPairInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handlePairSearch();
    }
  };

  const handlePairSelect = (value: string) => {
    setSelectedPair(value);
    generateTradingSignal(value, settings);
  };

  const handleSaveSettings = () => {
    generateTradingSignal(selectedPair, settings);
  };

  const handleBacktest = async (config: any) => {
    await startBacktest(config);
  };

  useEffect(() => {
    generateTradingSignal(selectedPair, settings);
  }, []);

  const renderDashboardContent = () => (
    <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
      <div className="md:col-span-12">
        <Card title="Overview">
          <Space direction="vertical" style={{ width: '100%' }}>
            <div className="flex justify-between items-center">
              <div>
                <Title level={4}>Current Balance: ${tradingMetrics.balance.toLocaleString()}</Title>
                <p>24h PnL: {tradingMetrics.pnl >= 0 ? '+' : ''}{tradingMetrics.pnl}%</p>
              </div>
              <div>
                <Title level={4}>Open Positions: {tradingMetrics.openPositions}</Title>
                <p>Win Rate: {tradingMetrics.winRate}%</p>
              </div>
            </div>
          </Space>
        </Card>
      </div>
    </div>
  );

  const renderSignalsContent = () => (
    <div className="space-y-6">
      <Card title="Live Trading Signal">
        <Space direction="vertical" style={{ width: '100%' }}>
          <div className="flex gap-2 items-center">
            <AntInput.Search
              placeholder="Enter trading pair..."
              value={pairInput}
              onChange={(e) => setPairInput(e.target.value)}
              onSearch={handlePairSearch}
              style={{ width: 200 }}
              enterButton
            />
            <AntSelect
              value={selectedPair}
              onChange={handlePairSelect}
              disabled={loading}
              options={availablePairs.map(pair => ({ label: pair, value: pair }))}
              style={{ width: 150 }}
            />
          </div>
          {error && (
            <div className="text-red-500">{error}</div>
          )}
          {loading ? (
            <div className="text-center p-8">Loading...</div>
          ) : tradingSignal ? (
            <>
              <TradingSignalCard signal={tradingSignal} />
              <SignalRationale
                rationale={tradingSignal.rationale}
                citations={tradingSignal.citations}
                sentiment_score={tradingSignal.sentiment_score}
              />
            </>
          ) : (
            <TradingSignalCard signal={{ ...mockTradingSignal, pair: selectedPair }} />
          )}
        </Space>
      </Card>
    </div>
  );

  const renderSettingsContent = () => (
    <Card title="Settings">
      <Space direction="vertical" style={{ width: '100%' }}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label>Default Leverage</label>
            <Input
              type="number"
              value={settings.leverage}
              onChange={(e) => setSettings({...settings, leverage: Number(e.target.value)})}
            />
          </div>
          <div>
            <label>Default Capital</label>
            <Input
              type="number"
              value={settings.capital}
              onChange={(e) => setSettings({...settings, capital: Number(e.target.value)})}
            />
          </div>
        </div>
        <Button onClick={handleSaveSettings}>Save Settings</Button>
      </Space>
    </Card>
  );

  if (marketLoading) {
    return (
      <div className="text-center p-8">Loading market data...</div>
    );
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#1f1f1f', padding: '0 24px' }}>
        <div className="flex justify-between items-center h-full">
          <Title level={3} style={{ color: '#fff', margin: 0 }}>
            PPO RL Crypto Trading Assistant
          </Title>
          <div className="flex items-center gap-4">
            <AntInput.Search
              placeholder="Enter trading pair..."
              value={pairInput}
              onChange={(e) => setPairInput(e.target.value)}
              onSearch={handlePairSearch}
              style={{ width: 200 }}
              enterButton
            />
            <AntSelect
              value={selectedPair}
              onChange={handlePairSelect}
              disabled={loading}
              options={availablePairs.map(pair => ({ label: pair, value: pair }))}
              style={{ width: 150 }}
            />
          </div>
        </div>
      </Header>
      <Content style={{ padding: '24px' }}>
        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          items={[
            {
              key: "dashboard",
              label: (
                <span className="flex items-center gap-2">
                  <BarChart3 size={16} />
                  Dashboard
                </span>
              ),
              children: <Welcome />,
            },
            {
              key: "signals",
              label: (
                <span className="flex items-center gap-2">
                  <ArrowDownUp size={16} />
                  Signals
                </span>
              ),
              children: renderSignalsContent(),
            },
            {
              key: "history",
              label: (
                <span className="flex items-center gap-2">
                  <History size={16} />
                  History
                </span>
              ),
              children: <Card title="Trading History">Trading history content</Card>,
            },
            {
              key: "backtest",
              label: (
                <span className="flex items-center gap-2">
                  <PlayCircle size={16} />
                  Backtest
                </span>
              ),
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <BacktestConfig onStartBacktest={handleBacktest} isLoading={isRunning} />
                  {results && <BacktestResults results={{
                    totalPnL: results.totalPnl || 0,
                    averagePnL: results.averagePnl || 0,
                    winRate: results.winRate || 0,
                    totalTrades: results.totalTrades || 0,
                    tradeHistory: results.trades || []
                  }} />}
                </Space>
              ),
            },
            {
              key: "live",
              label: (
                <span className="flex items-center gap-2">
                  <LineChart size={16} />
                  Live Trade
                </span>
              ),
              children: (
                <TradingMetrics
                  balance={tradingMetrics.balance}
                  pnl={tradingMetrics.pnl}
                  winRate={tradingMetrics.winRate}
                  totalTrades={tradingMetrics.totalTrades}
                  openPositions={tradingMetrics.openPositions}
                  recentSignals={tradingMetrics.recentSignals}
                />
              ),
            },
            {
              key: "learning",
              label: (
                <span className="flex items-center gap-2">
                  <Brain size={16} />
                  Learning
                </span>
              ),
              children: <LearningMetrics {...learningMetrics} />,
            },
            {
              key: "settings",
              label: (
                <span className="flex items-center gap-2">
                  <Settings size={16} />
                  Settings
                </span>
              ),
              children: renderSettingsContent(),
            },
          ]}
        />
      </Content>
    </Layout>
  );
}; 