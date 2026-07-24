from __future__ import annotations

import sys
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecom_forecasting.config import OLIST_RAW_DIR, ensure_directories


BASE_URL = "https://huggingface.co/datasets/miminmoons/olist-ecommerce-for-delivery-and-review-prediction"
FILES = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_products_dataset.csv",
    "product_category_name_translation.csv",
    "olist_customers_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_sellers_dataset.csv",
]


def download_file(filename: str) -> Path:
    ensure_directories()
    target = OLIST_RAW_DIR / filename
    if target.exists() and target.stat().st_size > 0:
        print(f"skip existing: {target}")
        return target

    url = f"{BASE_URL}/{filename}?download=true"
    print(f"download: {filename}")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    print(f"saved: {target} ({target.stat().st_size:,} bytes)")
    return target


def main() -> None:
    for filename in FILES:
        download_file(filename)
    print("Olist data is ready in", OLIST_RAW_DIR)


if __name__ == "__main__":
    main()
