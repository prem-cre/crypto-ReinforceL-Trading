"""Tests for the Transformer price forecasting module."""
import numpy as np
import pandas as pd
import pytest

from backend.forecasting.transformer_model import PriceForecaster, PriceTransformer


class TestPriceTransformer:
    def test_forward_pass(self):
        import torch
        model = PriceTransformer(input_dim=6, seq_len=48)
        x = torch.randn(2, 48, 6)
        preds, conf = model(x)
        assert preds.shape == (2, 3)
        assert conf.shape == (2, 3)
        assert (conf >= 0).all() and (conf <= 1).all()


class TestPriceForecaster:
    @pytest.fixture
    def sample_df(self):
        n = 200
        np.random.seed(42)
        close = 50000 + np.cumsum(np.random.randn(n) * 100)
        return pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h"),
            "open": close * 0.999,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": np.random.uniform(10, 100, n),
            "rsi": np.random.uniform(30, 70, n),
            "macd_hist": np.random.randn(n) * 50,
        })

    def test_prepare_features(self, sample_df):
        features = PriceForecaster._prepare_features(sample_df)
        assert features.shape == (200, 6)
        assert not np.any(np.isnan(features))

    def test_train_on_df(self, sample_df):
        forecaster = PriceForecaster()
        result = forecaster.train_on_df(sample_df, epochs=2, batch_size=16)
        assert "final_loss" in result
        assert result["epochs"] == 2
        assert forecaster.trained

    def test_predict(self, sample_df):
        forecaster = PriceForecaster()
        forecaster.train_on_df(sample_df, epochs=2, batch_size=16)
        result = forecaster.predict(sample_df)
        assert "predictions" in result
        assert "1h" in result["predictions"]
        assert "4h" in result["predictions"]
        assert "24h" in result["predictions"]

    def test_predict_as_features(self, sample_df):
        forecaster = PriceForecaster()
        forecaster.train_on_df(sample_df, epochs=2, batch_size=16)
        feats = forecaster.predict_as_features(sample_df)
        assert feats.shape == (6,)  # 3 preds + 3 confidences

    def test_get_metrics(self):
        forecaster = PriceForecaster()
        m = forecaster.get_metrics()
        assert "architecture" in m
        assert m["architecture"]["type"] == "TransformerEncoder"
