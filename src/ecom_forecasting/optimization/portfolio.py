from __future__ import annotations

import numpy as np
import pandas as pd


def optimize_portfolio(
    products: pd.DataFrame,
    forecast: pd.DataFrame,
    top_n: int = 20,
    max_category_share: float = 0.4,
    backtest_metrics: pd.DataFrame | None = None,
    service_level_z: float = 1.65,
) -> pd.DataFrame:
    required_products = {"sku", "title", "category", "price", "estimated_margin_rate"}
    required_forecast = {"sku", "forecast_quantity", "forecast_revenue"}
    missing_products = required_products.difference(products.columns)
    missing_forecast = required_forecast.difference(forecast.columns)
    if missing_products:
        raise ValueError(f"Missing product columns: {sorted(missing_products)}")
    if missing_forecast:
        raise ValueError(f"Missing forecast columns: {sorted(missing_forecast)}")

    forecast_summary = forecast.groupby("sku", as_index=False).agg(
        forecast_quantity=("forecast_quantity", "sum"),
        forecast_revenue=("forecast_revenue", "sum"),
        forecast_months=("date", "nunique") if "date" in forecast.columns else ("forecast_quantity", "count"),
    )
    portfolio = products.merge(forecast_summary, on="sku", how="left").fillna(
        {"forecast_quantity": 0, "forecast_revenue": 0, "forecast_months": 0}
    )
    if "demand_pattern" not in portfolio.columns:
        portfolio["demand_pattern"] = "unclassified"

    portfolio = _attach_forecast_uncertainty(portfolio, backtest_metrics, service_level_z=service_level_z)
    portfolio["expected_profit"] = (portfolio["forecast_revenue"] * portfolio["estimated_margin_rate"]).round(2)
    portfolio["risk_adjusted_revenue"] = (portfolio["risk_adjusted_quantity"] * portfolio["price"]).round(2)
    portfolio["revenue_rank_pct"] = portfolio["forecast_revenue"].rank(pct=True)
    portfolio["profit_rank_pct"] = portfolio["expected_profit"].rank(pct=True)
    portfolio["demand_rank_pct"] = portfolio["risk_adjusted_quantity"].rank(pct=True)
    portfolio["uncertainty_score"] = 1 - portfolio["uncertainty_ratio"].rank(pct=True).fillna(0)
    portfolio["pattern_score"] = portfolio["demand_pattern"].map(
        {"fast_moving": 1.0, "slow_moving": 0.65, "intermittent": 0.35}
    ).fillna(0.5)
    portfolio["portfolio_score"] = (
        0.30 * portfolio["profit_rank_pct"]
        + 0.25 * portfolio["demand_rank_pct"]
        + 0.20 * portfolio["revenue_rank_pct"]
        + 0.15 * portfolio["pattern_score"]
        + 0.10 * portfolio["uncertainty_score"]
    ).round(4)
    portfolio["abc_class"] = _abc_class(portfolio["forecast_revenue"])

    selected = _select_with_category_cap(
        portfolio.sort_values("portfolio_score", ascending=False),
        top_n=top_n,
        max_category_share=max_category_share,
    )
    selected["recommendation"] = selected.apply(_recommend_action, axis=1)
    selected["inventory_policy"] = selected.apply(_inventory_policy, axis=1)
    selected["risk_flag"] = selected.apply(_risk_flag, axis=1)
    return selected.reset_index(drop=True)


def _attach_forecast_uncertainty(
    portfolio: pd.DataFrame,
    backtest_metrics: pd.DataFrame | None,
    service_level_z: float,
) -> pd.DataFrame:
    result = portfolio.copy()
    result["forecast_error_std"] = 0.0
    if backtest_metrics is not None and not backtest_metrics.empty and {"sku", "error_std"}.issubset(backtest_metrics.columns):
        uncertainty = backtest_metrics[
            ~backtest_metrics["sku"].astype(str).str.startswith("__")
        ][["sku", "error_std"]].copy()
        uncertainty["error_std"] = pd.to_numeric(uncertainty["error_std"], errors="coerce").fillna(0)
        uncertainty = uncertainty.groupby("sku", as_index=False)["error_std"].mean()
        result = result.drop(columns=["forecast_error_std"]).merge(uncertainty, on="sku", how="left")
        result = result.rename(columns={"error_std": "forecast_error_std"})
        result["forecast_error_std"] = result["forecast_error_std"].fillna(0)

    horizon_scale = np.sqrt(result["forecast_months"].clip(lower=1))
    result["safety_stock"] = np.ceil(service_level_z * result["forecast_error_std"] * horizon_scale).astype(int)
    result["risk_adjusted_quantity"] = result["forecast_quantity"] + result["safety_stock"]
    denominator = result["forecast_quantity"].replace(0, np.nan)
    result["uncertainty_ratio"] = (result["safety_stock"] / denominator).replace([np.inf, -np.inf], np.nan).fillna(0)
    result["uncertainty_ratio"] = result["uncertainty_ratio"].clip(0, 5).round(4)
    return result


def _abc_class(revenue: pd.Series) -> pd.Series:
    total = revenue.sum()
    if total <= 0:
        return pd.Series(["C"] * len(revenue), index=revenue.index)

    cumulative = revenue.sort_values(ascending=False).cumsum() / total
    classes = pd.Series(index=revenue.sort_values(ascending=False).index, dtype="object")
    classes.loc[cumulative <= 0.8] = "A"
    classes.loc[(cumulative > 0.8) & (cumulative <= 0.95)] = "B"
    classes.loc[cumulative > 0.95] = "C"
    return classes.reindex(revenue.index).fillna("A")


def _select_with_category_cap(ranked: pd.DataFrame, top_n: int, max_category_share: float) -> pd.DataFrame:
    if top_n <= 0:
        return ranked.head(0).copy()
    if ranked["category"].nunique() <= 1:
        return ranked.head(top_n).copy()

    cap = max(1, int(round(top_n * max_category_share)))
    selected_rows = []
    counts: dict[str, int] = {}

    for _, row in ranked.iterrows():
        category = str(row["category"])
        if counts.get(category, 0) >= cap:
            continue
        selected_rows.append(row)
        counts[category] = counts.get(category, 0) + 1
        if len(selected_rows) >= top_n:
            break

    return pd.DataFrame(selected_rows)


def _recommend_action(row: pd.Series) -> str:
    pattern = row.get("demand_pattern", "unclassified")
    if row["abc_class"] == "A" and pattern == "fast_moving":
        return "Prioritize inventory and promotion"
    if row["abc_class"] in {"A", "B"} and pattern == "slow_moving":
        return "Maintain, monitor velocity and avoid overstock"
    if pattern == "intermittent":
        return "Limit stock, use bundle or campaign tests"
    return "Maintain and monitor demand"


def _inventory_policy(row: pd.Series) -> str:
    pattern = row.get("demand_pattern", "unclassified")
    safety_stock = int(row.get("safety_stock", 0))
    if pattern == "fast_moving" and row["abc_class"] == "A":
        return f"Replenish frequently with {safety_stock} units safety stock"
    if pattern == "intermittent":
        return f"Keep lean stock; cap buffer near {safety_stock} units"
    return f"Review monthly with {safety_stock} units safety buffer"


def _risk_flag(row: pd.Series) -> str:
    if row.get("uncertainty_ratio", 0) >= 1.0 and row.get("safety_stock", 0) > 0:
        return "high_forecast_uncertainty"
    if row.get("demand_pattern") == "intermittent" and row["forecast_quantity"] <= 3:
        return "high_intermittent_demand_risk"
    if row["estimated_margin_rate"] < 0.15:
        return "low_margin_risk"
    return "normal"
