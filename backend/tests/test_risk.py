"""Unit tests for risk manager."""
import pytest
from backend.risk.risk_manager import RiskManager


def test_no_pause_normal():
    rm = RiskManager(initial_balance=10000.0)
    assert not rm.is_paused(9500.0)  # 5% drawdown, below 15% threshold


def test_pause_on_large_drawdown():
    rm = RiskManager(initial_balance=10000.0)
    rm.peak_balance = 10000.0
    assert rm.is_paused(8400.0)  # 16% drawdown → paused


def test_position_size_positive():
    rm = RiskManager(initial_balance=10000.0)
    size = rm.position_size(10000.0, win_rate=0.6, avg_win=100.0, avg_loss=60.0, price=50000.0)
    assert size > 0


def test_position_size_zero_when_paused():
    rm = RiskManager(initial_balance=10000.0, max_drawdown_pct=0.05)
    rm.peak_balance = 10000.0
    size = rm.position_size(9000.0, win_rate=0.6, avg_win=100.0, avg_loss=60.0, price=50000.0)
    assert size == 0.0


def test_var_insufficient_data():
    rm = RiskManager(initial_balance=10000.0)
    result = rm.portfolio_var(10000.0)
    assert result["samples"] == 0
