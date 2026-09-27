from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .forecasting import (
    _build_global_rf_training_frame,
    _encode_global_rf_features,
    _global_feature_columns,
    _global_rf_feature_row,
    _monthly_panel,
)


@dataclass
class GlobalRFExplanation:
    rows: pd.DataFrame
    feature_values: pd.DataFrame
    shap_values: np.ndarray
    base_values: np.ndarray
    feature_names: list[str]


def explain_global_random_forest(history: pd.DataFrame) -> GlobalRFExplanation:
    """Train the production-style global RF and explain each SKU's next forecast."""
    try:
        import shap
        from sklearn.ensemble import RandomForestRegressor
    except ImportError as exc:
        raise ImportError("Model explainability requires the 'shap' package.") from exc

    data = history.copy()
    data["date"] = pd.to_datetime(data["date"])
    panel = _monthly_panel(data)
    training = _build_global_rf_training_frame(panel)
    if len(training) < 20:
        raise ValueError("At least 20 monthly training observations are required for SHAP.")

    feature_names = _global_feature_columns()
    train_x, encoders = _encode_global_rf_features(training, feature_names)
    model = RandomForestRegressor(
        n_estimators=40,
        max_depth=7,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(train_x, training["target"].astype(float))

    future_rows = []
    for _, group in panel.groupby("sku", sort=False):
        ordered = group.sort_values("date").reset_index(drop=True)
        future_rows.append(_global_rf_feature_row(ordered, len(ordered), step=1))
    rows = pd.DataFrame(future_rows).reset_index(drop=True)
    feature_values, _ = _encode_global_rf_features(rows, feature_names, encoders)

    explanation = shap.TreeExplainer(model)(feature_values)
    predictions = np.maximum(model.predict(feature_values), 0)
    rows["prediction"] = predictions.tolist()
    return GlobalRFExplanation(
        rows=rows,
        feature_values=feature_values,
        shap_values=np.asarray(explanation.values),
        base_values=np.asarray(explanation.base_values),
        feature_names=feature_names,
    )


def grouped_shap_importance(
    explanation: GlobalRFExplanation,
    patterns: tuple[str, ...] = ("fast_moving", "intermittent"),
) -> pd.DataFrame:
    """Return mean absolute SHAP values by demand pattern and feature."""
    frames: list[pd.DataFrame] = []
    normalized = explanation.rows["demand_pattern"].astype(str).str.lower()
    for pattern in patterns:
        mask = normalized.eq(pattern)
        if not mask.any():
            continue
        frames.append(
            pd.DataFrame(
                {
                    "feature": explanation.feature_names,
                    "mean_abs_shap": np.abs(explanation.shap_values[mask.to_numpy()]).mean(axis=0),
                    "demand_pattern": pattern,
                    "sku_count": mask.sum(),
                }
            )
        )
    if not frames:
        return pd.DataFrame(columns=["feature", "mean_abs_shap", "demand_pattern", "sku_count"])
    return pd.concat(frames, ignore_index=True)

