import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, BarChart2, LineChart, Brain, ArrowRight, Activity, Shield, TrendingUp } from 'lucide-react';

export const Home: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div style={{ minHeight: '100vh', background: '#0d1117', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 24px' }}>

      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 40 }}>
        <div style={{ width: 48, height: 48, borderRadius: 14, background: 'linear-gradient(135deg, #7c3aed, #06b6d4)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Zap size={24} color="#fff" />
        </div>
        <div>
          <p style={{ color: '#fff', fontWeight: 700, fontSize: 20, margin: 0, lineHeight: 1 }}>PPO RL Trading Bot</p>
          <p style={{ color: '#6b7280', fontSize: 13, margin: '4px 0 0' }}>Crypto · Reinforcement Learning · RAG</p>
        </div>
      </div>

      {/* Hero */}
      <div style={{ textAlign: 'center', maxWidth: 560, marginBottom: 48 }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 99, background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.25)', marginBottom: 20 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#a78bfa', display: 'inline-block' }} />
          <span style={{ color: '#a78bfa', fontSize: 12, fontWeight: 500 }}>Powered by PyTorch PPO + Gemini 2.0</span>
        </div>
        <h1 style={{ color: '#f9fafb', fontSize: 36, fontWeight: 800, margin: '0 0 16px', lineHeight: 1.2 }}>
          Autonomous Crypto Trading<br />with Reinforcement Learning
        </h1>
        <p style={{ color: '#6b7280', fontSize: 15, margin: 0, lineHeight: 1.7 }}>
          PPO actor-critic agent with LLM-grounded signal rationale, walk-forward backtesting,
          Kelly-fraction risk management, and full MLOps — 100% free hosting.
        </p>
      </div>

      {/* Feature cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, width: '100%', maxWidth: 720, marginBottom: 40 }}>
        {[
          { icon: BarChart2, title: 'Backtest', desc: 'Sharpe, Sortino, Calmar vs buy-and-hold', tab: 'backtest', color: '#7c3aed' },
          { icon: LineChart, title: 'Live Trade', desc: 'PPO signals with Kelly position sizing', tab: 'live', color: '#06b6d4' },
          { icon: Brain,    title: 'RL Training', desc: 'Watch the agent learn episode by episode', tab: 'learning', color: '#10b981' },
        ].map(({ icon: Icon, title, desc, tab, color }) => (
          <button
            key={tab}
            onClick={() => navigate(`/dashboard?tab=${tab}`)}
            style={{
              background: '#161b27', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 16,
              padding: '24px', textAlign: 'left', cursor: 'pointer', transition: 'border-color 0.2s, transform 0.15s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = `${color}55`; (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.07)'; (e.currentTarget as HTMLElement).style.transform = 'none'; }}
          >
            <div style={{ width: 40, height: 40, borderRadius: 12, background: `${color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
              <Icon size={20} color={color} />
            </div>
            <p style={{ color: '#f9fafb', fontWeight: 600, fontSize: 15, margin: '0 0 6px' }}>{title}</p>
            <p style={{ color: '#6b7280', fontSize: 13, margin: 0 }}>{desc}</p>
          </button>
        ))}
      </div>

      {/* Stats strip */}
      <div style={{ display: 'flex', gap: 32, marginBottom: 40, flexWrap: 'wrap', justifyContent: 'center' }}>
        {[
          { icon: Activity, label: 'Live on HF Spaces', color: '#10b981' },
          { icon: Shield,   label: 'Neon pgvector DB',  color: '#60a5fa' },
          { icon: TrendingUp, label: '$0/month hosting', color: '#a78bfa' },
        ].map(({ icon: Icon, label, color }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Icon size={15} color={color} />
            <span style={{ color: '#9ca3af', fontSize: 13 }}>{label}</span>
          </div>
        ))}
      </div>

      {/* CTA */}
      <button
        onClick={() => navigate('/dashboard')}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          padding: '13px 28px', background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
          color: '#fff', fontSize: 15, fontWeight: 600, borderRadius: 12, border: 'none', cursor: 'pointer',
          boxShadow: '0 4px 24px rgba(124,58,237,0.35)',
        }}
        onMouseEnter={e => (e.currentTarget.style.opacity = '0.9')}
        onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
      >
        Open Dashboard <ArrowRight size={16} />
      </button>
    </div>
  );
};
