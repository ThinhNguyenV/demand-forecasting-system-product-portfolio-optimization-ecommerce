from __future__ import annotations

from dataclasses import dataclass

from .config import CHART_DIR, PipelinePaths, ensure_directories
from .dashboard_data import export_dashboard_datasets
from .eda import create_eda_charts
from .evaluation import backtest_demand, benchmark_forecast_models, best_model_from_metrics
from .forecasting import forecast_demand
from .olist import build_olist_inputs
from .optimization import optimize_portfolio
from .time_series import aggregate_enriched_items_by_category


@dataclass(frozen=True)
class PipelineResult:
    raw_rows: int
    clean_rows: int
    demand_rows: int
    forecast_rows: int
    portfolio_rows: int
    paths: PipelinePaths


def run_pipeline(
    pages: int | None = None,
    horizon: int = 6,
    top_n: int = 30,
    create_charts: bool = True,
    max_products: int = 800,
    min_months: int = 4,
) -> PipelineResult:
    """Run the main Olist forecasting and portfolio pipeline."""
    del pages
    ensure_directories()
    paths = PipelinePaths()
    test_months = min(3, horizon)

    olist = build_olist_inputs(max_products=max_products, min_months=min_months)
    category_history = aggregate_enriched_items_by_category(olist.enriched_items)

    olist.enriched_items.to_csv(paths.olist_order_items, index=False, encoding="utf-8-sig")
    olist.products.to_csv(paths.raw_products, index=False, encoding="utf-8-sig")
    olist.products.to_csv(paths.clean_products, index=False, encoding="utf-8-sig")
    olist.demand_history.to_csv(paths.demand_history, index=False, encoding="utf-8-sig")
    category_history.to_csv(paths.category_demand_history, index=False, encoding="utf-8-sig")

    model_details, model_metrics = benchmark_forecast_models(
        category_history,
        test_months=test_months,
        model_names=(
            "naive",
            "moving_average",
            "seasonal_naive",
            "simple_exp_smoothing",
            "exp_smoothing",
            "random_forest",
        ),
    )
    model_details.to_csv(paths.model_comparison_details, index=False, encoding="utf-8-sig")
    model_metrics.to_csv(paths.model_comparison_metrics, index=False, encoding="utf-8-sig")
    best_category_model = best_model_from_metrics(model_metrics)

    sku_backtest_details, sku_backtest_metrics = backtest_demand(
        olist.demand_history,
        test_months=test_months,
        model_name="exp_smoothing",
    )
    sku_backtest_details.to_csv(paths.forecast_backtest_details, index=False, encoding="utf-8-sig")
    sku_backtest_metrics.to_csv(paths.forecast_backtest_metrics, index=False, encoding="utf-8-sig")

    category_backtest_details, category_backtest_metrics = backtest_demand(
        category_history,
        test_months=test_months,
        model_name=best_category_model,
    )
    category_backtest_details.to_csv(paths.category_forecast_backtest_details, index=False, encoding="utf-8-sig")
    category_backtest_metrics.to_csv(paths.category_forecast_backtest_metrics, index=False, encoding="utf-8-sig")

    forecast = forecast_demand(olist.demand_history, horizon=horizon, model_name="exp_smoothing")
    forecast.to_csv(paths.forecast, index=False, encoding="utf-8-sig")

    category_forecast = forecast_demand(category_history, horizon=horizon, model_name=best_category_model)
    category_forecast.to_csv(paths.category_forecast, index=False, encoding="utf-8-sig")

    portfolio = optimize_portfolio(olist.products, forecast, top_n=top_n)
    portfolio.to_csv(paths.portfolio, index=False, encoding="utf-8-sig")
    export_dashboard_datasets(
        olist.products,
        olist.demand_history,
        forecast,
        portfolio,
        paths.portfolio.parent,
    )

    if create_charts:
        create_eda_charts(olist.products, olist.demand_history, CHART_DIR)

    return PipelineResult(
        raw_rows=len(olist.enriched_items),
        clean_rows=len(olist.products),
        demand_rows=len(olist.demand_history),
        forecast_rows=len(forecast),
        portfolio_rows=len(portfolio),
        paths=paths,
    )
