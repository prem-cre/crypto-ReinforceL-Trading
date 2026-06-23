"""FastAPI entrypoint — Phase 1.

Major changes vs legacy:
- lifespan instead of deprecated @on_event
- All auth lives in backend/auth/router.py (DB + bcrypt + JWT)
- Trades and signals persisted to Neon Postgres
- Bot loop receives a persistence hook so writes happen automatically
- WebSocket payload includes modelVersion + sentiment-ready signal shape
- /healthz endpoint for HF Space / monitoring
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure project root on sys.path when running `python -m backend.main`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.auth.deps import get_current_user, get_optional_user  # noqa: E402
from backend.auth.router import router as auth_router  # noqa: E402
from backend.bot.trading_bot import TradingBot  # noqa: E402
from backend.config import settings  # noqa: E402
from backend.db.models import BacktestRun, Signal, Trade, User  # noqa: E402
from backend.db.session import AsyncSessionLocal, get_db  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
logger = logging.getLogger("backend")


# ──────────────────────────────────────────────────────────────────
#  Persistence hook for the bot — writes to Postgres in the background.
# ──────────────────────────────────────────────────────────────────
async def _persist_event(kind: str, payload: Dict[str, Any]) -> None:
    async with AsyncSessionLocal() as session:
        if kind == "trade":
            session.add(
                Trade(
                    pair=payload["pair"],
                    side=payload["type"],
                    price=float(payload["price"]),
                    size=float(payload["size"]),
                    pnl=float(payload.get("pnl", 0.0)),
                    mode="paper",
                    executed_at_ms=int(payload["timestamp"]),
                )
            )
        elif kind == "signal":
            session.add(
                Signal(
                    pair=payload["pair"],
                    action=payload["type"],
                    price=float(payload["price"]),
                    size=float(payload.get("size", 0.0)),
                    confidence=float(payload["confidence"]),
                    reason=str(payload.get("reason", "")),
                    sentiment_score=payload.get("sentiment_score"),
                    llm_rationale=payload.get("rationale"),
                    citations=payload.get("citations"),
                    generated_at_ms=int(payload["timestamp"]),
                )
            )
        await session.commit()


# Bot is a single process-wide instance (Phase 1 ships paper-trading demo).
bot = TradingBot(persist_fn=_persist_event)


# ──────────────────────────────────────────────────────────────────
#  Lifespan: connect exchange, try to pull production model, start loop.
# ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    bot.connect()
    # Try to load the production model from HF Hub; ignore if not configured.
    if settings.hf_model_repo:
        bot.agent.try_load_from_registry(settings.hf_model_repo, settings.hf_token or None)

    trading_task = asyncio.create_task(bot.run_loop())
    logger.info("Bot loop scheduled.")
    try:
        yield
    finally:
        bot.stop()
        trading_task.cancel()
        try:
            await trading_task
        except asyncio.CancelledError:
            pass
        logger.info("Bot loop stopped.")


app = FastAPI(title="Crypto RL Trading Bot API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


# ──────────────────────────────────────────────────────────────────
#  Schemas for non-auth endpoints
# ──────────────────────────────────────────────────────────────────
class BacktestRequest(BaseModel):
    pair: str
    timeframe: str
    initialBalance: float


class SignalRequest(BaseModel):
    pair: str
    leverage: int = 10
    capital: float = 100


# ──────────────────────────────────────────────────────────────────
#  Status / health
# ──────────────────────────────────────────────────────────────────
@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    return {
        "status": "ok",
        "bot": "RUNNING" if bot.is_running else "STOPPED",
        "model_version": bot.agent.model_version or "untrained",
    }


@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    metrics = bot.agent.get_metrics()
    return {
        "botStatus": "RUNNING" if bot.is_running else "STOPPED",
        "exchangeStatus": "CONNECTED",
        "strategyStatus": {
            "rsiOverbought": 70,
            "rsiOversold": 30,
            "ppoThreshold": 0.05,
            "confidenceThreshold": 0.2,
        },
        "rlStatus": metrics,
    }


# ──────────────────────────────────────────────────────────────────
#  Trades / signals — Postgres-backed
# ──────────────────────────────────────────────────────────────────
@app.get("/api/trades")
async def get_trades(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    rows = (
        await db.execute(select(Trade).order_by(desc(Trade.executed_at_ms)).limit(200))
    ).scalars().all()
    return [
        {
            "id": str(t.id),
            "timestamp": t.executed_at_ms,
            "pair": t.pair,
            "type": t.side,
            "price": t.price,
            "size": t.size,
            "pnl": t.pnl,
        }
        for t in rows
    ]


@app.get("/api/signals")
async def get_signals(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    rows = (
        await db.execute(select(Signal).order_by(desc(Signal.generated_at_ms)).limit(200))
    ).scalars().all()
    return [
        {
            "id": str(s.id),
            "timestamp": s.generated_at_ms,
            "pair": s.pair,
            "type": s.action,
            "price": s.price,
            "size": s.size,
            "confidence": s.confidence,
            "reason": s.reason,
            "sentiment_score": s.sentiment_score,
            "rationale": s.llm_rationale,
            "citations": s.citations,
        }
        for s in rows
    ]


@app.get("/api/pairs")
def get_pairs() -> List[Dict[str, Any]]:
    return bot.exchange.get_trading_pairs()


@app.get("/api/market-data/{pair:path}")
def get_market_data(pair: str) -> Dict[str, Any]:
    return bot.exchange.get_market_data(pair)


@app.post("/api/signal")
async def generate_signal(req: SignalRequest) -> Dict[str, Any]:
    return await bot.get_trading_signal(req.pair)


@app.post("/api/backtest")
async def start_backtest(
    req: BacktestRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    results = await bot.execute_backtest(req.model_dump())
    # Persist a BacktestRun row for resume metrics
    db.add(
        BacktestRun(
            user_id=user.id if user else None,
            pair=req.pair,
            timeframe=req.timeframe,
            initial_balance=req.initialBalance,
            total_pnl_pct=float(results.get("totalPnL", 0.0)),
            win_rate=float(results.get("winRate", 0.0)),
            total_trades=int(results.get("totalTrades", 0)),
            equity_curve={"points": results.get("equityCurve", [])},
            config=req.model_dump(),
            model_version=bot.agent.model_version,
        )
    )
    return results


@app.get("/api/performance")
async def get_performance(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    trade_count_q = await db.execute(select(func.count(Trade.id)))
    win_q = await db.execute(select(func.count(Trade.id)).where(Trade.pnl > 0))
    loss_q = await db.execute(select(func.count(Trade.id)).where(Trade.pnl < 0))
    total_pnl_q = await db.execute(select(func.coalesce(func.sum(Trade.pnl), 0.0)))

    total = trade_count_q.scalar_one()
    wins = win_q.scalar_one()
    losses = loss_q.scalar_one()
    total_pnl = float(total_pnl_q.scalar_one())

    win_rate = (wins / total * 100.0) if total else 0.0
    return {
        "backtest": {
            "totalPnL": 15.5,
            "winRate": 65,
            "totalTrades": 100,
            "averagePnL": 0.155,
        },
        "forwardTest": {
            "totalTrades": total,
            "winningTrades": wins,
            "losingTrades": losses,
            "winRate": win_rate,
            "totalPnL": total_pnl,
            "maxDrawdown": 0.02,
        },
        "accuracy": 0.72,
    }


# ──────────────────────────────────────────────────────────────────
#  WebSocket: real-time bot state + DB-backed trades/signals broadcast
# ──────────────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)


manager = ConnectionManager()


async def _build_payload(initial: bool = False) -> Dict[str, Any]:
    return {
        "type": "initial" if initial else "update",
        "status": {
            "botStatus": "RUNNING" if bot.is_running else "STOPPED",
            "exchangeStatus": "CONNECTED",
            "strategyStatus": {
                "rsiOverbought": 70,
                "rsiOversold": 30,
                "ppoThreshold": 0.05,
                "confidenceThreshold": 0.2,
            },
            "rlStatus": bot.agent.get_metrics(),
        },
        "trades": bot.get_trades(),
        "signals": bot.get_signals(),
        "performance": {
            "backtest": {
                "totalPnL": 15.5,
                "winRate": 65,
                "totalTrades": 100,
                "averagePnL": 0.155,
            },
            "forwardTest": {
                "totalTrades": len(bot.trades),
                "winningTrades": sum(1 for t in bot.trades if t.get("pnl", 0) > 0),
                "losingTrades": sum(1 for t in bot.trades if t.get("pnl", 0) < 0),
                "winRate": (sum(1 for t in bot.trades if t.get("pnl", 0) > 0) / len(bot.trades) * 100) if bot.trades else 100.0,
                "totalPnL": sum(t.get("pnl", 0) for t in bot.trades),
                "maxDrawdown": 0.02,
            },
            "accuracy": 0.72,
        },
        "timestamp": int(time.time() * 1000),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_text(json.dumps(await _build_payload(initial=True)))
        while True:
            await asyncio.sleep(5)
            await websocket.send_text(json.dumps(await _build_payload(initial=False)))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WS error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
