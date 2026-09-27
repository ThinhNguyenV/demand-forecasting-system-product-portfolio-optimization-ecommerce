from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OLIST_RAW_DIR = RAW_DIR / "olist"
TIKI_RAW_DIR = RAW_DIR / "tiki"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "outputs"
CHART_DIR = OUTPUT_DIR / "charts"


@dataclass(frozen=True)
class PipelinePaths:
    raw_products: Path = RAW_DIR / "products_raw.csv"
    clean_products: Path = PROCESSED_DIR / "products_clean.csv"
    demand_history: Path = PROCESSED_DIR / "demand_history.csv"
    category_demand_history: Path = PROCESSED_DIR / "category_demand_history.csv"
    olist_order_items: Path = PROCESSED_DIR / "olist_order_items_enriched.csv"
    tiki_snapshot: Path = RAW_DIR / "tiki_snapshot.csv"
    public_market_snapshot: Path = RAW_DIR / "public_market_snapshot.csv"
    forecast: Path = OUTPUT_DIR / "forecast.csv"
    category_forecast: Path = OUTPUT_DIR / "category_forecast.csv"
    forecast_backtest_details: Path = OUTPUT_DIR / "forecast_backtest_details.csv"
    forecast_backtest_metrics: Path = OUTPUT_DIR / "forecast_backtest_metrics.csv"
    category_forecast_backtest_details: Path = OUTPUT_DIR / "category_forecast_backtest_details.csv"
    category_forecast_backtest_metrics: Path = OUTPUT_DIR / "category_forecast_backtest_metrics.csv"
    model_comparison_details: Path = OUTPUT_DIR / "model_comparison_details.csv"
    model_comparison_metrics: Path = OUTPUT_DIR / "model_comparison_metrics.csv"
    portfolio: Path = OUTPUT_DIR / "portfolio_recommendations.csv"
    tiki_portfolio_case: Path = OUTPUT_DIR / "tiki_portfolio_case.csv"
    public_market_case: Path = OUTPUT_DIR / "public_market_case.csv"


def ensure_directories() -> None:
    for directory in [RAW_DIR, OLIST_RAW_DIR, TIKI_RAW_DIR, PROCESSED_DIR, OUTPUT_DIR, CHART_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
