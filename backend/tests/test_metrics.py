"""Unit tests for performance metrics."""
import pytest
from backend.metrics.performance import sharpe_ratio, sortino_ratio, max_drawdown, calmar_ratio, compute_all


def _equity(returns):
    eq = [1000.0]
    for r in returns:
        eq.append(eq[-1] * (1 + r))
    return eq


def test_sharpe_flat():
    eq = [1000.0] * 100
    assert sharpe_ratio(eq) == 0.0


def test_sharpe_positive():
    # consistent 0.1% daily gain → positive Sharpe
    eq = _equity([0.001] * 252)
    assert sharpe_ratio(eq) > 1.0


def test_max_drawdown_zero():
    eq = [100.0 * (1.01 ** i) for i in range(50)]
    assert max_drawdown(eq) == pytest.approx(0.0, abs=1e-4)


def test_max_drawdown_known():
    eq = [100.0, 120.0, 80.0, 90.0]
    dd = max_drawdown(eq)
    assert dd == pytest.approx(-1/3, rel=0.01)


def test_sortino_higher_than_sharpe_on_up_only():
    eq = _equity([0.01 if i % 2 == 0 else -0.001 for i in range(200)])
    s = sharpe_ratio(eq)
    so = sortino_ratio(eq)
    # Sortino ignores upside vol → usually higher than Sharpe for asymmetric returns
    assert so > s


def test_compute_all_basic():
    trades = [{"pnl": 50.0}, {"pnl": -20.0}, {"pnl": 30.0}]
    eq = [1000.0, 1050.0, 1030.0, 1060.0]
    result = compute_all(trades, eq, 1000.0)
    assert result["totalTrades"] == 3
    assert result["winRate"] == pytest.approx(66.7, rel=0.01)
    assert "sharpe" in result
    assert "maxDrawdownPct" in result
