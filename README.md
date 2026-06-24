# Crypto RL Trading Bot

> **Live Demo:** https://hhh444-trading-bot.hf.space  
> **Frontend:** Deploy to Vercel — see [Quick Start](#quick-start-local) below

A production-grade reinforcement learning trading system combining a PPO actor-critic agent with LLM-grounded signal analysis, real-time news RAG, and full MLOps instrumentation. Built entirely on free-tier infrastructure.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend  —  Vercel  (React + Vite + Ant Design)               │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTPS / WSS
┌──────────────────────▼──────────────────────────────────────────┐
│  Backend  —  HuggingFace Spaces (Docker / FastAPI)              │
│  • JWT Auth  • REST API  • WebSocket (real-time)                │
│  • PPO RL Agent (PyTorch)   • RAG Signal Explainer              │
│  • Walk-Forward Backtest    • Risk Manager (Kelly + VaR)        │
│  • Drift Monitor (KS test)  • Prometheus /metrics               │
└──┬──────────────┬──────────────┬────────────────┬───────────────┘
   │              │              │                │
┌──▼──────┐ ┌────▼──────┐ ┌────▼───────┐ ┌──────▼──────┐
│ Neon    │ │ Gemini    │ │ HF Hub     │ │ W&B         │
│ Postgres│ │ Flash 2.0 │ │ Model      │ │ Experiment  │
│+pgvector│ │ Embed-004 │ │ Registry   │ │ Tracking    │
└─────────┘ └───────────┘ └────────────┘ └─────────────┘
       ▲
┌──────┴──────────────────────────────────────────────────────────┐
│  GitHub Actions                                                  │
│  • PR: ruff + mypy + pytest                                     │
│  • main: Docker build → HF Space deploy                         │
│  • hourly: news ingestion → embed → pgvector                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Performance Metrics (Backtested)

| Metric | Value |
|---|---|
| Strategy | PPO Actor-Critic (PyTorch) |
| Pairs | BTC/USDT, ETH/USDT |
| Backtest period | 500 1h candles |
| **Sharpe Ratio** | Computed per run via `/api/backtest` |
| **Sortino Ratio** | Computed per run |
| **Calmar Ratio** | Computed per run |
| **Max Drawdown** | Computed per run |
| **vs Buy-and-Hold** | Alpha tracked per run |
| Walk-forward splits | 4-fold out-of-sample |

---

## Key Features

### 1. PPO Reinforcement Learning Agent
- Actor-Critic policy network trained on live OHLCV data
- State: 10 features (trend, RSI, MACD, momentum, regime, position state)
- Actions: BUY / SELL / HOLD with probability-based confidence
- Safetensors model format with HuggingFace Hub versioning

### 2. LLM-Grounded Signal Rationale (RAG)
- Hourly news ingestion from CryptoPanic + Reddit r/Bitcoin
- Google text-embedding-004 (768-dim) → pgvector cosine search
- Gemini 2.0 Flash generates sentiment score + rationale + citations
- 10-minute Postgres-backed cache to stay within free-tier RPM limits

### 3. Walk-Forward Backtesting
- 4-fold out-of-sample validation
- Sharpe, Sortino, Calmar, max drawdown, profit factor, alpha vs benchmark
- Equity curve visualization

### 4. MLOps Stack
- **W&B**: every training run logs hyperparams + eval metrics
- **HF Hub**: versioned models with `production` tag
- **GitHub Actions**: CI (ruff + mypy + pytest) + CD (auto-deploy to HF Space)
- **Drift detection**: KS test on 10 features, `/api/monitoring/drift` endpoint
- **Risk manager**: Kelly-fraction position sizing + 15% drawdown circuit breaker + portfolio VaR (95%)

### 5. Production Backend
- FastAPI with async SQLAlchemy 2.x + Neon Postgres + pgvector
- JWT access + refresh tokens (bcrypt password hashing)
- WebSocket for real-time dashboard updates
- Prometheus `/metrics` endpoint

---

## Free-Tier Stack

| Layer | Service | Cost |
|---|---|---|
| Frontend | Vercel | Free |
| Backend | HuggingFace Spaces (Docker) | Free |
| Database | Neon Postgres + pgvector | Free |
| LLM | Google Gemini 2.0 Flash | Free |
| Embeddings | Google text-embedding-004 | Free |
| Model registry | HuggingFace Hub | Free |
| Experiment tracking | Weights & Biases | Free |
| CI/CD | GitHub Actions | Free |

**Total hosting cost: $0/month**

---

## Quick Start (Local)

```bash
git clone https://github.com/hhh444/crypto-rl-trading-bot
cd crypto-rl-trading-bot
cp .env.example .env   # fill in DATABASE_URL, GEMINI_API_KEY, JWT_SECRET
docker compose up      # backend at :8000
cd frontend && npm install && npm run dev   # frontend at :5173
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/healthz` | GET | Health check |
| `/api/auth/register` | POST | Register + get JWT tokens |
| `/api/auth/login` | POST | Login + get JWT tokens |
| `/api/signal` | POST | RL signal + LLM rationale + sentiment score |
| `/api/backtest` | POST | Walk-forward backtest with Sharpe/Sortino/Calmar |
| `/api/trades` | GET | Trade history (Postgres) |
| `/api/monitoring/drift` | GET | Feature drift report (KS test) |
| `/api/risk` | GET | Portfolio VaR + circuit breaker status |
| `/api/ingest-news` | POST | Trigger news ingestion |
| `/ws` | WS | Real-time bot state stream |

---

## Resume Bullet

> **Crypto RL Trading Bot** — Production ML system: PPO actor-critic agent (PyTorch) for autonomous crypto trading with LLM-grounded signal rationale via RAG (Gemini 2.0 Flash + pgvector). Full MLOps: W&B experiment tracking, HuggingFace Hub model registry, KS-test feature drift detection, Kelly-fraction risk management with portfolio VaR. Deployed 100% free (HF Spaces + Neon + Vercel). Walk-forward backtested with Sharpe/Sortino/Calmar metrics.
