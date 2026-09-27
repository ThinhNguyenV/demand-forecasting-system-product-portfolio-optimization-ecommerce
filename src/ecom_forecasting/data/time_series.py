from __future__ import annotations

import pandas as pd


def aggregate_history_by_category(history: pd.DataFrame) -> pd.DataFrame:
    data = history.copy()
    data["date"] = pd.to_datetime(data["date"])
    grouped = (
        data.groupby(["date", "category"], as_index=False)
        .agg(
            quantity=("quantity", "sum"),
            revenue=("revenue", "sum"),
            gross_profit=("gross_profit", "sum"),
        )
        .sort_values(["category", "date"])
    )
    return _finalize_category_history(grouped)


def aggregate_enriched_items_by_category(enriched_items: pd.DataFrame) -> pd.DataFrame:
    data = enriched_items.copy()
    data["date"] = pd.to_datetime(data["date"])
    grouped = (
        data.groupby(["date", "category"], as_index=False)
        .agg(
            quantity=("order_id", "count"),
            revenue=("revenue", "sum"),
        )
        .sort_values(["category", "date"])
    )
    grouped["gross_profit"] = grouped["revenue"] * 0.25
    return _finalize_category_history(grouped)


def _finalize_category_history(grouped: pd.DataFrame) -> pd.DataFrame:
    grouped["sku"] = grouped["category"]
    grouped["title"] = grouped["category"]
    grouped["price"] = grouped["revenue"] / grouped["quantity"].replace(0, pd.NA)
    grouped["price"] = grouped.groupby("category")["price"].ffill().bfill().fillna(0)
    grouped["date"] = grouped["date"].dt.date.astype(str)
    grouped["revenue"] = grouped["revenue"].round(2)
    grouped["gross_profit"] = grouped["gross_profit"].round(2)
    grouped["price"] = grouped["price"].round(2)
    return grouped[["date", "sku", "title", "category", "quantity", "price", "revenue", "gross_profit"]]
