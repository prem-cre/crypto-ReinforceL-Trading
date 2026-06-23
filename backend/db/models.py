"""
Database models for the Crypto RL Trading Bot.

Tables:
- users          : auth (bcrypt password hash)
- trades         : every executed paper/live trade
- signals        : every RL-generated signal (with LLM rationale once Phase 2 lands)
- backtest_runs  : Sharpe / Sortino / MaxDD per backtest config
- rl_runs        : training run metadata (Phase 4 W&B sync)
- news_chunks    : embedded news for RAG (pgvector) — used in Phase 2
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


# ─── Auth ────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    trades: Mapped[list["Trade"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    signals: Mapped[list["Signal"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    backtest_runs: Mapped[list["BacktestRun"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ─── Trading ─────────────────────────────────────────────────────
class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    pair: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)  # BUY_LONG, SELL_SHORT, BUY_TO_COVER, SELL_CLOSE
    price: Mapped[float] = mapped_column(Float, nullable=False)
    size: Mapped[float] = mapped_column(Float, nullable=False)
    pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), default="paper", nullable=False)  # paper | live
    executed_at_ms: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)

    user: Mapped[Optional["User"]] = relationship(back_populates="trades")


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    pair: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(8), nullable=False)  # BUY | SELL | HOLD
    price: Mapped[float] = mapped_column(Float, nullable=False)
    size: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Phase 2 fields (LLM rationale + citations + sentiment)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    llm_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    citations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # list of {url, title, source}

    generated_at_ms: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)

    user: Mapped[Optional["User"]] = relationship(back_populates="signals")


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    pair: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    initial_balance: Mapped[float] = mapped_column(Float, nullable=False)

    # Metrics (Phase 3 fills these properly)
    total_pnl_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sortino: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calmar: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_drawdown_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    benchmark_pnl_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    equity_curve: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # [{ts, equity}, ...]
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="backtest_runs")


# ─── RL training metadata (Phase 4) ───────────────────────────────
class RLRun(Base):
    __tablename__ = "rl_runs"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wandb_run_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    hyperparams: Mapped[dict] = mapped_column(JSON, nullable=False)
    eval_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_production: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hf_hub_uri: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


# ─── RAG: news chunks (Phase 2) ───────────────────────────────────
class NewsChunk(Base):
    __tablename__ = "news_chunks"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset: Mapped[str] = mapped_column(String(16), index=True, nullable=False)  # BTC, ETH, etc.
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # cryptopanic | reddit | ...
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    published_at_ms: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)

    # text-embedding-004 is 768-dim
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(768), nullable=True)

    __table_args__ = (
        Index("ix_news_asset_published", "asset", "published_at_ms"),
    )


# ─── LLM response cache (Phase 2, keeps Gemini under free tier) ───
class LLMCache(Base):
    __tablename__ = "llm_cache"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    response: Mapped[dict] = mapped_column(JSON, nullable=False)
    expires_at_ms: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
