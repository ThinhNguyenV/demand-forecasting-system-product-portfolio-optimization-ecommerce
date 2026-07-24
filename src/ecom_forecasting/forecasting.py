from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing, SimpleExpSmoothing


SUPPORTED_MODELS = (
    "naive",
    "moving_average",
    "seasonal_naive",
    "simple_exp_smoothing",
    "exp_smoothing",
    "random_forest",
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
    forecasts: list[pd.DataFrame] = []

    for sku, group in data.groupby("sku"):
        group = group.sort_values("date")
        monthly = (
            group.set_index("date")["quantity"]
            .asfreq("MS")
            .interpolate()
            .bfill()
            .ffill()
        )
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


def _random_forest(series: pd.Series, horizon: int) -> np.ndarray:
    if len(series) < 10 or series.sum() <= 0:
        return _moving_average(series, horizon)
    try:
        from sklearn.ensemble import RandomForestRegressor
    except Exception:
        return _moving_average(series, horizon)

    values = series.to_numpy(dtype=float)
    lag_count = min(6, max(2, len(values) // 3))
    rows: list[list[float]] = []
    targets: list[float] = []
    for idx in range(lag_count, len(values)):
        lag_values = values[idx - lag_count : idx]
        month = int(series.index[idx].month) if hasattr(series.index[idx], "month") else idx % 12 + 1
        rows.append([*lag_values, month, np.mean(lag_values), np.std(lag_values)])
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
            lag_values = np.array(history[-lag_count:], dtype=float)
            month = int((next_month + pd.offsets.MonthBegin(step)).month)
            features = [*lag_values, month, float(np.mean(lag_values)), float(np.std(lag_values))]
            pred = float(model.predict([features])[0])
            pred = max(pred, 0)
            predictions.append(pred)
            history.append(pred)
        return np.array(predictions, dtype=float)
    except Exception:
        return _moving_average(series, horizon)
