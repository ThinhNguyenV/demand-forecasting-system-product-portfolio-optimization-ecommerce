import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecom_forecasting.models.forecasting import forecast_demand, forecast_series, reconcile_sku_to_category_forecast


def test_intermittent_models_return_non_negative_forecast():
    series = pd.Series([0, 0, 3, 0, 0, 6], index=pd.date_range("2024-01-01", periods=6, freq="MS"))

    croston = forecast_series(series, horizon=3, model_name="croston")
    tsb = forecast_series(series, horizon=3, model_name="tsb")

    assert len(croston) == 3
    assert len(tsb) == 3
    assert (croston >= 0).all()
    assert (tsb >= 0).all()
    assert croston.sum() > 0
    assert tsb.sum() > 0


def test_reconcile_sku_to_category_forecast_matches_category_target():
    sku_forecast = pd.DataFrame(
        {
            "date": ["2024-07-01", "2024-07-01", "2024-07-01"],
            "sku": ["a", "b", "c"],
            "title": ["A", "B", "C"],
            "category": ["x", "x", "y"],
            "model": ["pattern_routed", "pattern_routed", "pattern_routed"],
            "forecast_quantity": [6, 4, 5],
            "price": [10.0, 20.0, 30.0],
            "forecast_revenue": [60.0, 80.0, 150.0],
        }
    )
    category_forecast = pd.DataFrame(
        {
            "date": ["2024-07-01", "2024-07-01"],
            "category": ["x", "y"],
            "forecast_quantity": [20, 3],
        }
    )

    result = reconcile_sku_to_category_forecast(sku_forecast, category_forecast)

    totals = result.groupby("category")["forecast_quantity"].sum().to_dict()
    assert totals == {"x": 20, "y": 3}
    assert "pre_reconciliation_forecast_quantity" in result.columns
    assert "reconciliation_factor" in result.columns

def test_global_random_forest_supports_recursive_multi_step_forecast():
    dates = pd.date_range("2023-01-01", periods=12, freq="MS")
    history = pd.DataFrame(
        [
            {
                "date": date,
                "sku": sku,
                "title": sku.upper(),
                "category": "category_a",
                "quantity": quantity + offset,
                "price": 10.0 + offset,
                "demand_pattern": "fast_moving",
            }
            for offset, sku in enumerate(["a", "b"])
            for quantity, date in enumerate(dates, start=1)
        ]
    )

    result = forecast_demand(history, horizon=3, model_name="random_forest_global")

    assert len(result) == 6
    assert result.groupby("sku").size().to_dict() == {"a": 3, "b": 3}
    assert (result["forecast_quantity"] >= 0).all()
