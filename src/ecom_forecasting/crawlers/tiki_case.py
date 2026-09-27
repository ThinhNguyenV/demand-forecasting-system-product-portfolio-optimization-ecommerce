from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests


@dataclass(frozen=True)
class TikiScrapeConfig:
    keywords: tuple[str, ...] = ("tai nghe", "ban phim", "chuot may tinh", "sac du phong")
    pages_per_keyword: int = 2
    limit: int = 40
    delay_seconds: float = 1.0
    timeout_seconds: int = 30


def crawl_tiki_snapshot(config: TikiScrapeConfig) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://tiki.vn/",
        }
    )

    for keyword in config.keywords:
        for page in range(1, config.pages_per_keyword + 1):
            response = session.get(
                "https://tiki.vn/api/v2/products",
                params={"limit": config.limit, "page": page, "q": keyword},
                timeout=config.timeout_seconds,
            )
            if response.status_code in {401, 403, 429}:
                raise RuntimeError(
                    "Tiki blocked the lightweight public request. "
                    "Use a manual CSV export or reduce crawl frequency."
                )
            response.raise_for_status()
            for item in response.json().get("data", []):
                rows.append(_parse_tiki_item(item, keyword))
            time.sleep(config.delay_seconds)

    snapshot = pd.DataFrame(rows)
    if snapshot.empty:
        return snapshot
    return snapshot.drop_duplicates(subset=["sku"]).reset_index(drop=True)


def export_tiki_portfolio_case(snapshot: pd.DataFrame, output_path: Path, top_n: int = 50) -> pd.DataFrame:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if snapshot.empty:
        snapshot.to_csv(output_path, index=False, encoding="utf-8-sig")
        return snapshot

    data = snapshot.copy()
    for col in ["price", "original_price", "rating", "review_count", "sold", "discount_rate"]:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    data["market_demand_score"] = (
        0.40 * _rank01(data["sold"])
        + 0.25 * _rank01(data["review_count"])
        + 0.20 * (data["rating"].clip(0, 5) / 5)
        + 0.15 * _rank01(data["discount_rate"])
    ).round(4)
    data["estimated_margin_rate"] = (
        0.16 + 0.10 * _rank01(data["price"]) - 0.04 * (data["discount_rate"].clip(0, 80) / 80)
    ).clip(0.08, 0.32).round(4)
    data["expected_profit_proxy"] = (data["price"] * data["sold"] * data["estimated_margin_rate"]).round(0)
    data["portfolio_score"] = (
        0.50 * data["market_demand_score"]
        + 0.30 * _rank01(data["expected_profit_proxy"])
        + 0.20 * data["official_store_score"]
    ).round(4)
    data["recommendation"] = data.apply(_recommend_tiki_action, axis=1)
    result = data.sort_values("portfolio_score", ascending=False).head(top_n)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result


def _parse_tiki_item(item: dict, keyword: str) -> dict[str, object]:
    quantity_sold = item.get("quantity_sold") or {}
    if isinstance(quantity_sold, dict):
        sold = quantity_sold.get("value", 0)
    else:
        sold = quantity_sold or 0

    product_id = item.get("id", "")
    sku = item.get("sku") or item.get("master_product_sku") or str(product_id)
    url_path = item.get("url_path") or ""
    return {
        "sku": str(sku),
        "product_id": product_id,
        "title": item.get("name", ""),
        "category": item.get("primary_category_name") or keyword,
        "keyword": keyword,
        "brand": item.get("brand_name", ""),
        "seller": item.get("seller_name", ""),
        "price": item.get("price", 0),
        "original_price": item.get("original_price", 0),
        "discount_rate": item.get("discount_rate", 0),
        "rating": item.get("rating_average", 0),
        "review_count": item.get("review_count", 0),
        "sold": sold,
        "is_authentic": bool(item.get("is_authentic", False)),
        "is_official_store": bool(item.get("is_from_official_store", False)),
        "official_store_score": 1.0 if bool(item.get("is_from_official_store", False)) else 0.0,
        "product_url": f"https://tiki.vn/{url_path}" if url_path else "https://tiki.vn/",
        "source": "Tiki Vietnam snapshot",
    }


def _rank01(series: pd.Series) -> pd.Series:
    return series.rank(pct=True).fillna(0)


def _recommend_tiki_action(row: pd.Series) -> str:
    if row["portfolio_score"] >= 0.8 and row["rating"] >= 4.5:
        return "High-priority Tiki market candidate"
    if row["market_demand_score"] >= 0.65:
        return "Monitor demand, price and discount intensity"
    return "Use as long-tail benchmark only"
