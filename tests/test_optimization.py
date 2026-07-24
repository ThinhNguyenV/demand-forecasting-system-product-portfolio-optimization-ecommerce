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
