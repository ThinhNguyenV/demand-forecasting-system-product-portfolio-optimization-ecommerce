"""Data ingestion, preprocessing, time-series aggregation, and EDA utilities."""
from __future__ import annotations

from .eda import create_eda_charts
from .olist import (
    OPTIONAL_OLIST_FILES,
    REQUIRED_OLIST_FILES,
    OlistBuildResult,
    build_olist_inputs,
    missing_olist_files,
)
from .preprocessing import (
    REQUIRED_PRODUCT_COLUMNS,
    clean_products,
    create_demand_history,
)
from .time_series import (
    aggregate_enriched_items_by_category,
    aggregate_history_by_category,
)

__all__ = [
    "OPTIONAL_OLIST_FILES",
    "REQUIRED_OLIST_FILES",
    "OlistBuildResult",
    "REQUIRED_PRODUCT_COLUMNS",
    "aggregate_enriched_items_by_category",
    "aggregate_history_by_category",
    "build_olist_inputs",
    "clean_products",
    "create_demand_history",
    "create_eda_charts",
    "missing_olist_files",
]
