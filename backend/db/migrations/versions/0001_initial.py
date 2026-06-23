"""initial schema: users, trades, signals, backtest_runs, rl_runs, news_chunks (pgvector), llm_cache

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "trades",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("pair", sa.String(32), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("size", sa.Float, nullable=False),
        sa.Column("pnl", sa.Float, nullable=False, server_default="0"),
        sa.Column("mode", sa.String(16), nullable=False, server_default="paper"),
        sa.Column("executed_at_ms", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_trades_user_id", "trades", ["user_id"])
    op.create_index("ix_trades_pair", "trades", ["pair"])
    op.create_index("ix_trades_executed_at_ms", "trades", ["executed_at_ms"])

    op.create_table(
        "signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("pair", sa.String(32), nullable=False),
        sa.Column("action", sa.String(8), nullable=False),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("size", sa.Float, nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("reason", sa.Text, nullable=False, server_default=""),
        sa.Column("sentiment_score", sa.Float, nullable=True),
        sa.Column("llm_rationale", sa.Text, nullable=True),
        sa.Column("citations", JSONB, nullable=True),
        sa.Column("generated_at_ms", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_signals_user_id", "signals", ["user_id"])
    op.create_index("ix_signals_pair", "signals", ["pair"])
    op.create_index("ix_signals_generated_at_ms", "signals", ["generated_at_ms"])

    op.create_table(
        "backtest_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("pair", sa.String(32), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("initial_balance", sa.Float, nullable=False),
        sa.Column("total_pnl_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_trades", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sharpe", sa.Float, nullable=True),
        sa.Column("sortino", sa.Float, nullable=True),
        sa.Column("calmar", sa.Float, nullable=True),
        sa.Column("max_drawdown_pct", sa.Float, nullable=True),
        sa.Column("benchmark_pnl_pct", sa.Float, nullable=True),
        sa.Column("equity_curve", JSONB, nullable=True),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_backtest_runs_user_id", "backtest_runs", ["user_id"])

    op.create_table(
        "rl_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("wandb_run_id", sa.String(64), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("hyperparams", JSONB, nullable=False),
        sa.Column("eval_metrics", JSONB, nullable=True),
        sa.Column("is_production", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("hf_hub_uri", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rl_runs_wandb_run_id", "rl_runs", ["wandb_run_id"])

    op.create_table(
        "news_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("asset", sa.String(16), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("published_at_ms", sa.BigInteger, nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_news_chunks_asset", "news_chunks", ["asset"])
    op.create_index("ix_news_chunks_published_at_ms", "news_chunks", ["published_at_ms"])
    op.create_index("ix_news_asset_published", "news_chunks", ["asset", "published_at_ms"])
    # HNSW vector index for fast cosine search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_news_embedding_hnsw "
        "ON news_chunks USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "llm_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cache_key", sa.String(255), nullable=False, unique=True),
        sa.Column("response", JSONB, nullable=False),
        sa.Column("expires_at_ms", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_llm_cache_cache_key", "llm_cache", ["cache_key"])
    op.create_index("ix_llm_cache_expires_at_ms", "llm_cache", ["expires_at_ms"])


def downgrade() -> None:
    op.drop_table("llm_cache")
    op.drop_table("news_chunks")
    op.drop_table("rl_runs")
    op.drop_table("backtest_runs")
    op.drop_table("signals")
    op.drop_table("trades")
    op.drop_table("users")
