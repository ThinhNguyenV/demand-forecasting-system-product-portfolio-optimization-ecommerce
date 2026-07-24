from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecom_forecasting.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Olist demand forecasting and portfolio optimization pipeline."
    )
    parser.add_argument("--horizon", type=int, default=6, help="Forecast horizon in months.")
    parser.add_argument("--top-n", type=int, default=30, help="Number of recommended products.")
    parser.add_argument(
        "--max-products",
        type=int,
        default=800,
        help="Top Olist products by historical revenue included in SKU-level forecasting.",
    )
    parser.add_argument(
        "--min-months",
        type=int,
        default=4,
        help="Minimum active sales months for a product before SKU-level forecasting.",
    )
    parser.add_argument(
        "--skip-charts",
        action="store_true",
        help="Skip EDA chart generation.",
    )
    args = parser.parse_args()

    result = run_pipeline(
        horizon=args.horizon,
        top_n=args.top_n,
        max_products=args.max_products,
        min_months=args.min_months,
        create_charts=not args.skip_charts,
    )

    print("Olist pipeline completed")
    print(f"Enriched order item rows: {result.raw_rows}")
    print(f"Forecasted products: {result.clean_rows}")
    print(f"Demand rows: {result.demand_rows}")
    print(f"Forecast rows: {result.forecast_rows}")
    print(f"Portfolio rows: {result.portfolio_rows}")
    print(f"Forecast file: {result.paths.forecast}")
    print(f"Portfolio file: {result.paths.portfolio}")


if __name__ == "__main__":
    main()
