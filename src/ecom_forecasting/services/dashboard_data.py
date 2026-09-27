from __future__ import annotations

from pathlib import Path

import pandas as pd


DASHBOARD_PRODUCT_FILE = "dashboard_product_metrics.csv"
DASHBOARD_CATEGORY_FILE = "dashboard_category_metrics.csv"
DASHBOARD_MONTHLY_FILE = "dashboard_monthly_metrics.csv"


def export_dashboard_datasets(
    products: pd.DataFrame,
    history: pd.DataFrame,
    forecast: pd.DataFrame,
    portfolio: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    product_metrics = _build_product_metrics(products, history, forecast, portfolio)
    category_metrics = _build_category_metrics(products, history, forecast)
    monthly_metrics = _build_monthly_metrics(history)

    product_path = output_dir / DASHBOARD_PRODUCT_FILE
    category_path = output_dir / DASHBOARD_CATEGORY_FILE
    monthly_path = output_dir / DASHBOARD_MONTHLY_FILE

    product_metrics.to_csv(product_path, index=False, encoding="utf-8-sig")
    category_metrics.to_csv(category_path, index=False, encoding="utf-8-sig")
    monthly_metrics.to_csv(monthly_path, index=False, encoding="utf-8-sig")

    return {
        "product_metrics": product_path,
        "category_metrics": category_path,
        "monthly_metrics": monthly_path,
    }


def _build_product_metrics(
    products: pd.DataFrame,
    history: pd.DataFrame,
    forecast: pd.DataFrame,
    portfolio: pd.DataFrame,
) -> pd.DataFrame:
    history_summary = history.groupby("sku", as_index=False).agg(
        historical_quantity=("quantity", "sum"),
        historical_revenue=("revenue", "sum"),
        historical_gross_profit=("gross_profit", "sum"),
        avg_monthly_quantity_history=("quantity", "mean"),
    )
    forecast_summary = forecast.groupby("sku", as_index=False).agg(
        forecast_quantity=("forecast_quantity", "sum"),
        forecast_revenue=("forecast_revenue", "sum"),
    )
    portfolio_cols = [
        "sku",
        "expected_profit",
        "portfolio_score",
        "abc_class",
        "recommendation",
        "inventory_policy",
        "risk_flag",
        "safety_stock",
        "risk_adjusted_quantity",
        "risk_adjusted_revenue",
        "forecast_error_std",
        "uncertainty_ratio",
    ]
    available_portfolio_cols = [col for col in portfolio_cols if col in portfolio.columns]

    result = (
        products.merge(history_summary, on="sku", how="left")
        .merge(forecast_summary, on="sku", how="left")
        .merge(portfolio[available_portfolio_cols], on="sku", how="left")
    )
    numeric_cols = [
        "historical_quantity",
        "historical_revenue",
        "historical_gross_profit",
        "avg_monthly_quantity_history",
        "forecast_quantity",
        "forecast_revenue",
        "expected_profit",
        "portfolio_score",
        "safety_stock",
        "risk_adjusted_quantity",
        "risk_adjusted_revenue",
        "forecast_error_std",
        "uncertainty_ratio",
    ]
    for col in numeric_cols:
        if col in result.columns:
            result[col] = result[col].fillna(0)

    result["abc_class"] = result.get("abc_class", pd.Series(index=result.index)).fillna("Not selected")
    result["recommendation"] = result.get("recommendation", pd.Series(index=result.index)).fillna("Observe only")
    result["inventory_policy"] = result.get("inventory_policy", pd.Series(index=result.index)).fillna("No portfolio action")
    result["risk_flag"] = result.get("risk_flag", pd.Series(index=result.index)).fillna("not_selected")
    return result.sort_values("forecast_revenue", ascending=False)


def _build_category_metrics(products: pd.DataFrame, history: pd.DataFrame, forecast: pd.DataFrame) -> pd.DataFrame:
    product_summary = products.groupby("category", as_index=False).agg(
        product_count=("sku", "nunique"),
        avg_price=("price", "mean"),
        avg_rating=("rating", "mean"),
        avg_margin_rate=("estimated_margin_rate", "mean"),
    )
    history_summary = history.groupby("category", as_index=False).agg(
        historical_quantity=("quantity", "sum"),
        historical_revenue=("revenue", "sum"),
        historical_gross_profit=("gross_profit", "sum"),
    )
    forecast_summary = forecast.groupby("category", as_index=False).agg(
        forecast_quantity=("forecast_quantity", "sum"),
        forecast_revenue=("forecast_revenue", "sum"),
    )
    result = product_summary.merge(history_summary, on="category", how="left").merge(
        forecast_summary,
        on="category",
        how="left",
    )
    numeric_cols = result.select_dtypes(include="number").columns
    result[numeric_cols] = result[numeric_cols].fillna(0).round(2)
    return result.sort_values("forecast_revenue", ascending=False)


def _build_monthly_metrics(history: pd.DataFrame) -> pd.DataFrame:
    result = (
        history.groupby(["date", "category"], as_index=False)
        .agg(quantity=("quantity", "sum"), revenue=("revenue", "sum"), gross_profit=("gross_profit", "sum"))
        .sort_values(["date", "category"])
    )
    result["revenue"] = result["revenue"].round(2)
    result["gross_profit"] = result["gross_profit"].round(2)
    return result


