from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing, SimpleExpSmoothing


PATTERN_ROUTED_MODEL = "pattern_routed"
GLOBAL_RANDOM_FOREST_MODEL = "random_forest_global"

SUPPORTED_MODELS = (
    "naive",
    "moving_average",
    "seasonal_naive",
    "simple_exp_smoothing",
    "exp_smoothing",
    "croston",
    "tsb",
    "random_forest",
    GLOBAL_RANDOM_FOREST_MODEL,
    PATTERN_ROUTED_MODEL,
)


def forecast_demand(
    history: pd.DataFrame,
    horizon: int = 3,
    model_name: str = "exp_smoothing",
) -> pd.DataFrame:
    required = {"date", "sku", "quantity", "price", "category", "title"}
    missing = required.difference(history.columns)
    if missing:
        raise ValueError(f"Missing required demand columns: {sorted(missing)}")

    data = history.copy()
    data["date"] = pd.to_datetime(data["date"])
    if "demand_pattern" not in data.columns:
        data["demand_pattern"] = data.groupby("sku")["quantity"].transform(_infer_demand_pattern)

    if model_name == GLOBAL_RANDOM_FOREST_MODEL:
        return _forecast_global_random_forest(data, horizon, model_label=GLOBAL_RANDOM_FOREST_MODEL)
    if model_name == PATTERN_ROUTED_MODEL:
        return _forecast_pattern_routed(data, horizon)

    forecasts: list[pd.DataFrame] = []
    for sku, group in data.groupby("sku"):
        group = group.sort_values("date")
        monthly = group.set_index("date")["quantity"].asfreq("MS").fillna(0)
        predictions = forecast_series(monthly, horizon, model_name=model_name)
        last_row = group.iloc[-1]
        future_dates = pd.date_range(
            start=monthly.index.max() + pd.offsets.MonthBegin(1),
            periods=horizon,
            freq="MS",
        )
        forecasts.append(
            pd.DataFrame(
                {
                    "date": future_dates.date.astype(str),
                    "sku": sku,
                    "title": last_row["title"],
                    "category": last_row["category"],
                    "model": model_name,
                    "demand_pattern": last_row.get("demand_pattern", _infer_demand_pattern(monthly)),
                    "forecast_quantity": np.maximum(predictions, 0).round().astype(int),
                    "price": float(last_row["price"]),
                }
            )
        )

    result = pd.concat(forecasts, ignore_index=True)
    result["forecast_revenue"] = (result["forecast_quantity"] * result["price"]).round(2)
    return result


def forecast_series(series: pd.Series, horizon: int, model_name: str = "exp_smoothing") -> np.ndarray:
    if horizon <= 0:
        return np.array([])
    clean = pd.Series(series).astype(float).replace([np.inf, -np.inf], np.nan).fillna(0)
    if clean.empty:
        return np.zeros(horizon)

    if model_name == "naive":
        return _naive(clean, horizon)
    if model_name == "moving_average":
        return _moving_average(clean, horizon)
    if model_name == "seasonal_naive":
        return _seasonal_naive(clean, horizon)
    if model_name == "simple_exp_smoothing":
        return _simple_exp_smoothing(clean, horizon)
    if model_name == "croston":
        return _croston(clean, horizon)
    if model_name == "tsb":
        return _tsb(clean, horizon)
    if model_name == "random_forest":
        return _random_forest(clean, horizon)
    if model_name == "exp_smoothing":
        return _exp_smoothing(clean, horizon)
    raise ValueError(f"Unsupported model_name: {model_name}. Choose one of {SUPPORTED_MODELS}")


def _forecast_single_series(series: pd.Series, horizon: int) -> np.ndarray:
    return forecast_series(series, horizon, model_name="exp_smoothing")


def _naive(series: pd.Series, horizon: int) -> np.ndarray:
    return np.repeat(float(series.iloc[-1]), horizon)


def _moving_average(series: pd.Series, horizon: int, window: int = 6) -> np.ndarray:
    size = min(window, max(len(series), 1))
    return np.repeat(float(series.tail(size).mean()), horizon)


def _seasonal_naive(series: pd.Series, horizon: int, season: int = 12) -> np.ndarray:
    if len(series) >= season:
        tail = series.tail(season).to_numpy(dtype=float)
        return np.array([tail[i % season] for i in range(horizon)], dtype=float)
    return _moving_average(series, horizon)


def _simple_exp_smoothing(series: pd.Series, horizon: int) -> np.ndarray:
    if len(series) >= 4 and series.sum() > 0:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fit = SimpleExpSmoothing(
                    series,
                    initialization_method="estimated",
                ).fit(optimized=True)
                return fit.forecast(horizon).to_numpy(dtype=float)
        except Exception:
            pass
    return _moving_average(series, horizon)


def _exp_smoothing(series: pd.Series, horizon: int) -> np.ndarray:
    if len(series) >= 12 and series.sum() > 0:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = ExponentialSmoothing(
                    series,
                    trend="add",
                    seasonal="add",
                    seasonal_periods=12,
                    initialization_method="estimated",
                )
                fit = model.fit(optimized=True)
                return fit.forecast(horizon).to_numpy(dtype=float)
        except Exception:
            pass
    return _moving_average(series, horizon)


def _croston(series: pd.Series, horizon: int, alpha: float = 0.1) -> np.ndarray:
    values = np.maximum(series.to_numpy(dtype=float), 0)
    demand_idx = np.flatnonzero(values > 0)
    if len(demand_idx) == 0:
        return np.zeros(horizon)
    if len(demand_idx) == 1:
        interval = max(demand_idx[0] + 1, 1)
        return np.repeat(values[demand_idx[0]] / interval, horizon)

    demand = values[demand_idx[0]]
    interval = max(demand_idx[0] + 1, 1)
    last_idx = demand_idx[0]
    for idx in demand_idx[1:]:
        observed_interval = idx - last_idx
        demand = alpha * values[idx] + (1 - alpha) * demand
        interval = alpha * observed_interval + (1 - alpha) * interval
        last_idx = idx

    forecast = demand / max(interval, 1e-9)
    return np.repeat(float(forecast), horizon)


def _tsb(series: pd.Series, horizon: int, alpha: float = 0.1, beta: float = 0.1) -> np.ndarray:
    values = np.maximum(series.to_numpy(dtype=float), 0)
    positives = values[values > 0]
    if len(positives) == 0:
        return np.zeros(horizon)

    demand_size = float(positives[0])
    demand_probability = float(values[0] > 0)
    if demand_probability == 0:
        demand_probability = min(len(positives) / max(len(values), 1), 1.0)

    for value in values:
        occurrence = 1.0 if value > 0 else 0.0
        if occurrence:
            demand_size = alpha * value + (1 - alpha) * demand_size
        demand_probability = beta * occurrence + (1 - beta) * demand_probability

    forecast = demand_probability * demand_size
    return np.repeat(float(forecast), horizon)


def _random_forest(series: pd.Series, horizon: int) -> np.ndarray:
    if len(series) < 10 or series.sum() <= 0:
        return _moving_average(series, horizon)
    try:
        from sklearn.ensemble import RandomForestRegressor
    except Exception:
        return _moving_average(series, horizon)

    values = series.to_numpy(dtype=float)
    lag_count = min(12, max(3, len(values) // 3))
    rows: list[list[float]] = []
    targets: list[float] = []
    for idx in range(1, len(values)):
        lag_values = values[max(0, idx - lag_count) : idx]
        month = int(series.index[idx].month) if hasattr(series.index[idx], "month") else idx % 12 + 1
        rows.append(
            [
                *_lag_features(values, idx),
                month,
                float(lag_values.mean()),
                float(lag_values.std()),
                float(lag_values[-3:].mean()),
                float(lag_values[-3:].std()),
                float(np.count_nonzero(lag_values == 0) / len(lag_values)),
            ]
        )
        targets.append(values[idx])

    if len(rows) < 4:
        return _moving_average(series, horizon)

    try:
        model = RandomForestRegressor(n_estimators=80, max_depth=5, random_state=42)
        model.fit(rows, targets)
        history = list(values)
        predictions = []
        next_month = series.index.max() + pd.offsets.MonthBegin(1)
        for step in range(horizon):
            history_values = np.array(history, dtype=float)
            lag_values = history_values[-lag_count:]
            month = int((next_month + pd.offsets.MonthBegin(step)).month)
            features = [
                *_lag_features(history_values, len(history_values)),
                month,
                float(lag_values.mean()),
                float(lag_values.std()),
                float(lag_values[-3:].mean()),
                float(lag_values[-3:].std()),
                float(np.count_nonzero(lag_values == 0) / len(lag_values)),
            ]
            pred = float(model.predict([features])[0])
            pred = max(pred, 0)
            predictions.append(pred)
            history.append(pred)
        return np.array(predictions, dtype=float)
    except Exception:
        return _moving_average(series, horizon)


def _forecast_pattern_routed(data: pd.DataFrame, horizon: int) -> pd.DataFrame:
    route_rows: list[dict[str, Any]] = []
    for sku, group in data.groupby("sku"):
        group = group.sort_values("date")
        monthly = group.set_index("date")["quantity"].asfreq("MS").fillna(0)
        last_row = group.iloc[-1]
        pattern = str(last_row.get("demand_pattern", _infer_demand_pattern(monthly)))
        future_dates = pd.date_range(
            start=monthly.index.max() + pd.offsets.MonthBegin(1),
            periods=horizon,
            freq="MS",
        )
        route_rows.append(
            {
                "sku": sku,
                "monthly": monthly,
                "last_row": last_row,
                "pattern": pattern,
                "model_for_sku": _route_model_for_pattern(pattern, monthly),
                "future_dates": future_dates,
            }
        )

    global_lookup: dict[tuple[Any, str], float] = {}
    if any(row["model_for_sku"] == GLOBAL_RANDOM_FOREST_MODEL for row in route_rows):
        global_forecast = _forecast_global_random_forest(data, horizon, model_label=GLOBAL_RANDOM_FOREST_MODEL)
        for _, r in global_forecast.iterrows():
            global_lookup[(r["sku"], str(r["date"]))] = float(r["forecast_quantity"])

    forecasts: list[pd.DataFrame] = []
    for route in route_rows:
        sku = route["sku"]
        monthly = route["monthly"]
        last_row = route["last_row"]
        pattern = route["pattern"]
        model_for_sku = route["model_for_sku"]
        future_dates = route["future_dates"]

        if model_for_sku == GLOBAL_RANDOM_FOREST_MODEL:
            predictions = np.array(
                [global_lookup.get((sku, date.date().isoformat()), 0.0) for date in future_dates],
                dtype=float,
            )
        else:
            predictions = forecast_series(monthly, horizon, model_name=str(model_for_sku))

        forecasts.append(
            pd.DataFrame(
                {
                    "date": future_dates.date.astype(str),
                    "sku": sku,
                    "title": last_row["title"],
                    "category": last_row["category"],
                    "model": PATTERN_ROUTED_MODEL,
                    "routed_model": model_for_sku,
                    "demand_pattern": pattern,
                    "forecast_quantity": np.maximum(predictions, 0).round().astype(int),
                    "price": float(last_row["price"]),
                }
            )
        )

    result = pd.concat(forecasts, ignore_index=True)
    result["forecast_revenue"] = (result["forecast_quantity"] * result["price"]).round(2)
    return result


def _forecast_global_random_forest(
    data: pd.DataFrame,
    horizon: int,
    model_label: str = GLOBAL_RANDOM_FOREST_MODEL,
) -> pd.DataFrame:
    def fallback_forecast() -> pd.DataFrame:
        return _forecast_with_series_model(
            data,
            horizon,
            model_name="random_forest",
            model_label=model_label,
        )

    if horizon <= 0 or data["sku"].nunique() == 0:
        return fallback_forecast().head(0).copy()

    try:
        from sklearn.ensemble import RandomForestRegressor
    except Exception:
        return fallback_forecast()

    panel = _monthly_panel(data)
    train_rows = _build_global_rf_training_frame(panel)
    if len(train_rows) < 20:
        return fallback_forecast()

    feature_cols = _global_feature_columns()
    train_x, feature_encoders = _encode_global_rf_features(train_rows, feature_cols)
    train_y = train_rows["target"].astype(float)

    try:
        model = RandomForestRegressor(
            n_estimators=40,
            max_depth=7,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(train_x, train_y)
    except Exception:
        return fallback_forecast()

    predictions: list[dict[str, object]] = []
    histories = {
        sku: group.sort_values("date").reset_index(drop=True)
        for sku, group in panel.groupby("sku", sort=False)
    }

    for step in range(1, horizon + 1):
        future_rows = []
        for sku, history in histories.items():
            row = _global_rf_feature_row(history, len(history), step=step)
            row["target"] = 0.0
            future_rows.append(row)

        future = pd.DataFrame(future_rows)
        future_x, _ = _encode_global_rf_features(future, feature_cols, feature_encoders)
        pred_values = np.maximum(model.predict(future_x), 0)

        for idx, pred in enumerate(pred_values):
            row = future.iloc[idx]
            forecast_date = pd.Timestamp(row["date"])
            predictions.append(
                {
                    "date": forecast_date.date().isoformat(),
                    "sku": row["sku"],
                    "title": row["title"],
                    "category": row["category"],
                    "model": model_label,
                    "demand_pattern": row["demand_pattern"],
                    "forecast_quantity": round(float(pred)),
                    "price": float(row["price"]),
                }
            )
            next_history_row = {
                "date": forecast_date,
                "sku": row["sku"],
                "title": row["title"],
                "category": row["category"],
                "quantity": float(pred),
                "price": float(row["price"]),
                "demand_pattern": row["demand_pattern"],
            }
            histories[row["sku"]] = pd.concat(
                [histories[row["sku"]], pd.DataFrame([next_history_row])],
                ignore_index=True,
            )

    result = pd.DataFrame(predictions)
    result["forecast_revenue"] = (result["forecast_quantity"] * result["price"]).round(2)
    return result


def _forecast_with_series_model(
    data: pd.DataFrame,
    horizon: int,
    model_name: str,
    model_label: str,
) -> pd.DataFrame:
    forecasts: list[pd.DataFrame] = []
    for sku, group in data.groupby("sku"):
        group = group.sort_values("date")
        monthly = group.set_index("date")["quantity"].asfreq("MS").fillna(0)
        predictions = forecast_series(monthly, horizon, model_name=model_name)
        last_row = group.iloc[-1]
        future_dates = pd.date_range(
            start=monthly.index.max() + pd.offsets.MonthBegin(1),
            periods=horizon,
            freq="MS",
        )
        forecasts.append(
            pd.DataFrame(
                {
                    "date": future_dates.date.astype(str),
                    "sku": sku,
                    "title": last_row["title"],
                    "category": last_row["category"],
                    "model": model_label,
                    "demand_pattern": last_row.get("demand_pattern", _infer_demand_pattern(monthly)),
                    "forecast_quantity": np.maximum(predictions, 0).round().astype(int),
                    "price": float(last_row["price"]),
                }
            )
        )
    result = pd.concat(forecasts, ignore_index=True)
    result["forecast_revenue"] = (result["forecast_quantity"] * result["price"]).round(2)
    return result


def _monthly_panel(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for sku, group in data.groupby("sku", sort=False):
        group = group.sort_values("date")
        full_index = pd.date_range(group["date"].min(), group["date"].max(), freq="MS")
        monthly = group.set_index("date").reindex(full_index)
        monthly["sku"] = sku
        monthly["quantity"] = monthly["quantity"].fillna(0)
        monthly["title"] = monthly["title"].ffill().bfill().fillna(str(sku))
        monthly["category"] = monthly["category"].ffill().bfill().fillna("unknown")
        monthly["price"] = monthly["price"].ffill().bfill().fillna(0)
        monthly["demand_pattern"] = monthly["demand_pattern"].ffill().bfill()
        monthly["demand_pattern"] = monthly["demand_pattern"].fillna(_infer_demand_pattern(monthly["quantity"]))
        rows.append(monthly.reset_index(names="date"))
    return pd.concat(rows, ignore_index=True)


def _build_global_rf_training_frame(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, group in panel.groupby("sku", sort=False):
        group = group.sort_values("date").reset_index(drop=True)
        for idx in range(1, len(group)):
            rows.append(_global_rf_feature_row(group, idx, step=0, target=float(group["quantity"].iloc[idx])))
    return pd.DataFrame(rows)


def _global_rf_feature_row(
    history: pd.DataFrame,
    idx: int,
    step: int,
    target: float | None = None,
) -> dict[str, object]:
    past = history.iloc[:idx]
    last = history.iloc[idx - 1]
    next_date = pd.Timestamp(last["date"]) + pd.offsets.MonthBegin(1 if step else 0)
    if step == 0:
        next_date = pd.Timestamp(history["date"].iloc[idx])
    quantities = past["quantity"].to_numpy(dtype=float)
    recent_3 = quantities[-3:] if len(quantities) else np.array([0.0])
    recent_6 = quantities[-6:] if len(quantities) else np.array([0.0])
    row = {
        "date": next_date,
        "sku": last["sku"],
        "title": last["title"],
        "category": last["category"],
        "demand_pattern": last.get("demand_pattern", _infer_demand_pattern(past["quantity"])),
        "price": float(last["price"]),
        "month": next_date.month,
        "quarter": next_date.quarter,
        "time_idx": idx,
        "lag_1": _lag_value(quantities, 1),
        "lag_2": _lag_value(quantities, 2),
        "lag_3": _lag_value(quantities, 3),
        "lag_12": _lag_value(quantities, 12),
        "rolling_mean_3": float(recent_3.mean()),
        "rolling_std_3": float(recent_3.std()),
        "rolling_mean_6": float(recent_6.mean()),
        "rolling_std_6": float(recent_6.std()),
        "zero_rate_6": float(np.count_nonzero(recent_6 == 0) / len(recent_6)),
        "nonzero_rate": float(np.count_nonzero(quantities > 0) / max(len(quantities), 1)),
    }
    row["target"] = float(target) if target is not None else np.nan
    return row


def _global_feature_columns() -> list[str]:
    return [
        "sku",
        "category",
        "demand_pattern",
        "price",
        "month",
        "quarter",
        "time_idx",
        "lag_1",
        "lag_2",
        "lag_3",
        "lag_12",
        "rolling_mean_3",
        "rolling_std_3",
        "rolling_mean_6",
        "rolling_std_6",
        "zero_rate_6",
        "nonzero_rate",
    ]


def _encode_global_rf_features(
    frame: pd.DataFrame,
    feature_cols: list[str],
    encoders: dict[str, dict[str, int]] | None = None,
) -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    encoded = frame[feature_cols].copy()
    fitted_encoders: dict[str, dict[str, int]] = {} if encoders is None else encoders
    for col in ["sku", "category", "demand_pattern"]:
        values = encoded[col].astype(str).fillna("unknown")
        if encoders is None:
            fitted_encoders[col] = {value: idx for idx, value in enumerate(pd.unique(values))}
        encoded[col] = values.map(fitted_encoders[col]).fillna(-1).astype(int)
    return encoded.astype(float), fitted_encoders


def _route_model_for_pattern(pattern: str, series: pd.Series) -> str:
    normalized = pattern.lower()
    zero_rate = float((series <= 0).mean()) if len(series) else 1.0
    if normalized == "fast_moving":
        return GLOBAL_RANDOM_FOREST_MODEL
    if normalized == "intermittent":
        return "tsb"
    if normalized == "slow_moving":
        return "croston" if zero_rate >= 0.45 else GLOBAL_RANDOM_FOREST_MODEL
    return "tsb" if zero_rate >= 0.6 else "exp_smoothing"


def _infer_demand_pattern(series: pd.Series) -> str:
    clean = pd.Series(series).astype(float).fillna(0)
    if clean.empty:
        return "intermittent"
    velocity = float(clean.mean())
    zero_rate = float((clean <= 0).mean())
    nonzero_months = (clean > 0).sum()
    if velocity >= 4 and zero_rate <= 0.55 and nonzero_months >= 8:
        return "fast_moving"
    if zero_rate >= 0.75 or velocity < 1.5:
        return "intermittent"
    return "slow_moving"


def _lag_features(values: Any, idx: int) -> list[float]:
    return [_lag_value(values[:idx], lag) for lag in (1, 2, 3, 12)]


def _lag_value(values: Any, lag: int) -> float:
    if len(values) >= lag:
        return float(values[-lag])
    if len(values):
        return float(values.mean())
    return 0.0


def reconcile_sku_to_category_forecast(sku_forecast: pd.DataFrame, category_forecast: pd.DataFrame) -> pd.DataFrame:
    required_sku = {"date", "sku", "category", "forecast_quantity", "price"}
    required_category = {"date", "category", "forecast_quantity"}
    missing_sku = required_sku.difference(sku_forecast.columns)
    missing_category = required_category.difference(category_forecast.columns)
    if missing_sku:
        raise ValueError(f"Missing SKU forecast columns: {sorted(missing_sku)}")
    if missing_category:
        raise ValueError(f"Missing category forecast columns: {sorted(missing_category)}")

    result = sku_forecast.copy()
    targets = category_forecast[["date", "category", "forecast_quantity"]].rename(
        columns={"forecast_quantity": "category_target_forecast_quantity"}
    )
    result = result.merge(targets, on=["date", "category"], how="left")
    result["category_target_forecast_quantity"] = result["category_target_forecast_quantity"].fillna(
        result.groupby(["date", "category"])["forecast_quantity"].transform("sum")
    )
    result["pre_reconciliation_forecast_quantity"] = result["forecast_quantity"]
    reconciled_groups = [
        _reconcile_group(group)
        for _, group in result.groupby(["date", "category"], sort=False)
    ]
    result = pd.concat(reconciled_groups, ignore_index=True) if reconciled_groups else result.head(0).copy()
    result["forecast_revenue"] = (result["forecast_quantity"] * result["price"]).round(2)
    return result.reset_index(drop=True)


def _reconcile_group(group: pd.DataFrame) -> pd.DataFrame:
    adjusted = group.copy()
    target = round(float(adjusted["category_target_forecast_quantity"].iloc[0]))
    current = float(adjusted["forecast_quantity"].sum())
    if target < 0:
        target = 0

    if len(adjusted) == 0:
        return adjusted
    if current <= 0:
        base = np.zeros(len(adjusted), dtype=int)
        if target > 0:
            base[:] = target // len(adjusted)
            base[: target % len(adjusted)] += 1
        adjusted["forecast_quantity"] = base.tolist()
        adjusted["reconciliation_factor"] = 0.0 if target == 0 else np.nan
        return adjusted

    scaled = adjusted["forecast_quantity"].astype(float) * (target / current)
    floored = np.floor(scaled).astype(int)
    remainder = target - int(floored.sum())
    if remainder > 0:
        order = (scaled - floored).sort_values(ascending=False).index[:remainder]
        floored.loc[order] += 1
    adjusted["forecast_quantity"] = floored.clip(lower=0).astype(int)
    adjusted["reconciliation_factor"] = round(target / current, 6)
    return adjusted