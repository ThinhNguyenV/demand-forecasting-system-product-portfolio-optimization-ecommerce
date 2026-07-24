from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import OLIST_RAW_DIR


REQUIRED_OLIST_FILES = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "products": "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

OPTIONAL_OLIST_FILES = {
    "customers": "olist_customers_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
}


@dataclass(frozen=True)
class OlistBuildResult:
    products: pd.DataFrame
    demand_history: pd.DataFrame
    enriched_items: pd.DataFrame


def missing_olist_files(raw_dir: Path = OLIST_RAW_DIR) -> list[str]:
    return [name for name in REQUIRED_OLIST_FILES.values() if not (raw_dir / name).exists()]


def build_olist_inputs(
    raw_dir: Path = OLIST_RAW_DIR,
    max_products: int = 800,
    min_months: int = 4,
) -> OlistBuildResult:
    missing = missing_olist_files(raw_dir)
    if missing:
        raise FileNotFoundError(
            "Missing Olist files in "
            f"{raw_dir}: {missing}. Run scripts/download_olist.py or place Kaggle CSV files there."
        )

    tables = _load_olist_tables(raw_dir)
    enriched = _build_enriched_items(tables)
    products = _build_product_table(enriched, max_products=max_products, min_months=min_months)
    demand_history = _build_monthly_demand(enriched, products)
    return OlistBuildResult(products=products, demand_history=demand_history, enriched_items=enriched)


def _load_olist_tables(raw_dir: Path) -> dict[str, pd.DataFrame]:
    tables = {key: pd.read_csv(raw_dir / filename) for key, filename in REQUIRED_OLIST_FILES.items()}
    for key, filename in OPTIONAL_OLIST_FILES.items():
        path = raw_dir / filename
        if path.exists():
            tables[key] = pd.read_csv(path)
    return tables


def _build_enriched_items(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    orders = tables["orders"].copy()
    items = tables["items"].copy()
    products = tables["products"].copy()
    categories = tables["category_translation"].copy()

    orders["order_purchase_timestamp"] = pd.to_datetime(orders["order_purchase_timestamp"], errors="coerce")
    orders = orders[orders["order_status"].eq("delivered")]
    orders = orders.dropna(subset=["order_purchase_timestamp"])

    products = products.merge(categories, on="product_category_name", how="left")
    products["category"] = products["product_category_name_english"].fillna(products["product_category_name"])
    products["category"] = products["category"].fillna("unknown").astype(str)

    enriched = (
        items.merge(
            orders[
                [
                    "order_id",
                    "customer_id",
                    "order_purchase_timestamp",
                    "order_estimated_delivery_date",
                ]
            ],
            on="order_id",
            how="inner",
        )
        .merge(
            products[
                [
                    "product_id",
                    "category",
                    "product_name_lenght",
                    "product_description_lenght",
                    "product_photos_qty",
                    "product_weight_g",
                    "product_length_cm",
                    "product_height_cm",
                    "product_width_cm",
                ]
            ],
            on="product_id",
            how="left",
        )
    )

    if "reviews" in tables:
        reviews = tables["reviews"][["order_id", "review_score"]].copy()
        reviews = reviews.groupby("order_id", as_index=False)["review_score"].mean()
        enriched = enriched.merge(reviews, on="order_id", how="left")
    else:
        enriched["review_score"] = np.nan

    if "customers" in tables:
        customers = tables["customers"][["customer_id", "customer_city", "customer_state"]].copy()
        enriched = enriched.merge(customers, on="customer_id", how="left")
    else:
        enriched["customer_city"] = "unknown"
        enriched["customer_state"] = "unknown"

    enriched["price"] = pd.to_numeric(enriched["price"], errors="coerce")
    enriched["freight_value"] = pd.to_numeric(enriched["freight_value"], errors="coerce").fillna(0)
    enriched = enriched.dropna(subset=["product_id", "price", "order_purchase_timestamp"])
    enriched = enriched[enriched["price"] > 0]
    enriched["date"] = enriched["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    enriched["revenue"] = enriched["price"]
    return enriched


def _build_product_table(enriched: pd.DataFrame, max_products: int, min_months: int) -> pd.DataFrame:
    total_months = max(enriched["date"].nunique(), 1)
    product_months = enriched.groupby("product_id")["date"].nunique().rename("active_months")
    summary = (
        enriched.groupby("product_id", as_index=False)
        .agg(
            title=("category", _product_title),
            category=("category", _mode_or_unknown),
            price=("price", "mean"),
            rating=("review_score", "mean"),
            historical_quantity=("order_id", "count"),
            historical_revenue=("revenue", "sum"),
            avg_freight_value=("freight_value", "mean"),
            sellers=("seller_id", "nunique"),
        )
        .merge(product_months, on="product_id", how="left")
    )
    eligible = summary[summary["active_months"].ge(min_months)].copy()
    if eligible.empty:
        eligible = summary.copy()

    eligible = eligible.sort_values("historical_revenue", ascending=False).head(max_products)
    eligible["sku"] = eligible["product_id"]
    eligible["rating"] = eligible["rating"].fillna(eligible["rating"].median()).fillna(3.0).round(2)
    eligible["in_stock"] = True
    eligible["estimated_margin_rate"] = _estimate_margin_rate(eligible)
    eligible["demand_score"] = _estimate_demand_score(eligible)
    eligible["avg_monthly_quantity"] = (
        eligible["historical_quantity"] / eligible["active_months"].replace(0, 1)
    ).round(2)
    eligible["zero_month_rate"] = (1 - eligible["active_months"] / total_months).clip(0, 1).round(4)
    eligible["demand_pattern"] = eligible.apply(_classify_demand_pattern, axis=1)
    return eligible[
        [
            "sku",
            "title",
            "category",
            "price",
            "rating",
            "in_stock",
            "estimated_margin_rate",
            "demand_score",
            "historical_quantity",
            "historical_revenue",
            "active_months",
            "avg_monthly_quantity",
            "zero_month_rate",
            "demand_pattern",
            "avg_freight_value",
            "sellers",
        ]
    ].reset_index(drop=True)


def _build_monthly_demand(enriched: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    selected = enriched[enriched["product_id"].isin(products["sku"])].copy()
    margin_lookup = products.set_index("sku")["estimated_margin_rate"]
    title_lookup = products.set_index("sku")["title"]
    category_lookup = products.set_index("sku")["category"]

    monthly = (
        selected.groupby(["product_id", "date"], as_index=False)
        .agg(quantity=("order_id", "count"), price=("price", "mean"), revenue=("revenue", "sum"))
        .rename(columns={"product_id": "sku"})
    )

    complete_rows = []
    full_index = pd.date_range(monthly["date"].min(), monthly["date"].max(), freq="MS")
    for sku, group in monthly.groupby("sku"):
        group = group.set_index("date").sort_index()
        group = group.reindex(full_index)
        group["sku"] = sku
        group["quantity"] = group["quantity"].fillna(0).astype(int)
        default_price = float(products.loc[products["sku"].eq(sku), "price"].iloc[0])
        group["price"] = group["price"].ffill().bfill().fillna(default_price)
        group["revenue"] = group["revenue"].fillna(0)
        group["title"] = title_lookup.get(sku, sku)
        group["category"] = category_lookup.get(sku, "unknown")
        group["gross_profit"] = group["revenue"] * float(margin_lookup.get(sku, 0.25))
        complete_rows.append(group.reset_index(names="date"))

    result = pd.concat(complete_rows, ignore_index=True)
    result["date"] = pd.to_datetime(result["date"]).dt.date.astype(str)
    result["price"] = result["price"].round(2)
    result["revenue"] = result["revenue"].round(2)
    result["gross_profit"] = result["gross_profit"].round(2)
    return result[["date", "sku", "title", "category", "quantity", "price", "revenue", "gross_profit"]]


def _estimate_margin_rate(products: pd.DataFrame) -> pd.Series:
    price_rank = products["price"].rank(pct=True)
    freight_burden = (products["avg_freight_value"] / products["price"].clip(lower=1)).clip(0, 0.6)
    margin = 0.32 + 0.16 * price_rank - 0.18 * freight_burden
    return margin.clip(0.08, 0.48).round(4)


def _estimate_demand_score(products: pd.DataFrame) -> pd.Series:
    qty = products["historical_quantity"]
    revenue = products["historical_revenue"]
    months = products["active_months"].replace(0, 1)
    velocity = qty / months
    score = 0.45 * _rank01(velocity) + 0.35 * _rank01(revenue) + 0.20 * (products["rating"].clip(1, 5) / 5)
    return score.clip(0.05, 1).round(4)


def _classify_demand_pattern(row: pd.Series) -> str:
    velocity = float(row.get("avg_monthly_quantity", 0))
    zero_month_rate = float(row.get("zero_month_rate", 1))
    active_months = float(row.get("active_months", 0))
    if velocity >= 4 and zero_month_rate <= 0.55 and active_months >= 8:
        return "fast_moving"
    if zero_month_rate >= 0.75 or velocity < 1.5:
        return "intermittent"
    return "slow_moving"


def _rank01(series: pd.Series) -> pd.Series:
    return series.rank(pct=True).fillna(0)


def _mode_or_unknown(series: pd.Series) -> str:
    mode = series.dropna().mode()
    return str(mode.iloc[0]) if not mode.empty else "unknown"


def _product_title(series: pd.Series) -> str:
    category = _mode_or_unknown(series)
    return f"Olist product - {category}"
