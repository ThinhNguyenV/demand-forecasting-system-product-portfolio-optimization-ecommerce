from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def create_eda_charts(products: pd.DataFrame, history: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    _save_price_distribution(products, output_dir / "price_distribution.png")
    _save_revenue_by_category(history, output_dir / "revenue_by_category.png")
    _save_monthly_demand(history, output_dir / "monthly_demand.png")


def _save_price_distribution(products: pd.DataFrame, path: Path) -> None:
    plt.figure(figsize=(9, 5))
    sns.histplot(products["price"], bins=20, kde=True, color="#2563eb")
    plt.title("Price Distribution")
    plt.xlabel("Price")
    plt.ylabel("Number of products")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _save_revenue_by_category(history: pd.DataFrame, path: Path) -> None:
    revenue = (
        history.groupby("category", as_index=False)["revenue"]
        .sum()
        .sort_values("revenue", ascending=False)
        .head(12)
    )
    plt.figure(figsize=(10, 5))
    sns.barplot(data=revenue, x="revenue", y="category", color="#059669")
    plt.title("Revenue by Category")
    plt.xlabel("Revenue")
    plt.ylabel("Category")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _save_monthly_demand(history: pd.DataFrame, path: Path) -> None:
    data = history.copy()
    data["date"] = pd.to_datetime(data["date"])
    monthly = data.groupby("date", as_index=False)["quantity"].sum()
    plt.figure(figsize=(10, 5))
    sns.lineplot(data=monthly, x="date", y="quantity", marker="o", color="#dc2626")
    plt.title("Monthly Demand")
    plt.xlabel("Month")
    plt.ylabel("Quantity")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
