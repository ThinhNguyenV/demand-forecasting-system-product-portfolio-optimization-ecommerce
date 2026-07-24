from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_PRODUCT_COLUMNS = {
    "sku",
    "title",
    "category",
    "price",
    "rating",
    "in_stock",
}


def clean_products(products: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_PRODUCT_COLUMNS.difference(products.columns)
    if missing:
        raise ValueError(f"Missing required product columns: {sorted(missing)}")

    clean = products.copy()
    clean["sku"] = clean["sku"].astype(str).str.strip()
    clean["title"] = clean["title"].astype(str).str.strip()
    clean["category"] = clean["category"].fillna("Unknown").astype(str).str.strip()
    clean["price"] = pd.to_numeric(clean["price"], errors="coerce")
    clean["rating"] = pd.to_numeric(clean["rating"], errors="coerce").fillna(0)
    clean["in_stock"] = clean["in_stock"].astype(bool)
    clean = clean.dropna(subset=["sku", "title", "price"])
    clean = clean[clean["price"] > 0]
    clean = clean.drop_duplicates(subset=["sku"])
    clean["estimated_margin_rate"] = _estimate_margin_rate(clean)
    clean["demand_score"] = _estimate_demand_score(clean)
    return clean.reset_index(drop=True)


def create_demand_history(
    products: pd.DataFrame,
    months: int = 18,
    end_date: str | None = None,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Create monthly demand proxy when real order history is unavailable."""
    rng = np.random.default_rng(random_seed)
    end = pd.Timestamp(end_date) if end_date else pd.Timestamp.today().normalize()
    month_index = pd.date_range(end=end, periods=months, freq="MS")
    rows: list[dict[str, object]] = []

    for product in products.to_dict("records"):
        base = max(float(product["demand_score"]) * 35, 1)
        price = float(product["price"])
        margin_rate = float(product["estimated_margin_rate"])
        seasonal_shift = rng.uniform(0, 2 * np.pi)
        trend = rng.normal(0.01, 0.02)

        for idx, month in enumerate(month_index):
            seasonality = 1 + 0.18 * np.sin((idx / 12) * 2 * np.pi + seasonal_shift)
            growth = 1 + trend * idx
            stock_factor = 1.0 if bool(product["in_stock"]) else 0.4
            noise = rng.lognormal(mean=0, sigma=0.25)
            quantity = max(int(round(base * seasonality * growth * stock_factor * noise)), 0)
            rows.append(
                {
                    "date": month.date().isoformat(),
                    "sku": product["sku"],
                    "title": product["title"],
                    "category": product["category"],
                    "quantity": quantity,
                    "price": price,
                    "revenue": round(quantity * price, 2),
                    "gross_profit": round(quantity * price * margin_rate, 2),
                }
            )

    return pd.DataFrame(rows)


def _estimate_margin_rate(products: pd.DataFrame) -> pd.Series:
    price_rank = products["price"].rank(pct=True)
    margin = 0.18 + 0.22 * price_rank
    return margin.clip(0.12, 0.45).round(4)


def _estimate_demand_score(products: pd.DataFrame) -> pd.Series:
    price = products["price"]
    price_attractiveness = 1 - ((price - price.min()) / max(price.max() - price.min(), 1e-9))
    rating_score = products["rating"].clip(0, 5) / 5
    stock_score = products["in_stock"].astype(int)
    score = 0.45 * rating_score + 0.35 * price_attractiveness + 0.20 * stock_score
    return score.clip(0.05, 1).round(4)
