"""Lightweight Transformer for multi-horizon crypto price forecasting.

Architecture: positional-encoded input → 2-layer Transformer encoder → linear head
              predicting normalised returns at 1h, 4h, 24h horizons.

The predictions are fused as extra features into the RL agent's state vector,
giving the agent a forward-looking signal that pure technical indicators lack.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Positional encoding (sinusoidal, standard)
# ---------------------------------------------------------------------------

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term[:d_model // 2])
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, : x.size(1)]
        return self.dropout(x)


# ---------------------------------------------------------------------------
# Transformer forecaster
# ---------------------------------------------------------------------------

class PriceTransformer(nn.Module):
    """Encoder-only Transformer that predicts normalised returns at multiple horizons."""

    def __init__(
        self,
        input_dim: int = 6,     # OHLCV + returns
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 128,
        dropout: float = 0.1,
        n_horizons: int = 3,    # 1h, 4h, 24h
        seq_len: int = 48,      # input window length
    ):
        super().__init__()
        self.input_dim = input_dim
        self.d_model = d_model
        self.seq_len = seq_len
        self.n_horizons = n_horizons

        self.input_proj = nn.Linear(input_dim, d_model)
        self.pos_enc = PositionalEncoding(d_model, max_len=seq_len, dropout=dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # Multi-horizon output head
        self.head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Linear(d_model // 2, n_horizons),
        )

        # Confidence head — predicts how confident each horizon forecast is
        self.confidence_head = nn.Sequential(
            nn.Linear(d_model, n_horizons),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: (batch, seq_len, input_dim)
        Returns:
            predictions: (batch, n_horizons) — predicted normalised returns
            confidence:  (batch, n_horizons) — [0,1] confidence per horizon
        """
        h = self.input_proj(x)          # (B, S, d_model)
        h = self.pos_enc(h)
        h = self.encoder(h)             # (B, S, d_model)
        last = h[:, -1, :]              # (B, d_model) — use last token
        preds = self.head(last)          # (B, n_horizons)
        conf = self.confidence_head(last)
        return preds, conf


# ---------------------------------------------------------------------------
# Forecaster service (stateful, singleton-friendly)
# ---------------------------------------------------------------------------

class PriceForecaster:
    """High-level service: prepares data, runs inference, manages training."""

    HORIZONS = {"1h": 1, "4h": 4, "24h": 24}
    INPUT_DIM = 6   # close_ret, high_ret, low_ret, volume_norm, rsi_norm, macd_norm
    SEQ_LEN = 48

    def __init__(self, device: Optional[str] = None):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = PriceTransformer(
            input_dim=self.INPUT_DIM,
            seq_len=self.SEQ_LEN,
        ).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)
        self.loss_fn = nn.MSELoss()
        self.trained = False
        self._loss_history: List[float] = []

    # ── Data preparation ──────────────────────────────────────────
    @staticmethod
    def _prepare_features(df) -> np.ndarray:
        """Convert OHLCV + indicators DataFrame to normalised feature matrix."""
        close = df["close"].values.astype(float)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        volume = df["volume"].values.astype(float)

        close_ret = np.zeros_like(close)
        close_ret[1:] = np.diff(close) / (close[:-1] + 1e-10)

        high_ret = np.zeros_like(high)
        high_ret[1:] = (high[1:] - close[:-1]) / (close[:-1] + 1e-10)

        low_ret = np.zeros_like(low)
        low_ret[1:] = (low[1:] - close[:-1]) / (close[:-1] + 1e-10)

        vol_norm = volume / (np.mean(volume) + 1e-10)

        rsi = df["rsi"].values.astype(float) if "rsi" in df.columns else np.full(len(df), 50.0)
        rsi_norm = (rsi - 50.0) / 50.0

        macd_hist = df["macd_hist"].values.astype(float) if "macd_hist" in df.columns else np.zeros(len(df))
        macd_norm = macd_hist / (close + 1e-10)

        features = np.column_stack([close_ret, high_ret, low_ret, vol_norm, rsi_norm, macd_norm])
        return np.nan_to_num(features, nan=0.0)

    @staticmethod
    def _build_targets(close: np.ndarray, horizons: List[int]) -> np.ndarray:
        """Build normalised return targets for each horizon."""
        n = len(close)
        targets = np.zeros((n, len(horizons)))
        for j, h in enumerate(horizons):
            for i in range(n - h):
                targets[i, j] = (close[i + h] - close[i]) / (close[i] + 1e-10)
        return targets

    def _make_sequences(self, features: np.ndarray, targets: np.ndarray):
        """Sliding-window sequences for training."""
        n = len(features)
        X, Y = [], []
        for i in range(self.SEQ_LEN, n):
            X.append(features[i - self.SEQ_LEN: i])
            Y.append(targets[i])
        return np.array(X), np.array(Y)

    # ── Training ──────────────────────────────────────────────────
    def train_on_df(self, df, epochs: int = 20, batch_size: int = 32) -> Dict[str, Any]:
        """Train the Transformer on a DataFrame with OHLCV + indicators."""
        features = self._prepare_features(df)
        close = df["close"].values.astype(float)
        horizons = list(self.HORIZONS.values())
        targets = self._build_targets(close, horizons)

        X, Y = self._make_sequences(features, targets)
        if len(X) < batch_size:
            return {"error": "Not enough data", "samples": len(X)}

        X_t = torch.FloatTensor(X).to(self.device)
        Y_t = torch.FloatTensor(Y).to(self.device)

        self.model.train()
        epoch_losses = []
        for ep in range(epochs):
            perm = torch.randperm(len(X_t))
            total_loss = 0.0
            n_batches = 0
            for start in range(0, len(X_t), batch_size):
                idx = perm[start: start + batch_size]
                xb, yb = X_t[idx], Y_t[idx]
                preds, _ = self.model(xb)
                loss = self.loss_fn(preds, yb)
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                total_loss += loss.item()
                n_batches += 1
            avg = total_loss / max(n_batches, 1)
            epoch_losses.append(avg)

        self.trained = True
        self._loss_history.extend(epoch_losses)

        return {
            "epochs": epochs,
            "final_loss": round(epoch_losses[-1], 6),
            "samples": len(X),
            "loss_curve": [round(l, 6) for l in epoch_losses],
        }

    # ── Inference ─────────────────────────────────────────────────
    def predict(self, df) -> Dict[str, Any]:
        """Predict next 1h/4h/24h returns from the latest SEQ_LEN candles."""
        features = self._prepare_features(df)
        if len(features) < self.SEQ_LEN:
            return {"predictions": {}, "confidence": {}, "trained": False}

        seq = features[-self.SEQ_LEN:]
        x = torch.FloatTensor(seq).unsqueeze(0).to(self.device)

        self.model.eval()
        with torch.no_grad():
            preds, conf = self.model(x)

        pred_vals = preds.cpu().numpy().flatten()
        conf_vals = conf.cpu().numpy().flatten()

        horizon_names = list(self.HORIZONS.keys())
        return {
            "predictions": {
                horizon_names[i]: round(float(pred_vals[i]) * 100, 4)
                for i in range(len(horizon_names))
            },
            "confidence": {
                horizon_names[i]: round(float(conf_vals[i]), 4)
                for i in range(len(horizon_names))
            },
            "trained": self.trained,
        }

    def predict_as_features(self, df) -> np.ndarray:
        """Return a flat array of [pred_1h, pred_4h, pred_24h, conf_1h, conf_4h, conf_24h]
        suitable for concatenation into the RL state vector."""
        result = self.predict(df)
        preds = list(result["predictions"].values()) if result["predictions"] else [0.0, 0.0, 0.0]
        confs = list(result["confidence"].values()) if result["confidence"] else [0.0, 0.0, 0.0]
        return np.array(preds + confs, dtype=np.float32)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "trained": self.trained,
            "total_params": sum(p.numel() for p in self.model.parameters()),
            "loss_history": self._loss_history[-50:],
            "architecture": {
                "type": "TransformerEncoder",
                "layers": 2,
                "heads": 4,
                "d_model": 64,
                "seq_len": self.SEQ_LEN,
                "horizons": list(self.HORIZONS.keys()),
            },
        }


# Module-level singleton
price_forecaster = PriceForecaster()
