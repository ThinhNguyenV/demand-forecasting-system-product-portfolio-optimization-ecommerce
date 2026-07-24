from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from ecom_forecasting.config import CHART_DIR, PipelinePaths
from ecom_forecasting.pipeline import run_pipeline


st.set_page_config(page_title="Olist Demand Forecasting", layout="wide")
paths = PipelinePaths()

st.title("Demand Forecasting and Product Portfolio Optimization")
st.caption("Forecasting core: Olist category/SKU history. VN application case: Tiki snapshot.")

with st.sidebar:
    st.header("Olist Pipeline")
    horizon = st.slider("Forecast horizon", min_value=1, max_value=12, value=6)
    top_n = st.slider("Portfolio size", min_value=10, max_value=100, value=30)
    max_products = st.slider("Forecasted products", min_value=100, max_value=2000, value=800, step=100)
    min_months = st.slider("Minimum active months", min_value=1, max_value=12, value=4)
    run_button = st.button("Run Olist pipeline", type="primary")

if run_button:
    with st.spinner("Processing Olist orders, benchmarking models and optimizing portfolio..."):
        result = run_pipeline(horizon=horizon, top_n=top_n, max_products=max_products, min_months=min_months)
    st.success(
        f"Completed: {result.raw_rows:,} order-item rows, "
        f"{result.clean_rows:,} products, {result.forecast_rows:,} SKU forecast rows."
    )


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


products = read_csv(paths.clean_products)
history = read_csv(paths.demand_history)
category_history = read_csv(paths.category_demand_history)
forecast = read_csv(paths.forecast)
category_forecast = read_csv(paths.category_forecast)
portfolio = read_csv(paths.portfolio)
sku_metrics = read_csv(paths.forecast_backtest_metrics)
category_metrics = read_csv(paths.category_forecast_backtest_metrics)
model_metrics = read_csv(paths.model_comparison_metrics)
model_details = read_csv(paths.model_comparison_details)
tiki_case = read_csv(paths.tiki_portfolio_case)

if products.empty or history.empty or forecast.empty or portfolio.empty:
    st.info("Olist output files are not ready yet.")
    st.stop()

metric_cols = st.columns(5)
metric_cols[0].metric("Products", f"{len(products):,}")
metric_cols[1].metric("Categories", f"{products['category'].nunique():,}")
metric_cols[2].metric("History rows", f"{len(history):,}")
metric_cols[3].metric("Forecast revenue", f"{forecast['forecast_revenue'].sum():,.0f}")
metric_cols[4].metric("Recommended SKUs", f"{len(portfolio):,}")

tab_overview, tab_forecast, tab_eval, tab_portfolio, tab_tiki, tab_data = st.tabs(
    ["Olist Overview", "Forecast", "Model Evaluation", "Portfolio", "Tiki Case", "Data"]
)

with tab_overview:
    col_a, col_b = st.columns(2)
    with col_a:
        monthly = history.copy()
        monthly["date"] = pd.to_datetime(monthly["date"])
        monthly_total = monthly.groupby("date", as_index=False).agg(
            revenue=("revenue", "sum"),
            gross_profit=("gross_profit", "sum"),
        )
        st.plotly_chart(
            px.line(monthly_total, x="date", y=["revenue", "gross_profit"], markers=True, title="Monthly revenue and gross profit"),
            use_container_width=True,
        )
    with col_b:
        pattern_counts = products["demand_pattern"].value_counts().reset_index()
        pattern_counts.columns = ["demand_pattern", "products"]
        st.plotly_chart(
            px.bar(pattern_counts, x="demand_pattern", y="products", title="SKU demand pattern mix", color="demand_pattern"),
            use_container_width=True,
        )

    category_revenue = history.groupby("category", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False).head(15)
    st.plotly_chart(
        px.bar(category_revenue, x="revenue", y="category", orientation="h", title="Top categories by historical revenue", color_discrete_sequence=["#059669"]),
        use_container_width=True,
    )

with tab_forecast:
    if not category_metrics.empty:
        overall = category_metrics[category_metrics["sku"].eq("__OVERALL__")]
        if not overall.empty:
            row = overall.iloc[0]
            metric_a, metric_b, metric_c, metric_d = st.columns(4)
            metric_a.metric("Category MAE", f"{row['mae']:.2f}")
            metric_b.metric("Category RMSE", f"{row['rmse']:.2f}")
            metric_c.metric("Category WAPE", f"{row['wape']:.2%}")
            metric_d.metric("Category Bias", f"{row['bias']:.2f}")

    forecast_source = category_forecast if not category_forecast.empty else forecast
    col_a, col_b = st.columns([2, 1])
    with col_a:
        forecast_view = forecast_source.sort_values("date")
        top_categories = forecast_source.groupby("category")["forecast_revenue"].sum().sort_values(ascending=False).head(10).index
        forecast_view = forecast_view[forecast_view["category"].isin(top_categories)]
        st.plotly_chart(
            px.line(forecast_view, x="date", y="forecast_quantity", color="category", markers=True, title="Category-level demand forecast"),
            use_container_width=True,
        )
    with col_b:
        forecast_rank = forecast_source.groupby("category", as_index=False)["forecast_revenue"].sum().sort_values("forecast_revenue", ascending=False).head(10)
        st.dataframe(forecast_rank, use_container_width=True, hide_index=True)

    st.dataframe(forecast.sort_values("forecast_revenue", ascending=False).head(300), use_container_width=True, hide_index=True)

with tab_eval:
    if model_metrics.empty:
        st.info("Model comparison output is not available yet. Run the Olist pipeline.")
    else:
        overall_models = model_metrics[model_metrics["sku"].eq("__OVERALL__")].sort_values("wape")
        best_model = str(overall_models.iloc[0]["model"])
        cols = st.columns(4)
        cols[0].metric("Best model", best_model)
        cols[1].metric("Best WAPE", f"{overall_models.iloc[0]['wape']:.2%}")
        cols[2].metric("Best MAE", f"{overall_models.iloc[0]['mae']:.2f}")
        cols[3].metric("Best RMSE", f"{overall_models.iloc[0]['rmse']:.2f}")

        st.plotly_chart(
            px.bar(overall_models, x="model", y="wape", title="Category-level model comparison by WAPE", color="model"),
            use_container_width=True,
        )

        category_rows = model_metrics[(model_metrics["model"].eq(best_model)) & (model_metrics["sku"].eq("__CATEGORY__"))]
        st.plotly_chart(
            px.bar(
                category_rows.sort_values("wape", ascending=False).head(20),
                x="wape",
                y="category",
                orientation="h",
                title="Worst category-level WAPE for selected model",
                color_discrete_sequence=["#dc2626"],
            ),
            use_container_width=True,
        )

        details = model_details[model_details["model"].eq(best_model)].copy()
        if not details.empty:
            top_categories = details.groupby("category")["actual_quantity"].sum().sort_values(ascending=False).head(8).index
            details = details[details["category"].isin(top_categories)]
            melted = details.melt(
                id_vars=["date", "category", "model"],
                value_vars=["actual_quantity", "predicted_quantity"],
                var_name="series",
                value_name="quantity",
            )
            st.plotly_chart(
                px.line(melted, x="date", y="quantity", color="category", line_dash="series", markers=True, title="Actual vs predicted demand by category"),
                use_container_width=True,
            )

        st.dataframe(overall_models, use_container_width=True, hide_index=True)
        if not sku_metrics.empty:
            st.dataframe(
                sku_metrics[sku_metrics["sku"].ne("__OVERALL__")].sort_values("wape", ascending=True).head(100),
                use_container_width=True,
                hide_index=True,
            )

with tab_portfolio:
    st.plotly_chart(
        px.scatter(
            portfolio,
            x="forecast_revenue",
            y="expected_profit",
            size="forecast_quantity",
            color="demand_pattern" if "demand_pattern" in portfolio.columns else "abc_class",
            symbol="abc_class",
            hover_name="title",
            hover_data=["sku", "category", "portfolio_score", "recommendation", "inventory_policy", "risk_flag"],
            title="Olist SKU portfolio priority map",
        ),
        use_container_width=True,
    )
    st.dataframe(portfolio, use_container_width=True, hide_index=True)

with tab_tiki:
    if tiki_case.empty:
        st.info("Tiki snapshot output is not available yet. Run scripts/crawl_tiki_snapshot.py to create it.")
    else:
        cols = st.columns(4)
        cols[0].metric("Snapshot SKUs", f"{len(tiki_case):,}")
        cols[1].metric("Categories", f"{tiki_case['category'].nunique():,}")
        cols[2].metric("Median price", f"{tiki_case['price'].median():,.0f}")
        cols[3].metric("Avg rating", f"{tiki_case['rating'].mean():.2f}")
        st.plotly_chart(
            px.scatter(
                tiki_case,
                x="price",
                y="sold",
                size="review_count",
                color="category",
                hover_name="title",
                hover_data=["brand", "seller", "discount_rate", "portfolio_score", "recommendation"],
                title="Tiki VN market snapshot",
            ),
            use_container_width=True,
        )
        st.dataframe(tiki_case, use_container_width=True, hide_index=True)

with tab_data:
    st.subheader("Olist products")
    st.dataframe(products, use_container_width=True, hide_index=True)
    st.subheader("Category demand history")
    st.dataframe(category_history, use_container_width=True, hide_index=True)
    st.subheader("SKU demand history")
    st.dataframe(history.head(1000), use_container_width=True, hide_index=True)
    st.caption(f"Static chart exports are saved in {CHART_DIR}.")
