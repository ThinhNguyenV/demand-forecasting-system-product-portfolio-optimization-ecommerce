from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from ecom_forecasting.config import CHART_DIR, PipelinePaths
from ecom_forecasting.crawlers import (
    FieldSelector,
    PublicSiteConfig,
    crawl_public_site,
    export_market_portfolio_case,
)
from ecom_forecasting.models import explain_global_random_forest, grouped_shap_importance
from ecom_forecasting.services import run_pipeline


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
public_market_case = read_csv(paths.public_market_case)
market_case = public_market_case if not public_market_case.empty else tiki_case

if products.empty or history.empty or forecast.empty or portfolio.empty:
    st.info("Olist output files are not ready yet.")
    st.stop()

metric_cols = st.columns(5)
metric_cols[0].metric("Products", f"{len(products):,}")
metric_cols[1].metric("Categories", f"{products['category'].nunique():,}")
metric_cols[2].metric("History rows", f"{len(history):,}")
metric_cols[3].metric("Forecast revenue", f"{forecast['forecast_revenue'].sum():,.0f}")
metric_cols[4].metric("Recommended SKUs", f"{len(portfolio):,}")

tab_overview, tab_forecast, tab_eval, tab_portfolio, tab_explain, tab_tiki, tab_data = st.tabs(
    ["Olist Overview", "Forecast", "Model Evaluation", "Portfolio", "Model Explainability", "Market Case", "Data"]
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

    category_revenue = history.groupby("category")["revenue"].sum().reset_index().sort_values("revenue", ascending=False).head(15)
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
        forecast_rank = forecast_source.groupby("category")["forecast_revenue"].sum().reset_index().sort_values("forecast_revenue", ascending=False).head(10)
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

with tab_explain:
    @st.cache_resource(show_spinner=False)
    def load_explanation(history_path: str, modified_ns: int):
        del modified_ns
        source = pd.read_csv(history_path)
        return explain_global_random_forest(source)

    try:
        with st.spinner("Computing SHAP values for the global Random Forest..."):
            explanation = load_explanation(str(paths.demand_history), paths.demand_history.stat().st_mtime_ns)

        selector = explanation.rows[["sku", "title", "category", "demand_pattern", "prediction"]].copy()
        selector["label"] = selector["sku"].astype(str) + " | " + selector["title"].astype(str)
        selected_label = st.selectbox("SKU", selector["label"].tolist())
        selected_idx = int(selector.index[selector["label"].eq(selected_label)][0])
        selected = selector.loc[selected_idx]

        metric_cols = st.columns(4)
        metric_cols[0].metric("RF forecast", f"{selected['prediction']:.2f}")
        metric_cols[1].metric("Demand pattern", str(selected["demand_pattern"]))
        metric_cols[2].metric("Category", str(selected["category"]))
        if "routed_model" in forecast.columns:
            routed = forecast.loc[forecast["sku"].astype(str).eq(str(selected["sku"])), "routed_model"]
        else:
            routed = pd.Series(dtype=str)
        metric_cols[3].metric("Production route", str(routed.iloc[0]) if not routed.empty else "global RF")

        import matplotlib.pyplot as plt
        import shap

        local_explanation = shap.Explanation(
            values=explanation.shap_values[selected_idx],
            base_values=explanation.base_values[selected_idx],
            data=explanation.feature_values.iloc[selected_idx].tolist(),
            feature_names=explanation.feature_names,
        )
        figure, axis = plt.subplots(figsize=(10, 5))
        shap.plots.waterfall(local_explanation, max_display=12, show=False)
        axis.set_title(f"Why the global RF predicts {selected['prediction']:.2f} units")
        st.pyplot(figure, use_container_width=True)
        plt.close(figure)

        importance = grouped_shap_importance(explanation)
        if importance.empty:
            st.info("Fast-moving and intermittent groups are not available in the current data.")
        else:
            top_features = importance.groupby("feature")["mean_abs_shap"].max().nlargest(12).index
            comparison = importance[importance["feature"].isin(top_features)]
            st.plotly_chart(
                px.bar(
                    comparison,
                    x="mean_abs_shap",
                    y="feature",
                    color="demand_pattern",
                    barmode="group",
                    orientation="h",
                    hover_data=["sku_count"],
                    title="Forecast drivers: fast-moving vs intermittent SKUs",
                ),
                use_container_width=True,
            )
    except ImportError:
        st.warning("SHAP is not installed. Run `pip install -r requirements.txt` to enable this tab.")
    except (ValueError, KeyError) as exc:
        st.warning(f"Explainability is not available for the current output: {exc}")


with tab_tiki:
    st.subheader("Public Market Scraper & Portfolio Ranking")

    with st.expander("🌐 Tự nhập Link Web / Cấu hình Crawler trực tiếp trên giao diện", expanded=market_case.empty):
        crawler_mode = st.radio(
            "Phương thức cấu hình:",
            [
                "Tùy chỉnh (Nhập link web bất kỳ)",
                "Mẫu có sẵn: Chợ Tốt (Đồ điện tử)",
                "Mẫu có sẵn: Books to Scrape",
                "Nạp từ file cấu hình JSON",
            ],
            horizontal=True,
        )

        if crawler_mode == "Nạp từ file cấu hình JSON":
            existing_configs = list(ROOT.glob("configs/*.json"))
            config_options = ["Tải lên file JSON mới..."] + [p.name for p in existing_configs]
            selected_cfg = st.selectbox("Chọn file config có sẵn hoặc tải lên mới:", config_options)

            raw_cfg = None
            if selected_cfg == "Tải lên file JSON mới...":
                uploaded_file = st.file_uploader("Upload file config JSON", type=["json"])
                if uploaded_file is not None:
                    import json
                    raw_cfg = json.load(uploaded_file)
            else:
                cfg_path = ROOT / "configs" / selected_cfg
                import json
                raw_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

            if raw_cfg:
                st.json(raw_cfg)
                if st.button("🚀 Bắt đầu Crawl từ file JSON", type="primary", use_container_width=True):
                    try:
                        with st.spinner("Đang thu thập dữ liệu theo file JSON..."):
                            import tempfile
                            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
                                import json
                                json.dump(raw_cfg, tf, ensure_ascii=False)
                                tmp_name = tf.name
                            cfg = PublicSiteConfig.from_json(tmp_name)
                            snapshot = crawl_public_site(cfg)
                            if snapshot.empty:
                                st.warning("Không tìm thấy sản phẩm nào từ cấu hình này.")
                            else:
                                export_market_portfolio_case(snapshot, paths.public_market_case, top_n=top_n)
                                st.success(f"Thu thập thành công {len(snapshot):,} sản phẩm từ '{cfg.site_name}'!")
                                st.rerun()
                    except Exception as exc:
                        st.error(f"Lỗi khi crawl: {exc}")
        else:
            if crawler_mode == "Mẫu có sẵn: Chợ Tốt (Đồ điện tử)":
                def_site_name = "Chợ Tốt"
                def_url = "https://www.chotot.com/do-dien-tu"
                def_prod_sel = "div[class*='AdItem']"
                def_title_css = "[class*='adTitle']"
                def_title_attr = ""
                def_price_css = "[class*='price']"
                def_rating_css = ""
                def_rating_attr = ""
                def_url_css = "a[href*='.htm']"
                def_category = "Đồ điện tử"
                def_engine_idx = 1
                def_pages = 1
            elif crawler_mode == "Mẫu có sẵn: Books to Scrape":
                def_site_name = "Books to Scrape"
                def_url = "https://books.toscrape.com/catalogue/page-{page}.html"
                def_prod_sel = "article.product_pod"
                def_title_css = "h3 a"
                def_title_attr = "title"
                def_price_css = ".price_color"
                def_rating_css = "p.star-rating"
                def_rating_attr = "class"
                def_url_css = "h3 a"
                def_category = "Books"
                def_engine_idx = 0
                def_pages = 2
            else:
                def_site_name = ""
                def_url = ""
                def_prod_sel = ""
                def_title_css = ""
                def_title_attr = ""
                def_price_css = ""
                def_rating_css = ""
                def_rating_attr = ""
                def_url_css = ""
                def_category = ""
                def_engine_idx = 0
                def_pages = 1

            c1, c2 = st.columns([3, 1])
            with c1:
                crawl_url = st.text_input(
                    "URL Website cần crawl (dùng {page} nếu nhiều trang) *:",
                    value=def_url,
                    placeholder="https://example.com/shop/page-{page}.html hoặc https://example.com/products",
                )
            with c2:
                crawl_site_name = st.text_input("Tên nguồn / Website:", value=def_site_name, placeholder="Tên sàn / Website")

            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                num_pages = st.number_input("Số trang crawl:", min_value=1, max_value=20, value=def_pages)
            with col_p2:
                engine_choice = st.selectbox(
                    "Engine thu thập:",
                    ["static", "playwright"],
                    index=def_engine_idx,
                    help="Static: Requests + BeautifulSoup (nhanh, cho web HTML tĩnh). Playwright: Chromium headless (bắt buộc cho web Javascript/SPA như Chợ Tốt, Shopee, v.v.)."
                )
            with col_p3:
                delay_sec = st.number_input("Độ trễ giữa các trang (giây):", min_value=0.5, max_value=10.0, value=1.0, step=0.5)

            st.caption("🔍 **Cấu hình CSS Selectors bóc tách trường thông tin:**")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                p_sel = st.text_input("Product Card Selector (Khung chứa từng sản phẩm) *:", value=def_prod_sel, placeholder="article.product_pod hoặc div[class*='AdItem']")
                t_css = st.text_input("Title Selector (Tên sản phẩm) *:", value=def_title_css, placeholder="h3 a hoặc [class*='adTitle']")
                t_attr = st.text_input("Title Attribute (để trống nếu lấy text):", value=def_title_attr, placeholder="title hoặc để trống")
                pr_css = st.text_input("Price Selector (Giá):", value=def_price_css, placeholder=".price_color hoặc [class*='price']")
            with col_s2:
                r_css = st.text_input("Rating Selector (Đánh giá):", value=def_rating_css, placeholder="p.star-rating hoặc .rating (để trống nếu web không có)")
                r_attr = st.text_input("Rating Attribute (để trống nếu lấy text):", value=def_rating_attr, placeholder="class, data-value hoặc để trống")
                u_css = st.text_input("Product Link Selector (URL chi tiết):", value=def_url_css, placeholder="h3 a hoặc a[href*='.htm']")
                cat_val = st.text_input("Category mặc định:", value=def_category, placeholder="Books, Đồ điện tử, v.v.")

            if st.button("🚀 Bắt đầu Crawl & Phân tích ngay", type="primary", use_container_width=True):
                if not crawl_url.strip() or not p_sel.strip() or not t_css.strip():
                    st.error("Vui lòng nhập đầy đủ: URL website, Product Card Selector và Title Selector!")
                else:
                    try:
                        clean_url = crawl_url.strip()
                        # Tự động làm sạch các tham số theo dõi (analytics/tracking query params)
                        if "?" in clean_url and any(k in clean_url for k in ["_ga=", "ctfp=", "event_source=", "utm_"]):
                            clean_url = clean_url.split("?")[0]

                        actual_pages = num_pages
                        if "{page}" not in clean_url and actual_pages > 1:
                            st.warning("URL không chứa biến '{page}', hệ thống tự động đặt số trang cần crawl là 1.")
                            actual_pages = 1

                        from urllib.parse import urlparse
                        netloc = urlparse(clean_url).netloc
                        clean_name = crawl_site_name.strip() or netloc or "Public website"

                        fields = {
                            "title": FieldSelector(css=t_css.strip(), attribute=t_attr.strip() or None),
                        }
                        if pr_css.strip():
                            fields["price"] = FieldSelector(css=pr_css.strip())
                        if r_css.strip():
                            fields["rating"] = FieldSelector(css=r_css.strip(), attribute=r_attr.strip() or None)
                        if u_css.strip():
                            fields["product_url"] = FieldSelector(css=u_css.strip(), attribute="href")

                        constants = {}
                        if cat_val.strip():
                            constants["category"] = cat_val.strip()

                        wait_sel = None
                        if engine_choice == "playwright":
                            wait_sel = u_css.strip() or p_sel.strip()

                        config = PublicSiteConfig(
                            site_name=clean_name,
                            page_url_template=clean_url,
                            product_selector=p_sel.strip(),
                            fields=fields,
                            pages=actual_pages,
                            start_page=1,
                            delay_seconds=float(delay_sec),
                            timeout_seconds=30,
                            constants=constants,
                            engine=engine_choice,
                            wait_selector=wait_sel,
                            wait_after_load_ms=2000 if engine_choice == "playwright" else 0,
                        )

                        try:
                            with st.spinner(f"Đang kết nối tới {clean_name} ({clean_url}) và thu thập {actual_pages} trang..."):
                                snapshot = crawl_public_site(config)
                        except ValueError as val_err:
                            if "No products matched selector" in str(val_err) and engine_choice == "static":
                                st.info("💡 Website này render nội dung bằng JavaScript (Single Page Application). Hệ thống đang tự động chuyển sang engine Playwright để thử lại...")
                                config_pw = PublicSiteConfig(
                                    site_name=clean_name,
                                    page_url_template=clean_url,
                                    product_selector=p_sel.strip(),
                                    fields=fields,
                                    pages=actual_pages,
                                    start_page=1,
                                    delay_seconds=float(delay_sec),
                                    timeout_seconds=30,
                                    constants=constants,
                                    engine="playwright",
                                    wait_selector=u_css.strip() or p_sel.strip(),
                                    wait_after_load_ms=2000,
                                )
                                with st.spinner("Đang mở trình duyệt Chromium ngầm để render nội dung JavaScript..."):
                                    snapshot = crawl_public_site(config_pw)
                            else:
                                raise val_err

                        if snapshot.empty:
                            st.warning("Đã hoàn tất crawl nhưng không tìm thấy sản phẩm nào khớp với CSS Selector. Vui lòng kiểm tra lại selector.")
                        else:
                            result_df = export_market_portfolio_case(snapshot, paths.public_market_case, top_n=top_n)
                            st.success(f"🎉 Thu thập thành công {len(snapshot):,} sản phẩm từ '{clean_name}'! Đã xếp hạng và cập nhật Top {len(result_df)} SKU vào Dashboard.")
                            st.rerun()
                    except PermissionError as pe:
                        st.error(f"❌ robots.txt của website từ chối yêu cầu crawl: {pe}")
                    except Exception as ex:
                        st.error(f"❌ Quá trình crawl thất bại: {ex}")

    st.divider()

    if market_case.empty:
        st.info("Chưa có dữ liệu snapshot thị trường. Hãy sử dụng form phía trên để bắt đầu crawl từ website công khai.")
    else:
        source_label = market_case["source"].iloc[0] if "source" in market_case.columns and not market_case["source"].empty else "Public Market"
        st.caption(f"Đang hiển thị dữ liệu thị trường từ nguồn: **{source_label}**")
        cols = st.columns(4)
        cols[0].metric("Snapshot SKUs", f"{len(market_case):,}")
        cols[1].metric("Categories", f"{market_case['category'].nunique():,}")
        cols[2].metric("Median price", f"{market_case['price'].median():,.0f}")
        cols[3].metric("Avg rating", f"{market_case['rating'].mean():.2f}")
        st.plotly_chart(
            px.scatter(
                market_case,
                x="price",
                y="sold",
                size="review_count",
                color="category",
                hover_name="title",
                hover_data=["brand", "seller", "discount_rate", "portfolio_score", "recommendation"],
                title=f"Public market snapshot: {source_label}",
            ),
            use_container_width=True,
        )
        st.dataframe(market_case, use_container_width=True, hide_index=True)

with tab_data:
    st.subheader("Olist products")
    st.dataframe(products, use_container_width=True, hide_index=True)
    st.subheader("Category demand history")
    st.dataframe(category_history, use_container_width=True, hide_index=True)
    st.subheader("SKU demand history")
    st.dataframe(history.head(1000), use_container_width=True, hide_index=True)
    st.caption(f"Static chart exports are saved in {CHART_DIR}.")
