import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ─── Environment ─────────────────────────────────────────────
    env: str = Field(default="development", validation_alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api", validation_alias="API_V1_PREFIX")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        validation_alias="CORS_ORIGINS",
    )

    # ─── Database (Neon Postgres + pgvector) ─────────────────────
    # Example: postgresql+asyncpg://user:pass@ep-xxx.neon.tech/dbname?sslmode=require
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/cryptobot",
        validation_alias="DATABASE_URL",
    )
    # Sync URL for Alembic migrations (auto-derived if not set)
    database_url_sync: str = Field(default="", validation_alias="DATABASE_URL_SYNC")

    # ─── Auth ────────────────────────────────────────────────────
    jwt_secret: str = Field(
        default="change-me-in-production-please-this-is-not-secret",
        validation_alias="JWT_SECRET",
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=30, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # ─── External APIs ───────────────────────────────────────────
    binance_api_key: str = Field(default="", validation_alias="BINANCE_API_KEY")
    binance_api_secret: str = Field(default="", validation_alias="BINANCE_API_SECRET")

    # Model registry / LLM (Phase 1+2)
    hf_token: str = Field(default="", validation_alias="HF_TOKEN")
    hf_model_repo: str = Field(default="", validation_alias="HF_MODEL_REPO")  # e.g. "your-username/crypto-rl-bot"
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")

    # Experiment tracking (Phase 4)
    wandb_api_key: str = Field(default="", validation_alias="WANDB_API_KEY")
    wandb_project: str = Field(default="crypto-rl-trading-bot", validation_alias="WANDB_PROJECT")

    # Observability (Phase 4)
    logtail_source_token: str = Field(default="", validation_alias="LOGTAIL_SOURCE_TOKEN")

    # ─── Trading configuration ───────────────────────────────────
    trading_pairs: str = Field(default="BTC/USDT,ETH/USDT,BNB/USDT", validation_alias="TRADING_PAIRS")
    timeframe: str = Field(default="1h", validation_alias="TIMEFRAME")
    initial_capital: float = Field(default=10000.0, validation_alias="INITIAL_CAPITAL")

    # ─── RL training ─────────────────────────────────────────────
    batch_size: int = Field(default=64, validation_alias="BATCH_SIZE")
    epochs: int = Field(default=10, validation_alias="EPOCHS")
    min_trades: int = Field(default=100, validation_alias="MIN_TRADES")
    min_win_rate: float = Field(default=0.55, validation_alias="MIN_WIN_RATE")
    max_drawdown: float = Field(default=0.2, validation_alias="MAX_DRAWDOWN")
    retrain_interval: int = Field(default=86400000, validation_alias="RETRAIN_INTERVAL")

    # ─── Risk management ─────────────────────────────────────────
    max_risk_per_trade: float = Field(default=0.02, validation_alias="MAX_RISK_PER_TRADE")
    max_leverage: int = Field(default=10, validation_alias="MAX_LEVERAGE")
    max_open_positions: int = Field(default=5, validation_alias="MAX_OPEN_POSITIONS")
    stop_loss_distance: float = Field(default=0.02, validation_alias="STOP_LOSS_DISTANCE")
    take_profit_distance: float = Field(default=0.04, validation_alias="TAKE_PROFIT_DISTANCE")
    trailing_stop_distance: float = Field(default=0.01, validation_alias="TRAILING_STOP_DISTANCE")

    # ─── RL model hyperparameters ────────────────────────────────
    learning_rate: float = Field(default=0.001, validation_alias="LEARNING_RATE")
    gamma: float = Field(default=0.99, validation_alias="GAMMA")
    epsilon: float = Field(default=1.0, validation_alias="EPSILON")
    epsilon_min: float = Field(default=0.01, validation_alias="EPSILON_MIN")
    epsilon_decay: float = Field(default=0.995, validation_alias="EPSILON_DECAY")

    # ─── State / feature config ──────────────────────────────────
    state_window: int = Field(default=50, validation_alias="STATE_WINDOW")
    state_size: int = Field(default=10, validation_alias="STATE_SIZE")  # grows in Phase 2/3
    indicators: str = Field(default="EMA,MACD,RSI,VOLUME", validation_alias="INDICATORS")
    market_conditions: str = Field(default="TREND,VOLATILITY,VOLUME", validation_alias="MARKET_CONDITIONS")

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def pairs_list(self) -> List[str]:
        return [p.strip() for p in self.trading_pairs.split(",") if p.strip()]

    @property
    def indicators_list(self) -> List[str]:
        return [i.strip() for i in self.indicators.split(",") if i.strip()]

    @property
    def market_conditions_list(self) -> List[str]:
        return [m.strip() for m in self.market_conditions.split(",") if m.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sync_database_url(self) -> str:
        """Used by Alembic. Falls back to converting async URL → sync."""
        if self.database_url_sync:
            return self.database_url_sync
        return self.database_url.replace("+asyncpg", "")


settings = Settings()
