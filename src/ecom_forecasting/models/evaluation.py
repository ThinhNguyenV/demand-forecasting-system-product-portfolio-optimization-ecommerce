from __future__ import annotations

import numpy as np
import pandas as pd

from .forecasting import GLOBAL_RANDOM_FOREST_MODEL, PATTERN_ROUTED_MODEL, SUPPORTED_MODELS, forecast_demand, forecast_series


def backtest_demand(
    history: pd.DataFrame,
    test_months: int = 3,
    model_name: str = "exp_smoothing",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    details = _backtest_details(history, test_months=test_months, model_name=model_name)
    if details.empty:
        return details, pd.DataFrame()
    metrics = summarize_backtest(details)
    return details, metrics


def benchmark_forecast_models(
    history: pd.DataFrame,
    test_months: int = 3,
    model_names: tuple[str, ...] = SUPPORTED_MODELS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_details = [
        _backtest_details(history, test_months=test_months, model_name=model_name)
        for model_name in model_names
    ]
    details = pd.concat([item for item in all_details if not item.empty], ignore_index=True)
    if details.empty:
        return details, pd.DataFrame()

    metrics = pd.concat(
        [
            summarize_backtest(group).assign(model=model_name)
            for model_name, group in details.groupby("model")
        ],
        ignore_index=True,
    )
    ordered_cols = ["model", *[col for col in metrics.columns if col != "model"]]
    return details, metrics[ordered_cols]


def best_model_from_metrics(metrics: pd.DataFrame) -> str:
    if metrics.empty or "model" not in metrics.columns:
        return "exp_smoothing"
    overall = metrics[metrics["sku"].eq("__OVERALL__")].copy()
    if overall.empty:
        return "exp_smoothing"
    overall = overall.sort_values(["wape", "rmse", "mae"], ascending=True)
    return str(overall.iloc[0]["model"])


def summarize_backtest(details: pd.DataFrame) -> pd.DataFrame:
    sku_metrics = _metrics(details, ["sku", "title", "category"])
    category_metrics = _metrics(details, ["category"])
    category_metrics.insert(0, "sku", "__CATEGORY__")
    category_metrics.insert(1, "title", category_metrics["category"])
    overall = _metrics(
        details.assign(category="__OVERALL__", sku="__OVERALL__", title="Overall"),
        ["sku", "title", "category"],
    )
    return pd.concat([overall, category_metrics, sku_metrics], ignore_index=True)


def _backtest_details(history: pd.DataFrame, test_months: int, model_name: str) -> pd.DataFrame:
    required = {"date", "sku", "quantity", "category", "title"}
    missing = required.difference(history.columns)
    if missing:
        raise ValueError(f"Missing required demand columns: {sorted(missing)}")
    if model_name in {GLOBAL_RANDOM_FOREST_MODEL, PATTERN_ROUTED_MODEL}:
        return _panel_backtest_details(history, test_months=test_months, model_name=model_name)

    rows: list[dict[str, object]] = []
    data = history.copy()
    data["date"] = pd.to_datetime(data["date"])

    for sku, group in data.groupby("sku"):
        group = group.sort_values("date")
        monthly = group.set_index("date")["quantity"].asfreq("MS").fillna(0)
        if len(monthly) <= test_months + 3:
            continue

        train = monthly.iloc[:-test_months]
        actual = monthly.iloc[-test_months:]
        pred = np.maximum(forecast_series(train, test_months, model_name=model_name), 0)
        last_row = group.iloc[-1]
        routed_model = model_name

        for date, actual_value, pred_value in zip(actual.index, actual.to_numpy(), pred):
            row = {
                "model": model_name,
                "date": date.date().isoformat(),
                "sku": sku,
                "title": last_row["title"],
                "category": last_row["category"],
                "actual_quantity": float(actual_value),
                "predicted_quantity": float(pred_value),
                "error": float(pred_value - actual_value),
                "absolute_error": float(abs(pred_value - actual_value)),
                "squared_error": float((pred_value - actual_value) ** 2),
            }
            if "demand_pattern" in group.columns:
                row["demand_pattern"] = last_row.get("demand_pattern", "unclassified")
            row["routed_model"] = routed_model
            rows.append(row)

    return pd.DataFrame(rows)


def _panel_backtest_details(history: pd.DataFrame, test_months: int, model_name: str) -> pd.DataFrame:
    data = history.copy()
    data["date"] = pd.to_datetime(data["date"])
    cutoff_dates = sorted(data["date"].dropna().unique())
    if len(cutoff_dates) <= test_months + 3:
        return pd.DataFrame()

    test_dates = pd.to_datetime(cutoff_dates[-test_months:])
    train = data[data["date"].lt(test_dates.min())].copy()
    actual = data[data["date"].isin(test_dates)].copy()
    if train.empty or actual.empty:
        return pd.DataFrame()

    forecast = forecast_demand(train, horizon=test_months, model_name=model_name)
    forecast["date"] = pd.to_datetime(forecast["date"])
    merged = actual.merge(
        forecast,
        on=["sku", "date"],
        how="inner",
        suffixes=("_actual", "_forecast"),
    )
    if merged.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for row in merged.itertuples(index=False):
        actual_value = float(row.quantity)
        pred_value = float(row.forecast_quantity)
        error = pred_value - actual_value
        item = {
            "model": model_name,
            "date": pd.Timestamp(row.date).date().isoformat(),
            "sku": row.sku,
            "title": getattr(row, "title_actual", getattr(row, "title_forecast", row.sku)),
            "category": getattr(row, "category_actual", getattr(row, "category_forecast", "unknown")),
            "actual_quantity": actual_value,
            "predicted_quantity": pred_value,
            "error": error,
            "absolute_error": abs(error),
            "squared_error": error**2,
        }
        demand_pattern = getattr(row, "demand_pattern_forecast", None)
        if demand_pattern is None and hasattr(row, "demand_pattern_actual"):
            demand_pattern = getattr(row, "demand_pattern_actual")
        if demand_pattern is not None:
            item["demand_pattern"] = demand_pattern
        routed_model = getattr(row, "routed_model", None)
        if routed_model is not None:
            item["routed_model"] = routed_model
        rows.append(item)
    return pd.DataFrame(rows)


def _metrics(details: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    grouped = details.groupby(group_cols, as_index=False).agg(
        observations=("actual_quantity", "count"),
        actual_quantity=("actual_quantity", "sum"),
        predicted_quantity=("predicted_quantity", "sum"),
        mae=("absolute_error", "mean"),
        mse=("squared_error", "mean"),
        bias=("error", "mean"),
        error_std=("error", "std"),
    )
    grouped["rmse"] = np.sqrt(grouped["mse"])
    grouped["wape"] = grouped["mae"] * grouped["observations"] / grouped["actual_quantity"].replace(0, np.nan)
    grouped["wape"] = grouped["wape"].fillna(0)
    grouped["error_std"] = grouped["error_std"].fillna(0)
    grouped["mae"] = grouped["mae"].round(4)
    grouped["rmse"] = grouped["rmse"].round(4)
    grouped["bias"] = grouped["bias"].round(4)
    grouped["error_std"] = grouped["error_std"].round(4)
    grouped["wape"] = grouped["wape"].round(4)
    grouped["actual_quantity"] = grouped["actual_quantity"].round(4)
    grouped["predicted_quantity"] = grouped["predicted_quantity"].round(4)
    return grouped.drop(columns=["mse"])
