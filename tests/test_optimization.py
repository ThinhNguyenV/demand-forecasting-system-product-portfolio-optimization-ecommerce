import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecom_forecasting.optimization import optimize_portfolio


def test_optimize_portfolio_respects_top_n():
    products = pd.DataFrame(
        {
            "sku": ["a", "b", "c"],
            "title": ["A", "B", "C"],
            "category": ["x", "y", "y"],
            "price": [10, 20, 30],
            "estimated_margin_rate": [0.2, 0.3, 0.4],
        }
    )
    forecast = pd.DataFrame(
        {
            "sku": ["a", "b", "c"],
            "forecast_quantity": [10, 30, 20],
            "forecast_revenue": [100, 600, 600],
        }
    )

    result = optimize_portfolio(products, forecast, top_n=2, max_category_share=0.5)

    assert len(result) == 2
    assert set(result["recommendation"])


def test_optimize_portfolio_uses_backtest_error_as_safety_stock():
    products = pd.DataFrame(
        {
            "sku": ["a"],
            "title": ["A"],
            "category": ["x"],
            "price": [10],
            "estimated_margin_rate": [0.2],
            "demand_pattern": ["fast_moving"],
        }
    )
    forecast = pd.DataFrame(
        {
            "date": ["2024-07-01", "2024-08-01"],
            "sku": ["a", "a"],
            "forecast_quantity": [10, 10],
            "forecast_revenue": [100, 100],
        }
    )
    metrics = pd.DataFrame({"sku": ["a"], "error_std": [2.0]})

    result = optimize_portfolio(products, forecast, top_n=1, backtest_metrics=metrics, service_level_z=1.0)

    assert result.loc[0, "safety_stock"] == 3
    assert result.loc[0, "risk_adjusted_quantity"] == 23
    assert result.loc[0, "forecast_error_std"] == 2.0
