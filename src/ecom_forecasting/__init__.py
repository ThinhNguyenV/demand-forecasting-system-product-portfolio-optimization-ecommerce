"""E-commerce demand forecasting and portfolio optimization package.

Modular Subpackage Architecture:
- data: Data ingestion (Olist), cleaning, feature extraction, EDA
- models: Demand forecasting (statistical, ML, routing, reconciliation, SHAP)
- optimization: Portfolio and safety stock optimization
- crawlers: Public market crawlers and scrapers
- services: End-to-end pipeline orchestration and dashboard reporting
"""
from __future__ import annotations

from . import crawlers, data, models, optimization, services
from .config import (
    CHART_DIR,
    DATA_DIR,
    OLIST_RAW_DIR,
    OUTPUT_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    TIKI_RAW_DIR,
    PipelinePaths,
    ensure_directories,
)
from .services.pipeline import PipelineResult, run_pipeline

__all__ = [
    "CHART_DIR",
    "DATA_DIR",
    "OLIST_RAW_DIR",
    "OUTPUT_DIR",
    "PROCESSED_DIR",
    "RAW_DIR",
    "TIKI_RAW_DIR",
    "PipelinePaths",
    "PipelineResult",
    "crawlers",
    "data",
    "ensure_directories",
    "models",
    "optimization",
    "run_pipeline",
    "services",
]
