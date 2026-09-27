"""Demand forecasting, model evaluation, and explainability models."""
from __future__ import annotations

from .evaluation import (
    backtest_demand,
    benchmark_forecast_models,
    best_model_from_metrics,
    summarize_backtest,
)
from .explainability import (
    GlobalRFExplanation,
    explain_global_random_forest,
    grouped_shap_importance,
)
from .forecasting import (
    GLOBAL_RANDOM_FOREST_MODEL,
    PATTERN_ROUTED_MODEL,
    SUPPORTED_MODELS,
    forecast_demand,
    forecast_series,
    reconcile_sku_to_category_forecast,
)

__all__ = [
    "GLOBAL_RANDOM_FOREST_MODEL",
    "PATTERN_ROUTED_MODEL",
    "SUPPORTED_MODELS",
    "GlobalRFExplanation",
    "backtest_demand",
    "benchmark_forecast_models",
    "best_model_from_metrics",
    "explain_global_random_forest",
    "forecast_demand",
    "forecast_series",
    "grouped_shap_importance",
    "reconcile_sku_to_category_forecast",
    "summarize_backtest",
]
