# Dashboard Data Dictionary

Tài liệu này mô tả các file dữ liệu được pipeline tạo ra và cách dashboard sử dụng chúng. Xem thêm [thiết kế hệ thống](system_design.md) để hiểu luồng xử lý tổng thể.

## 1. Olist Raw Data

Folder: `data/raw/olist/`

Nguồn dữ liệu chính cho forecasting. Các file quan trọng:

- `olist_orders_dataset.csv`: order id, customer id, status, purchase timestamp, delivery dates.
- `olist_order_items_dataset.csv`: order item id, product id, seller id, price, freight value.
- `olist_products_dataset.csv`: product category and product attributes.
- `product_category_name_translation.csv`: Portuguese category to English category.
- `olist_customers_dataset.csv`: customer city/state.
- `olist_order_reviews_dataset.csv`: review score.
- `olist_order_payments_dataset.csv`: payment type/value.
- `olist_sellers_dataset.csv`: seller location.

## 2. Enriched Olist Order Items

File: `data/processed/olist_order_items_enriched.csv`

Bảng giao dịch đã join và lọc delivered orders. Đây là bảng nền cho EDA và tạo demand history.

Cột chính:

- `order_id`, `product_id`, `seller_id`, `customer_id`
- `order_purchase_timestamp`
- `date`: tháng mua hàng.
- `category`: category English.
- `price`, `freight_value`, `revenue`
- `review_score`
- `customer_city`, `customer_state`

## 3. Clean Product Data

File: `data/processed/products_clean.csv`

Bảng sản phẩm top theo doanh thu lịch sử, đã sẵn sàng cho portfolio optimization.

Cột chính:

- `sku`: product id Olist.
- `title`: tên hiển thị tạo từ category.
- `category`: danh mục English.
- `price`: giá trung bình.
- `rating`: review score trung bình.
- `estimated_margin_rate`: biên lợi nhuận proxy.
- `demand_score`: điểm nhu cầu proxy từ lịch sử bán, doanh thu và rating.
- `historical_quantity`, `historical_revenue`, `active_months`.
- `avg_monthly_quantity`, `zero_month_rate`, `demand_pattern`.

## 4. Demand History

File: `data/processed/demand_history.csv`

Lịch sử nhu cầu hàng tháng theo SKU từ Olist delivered orders.

Cột chính:

- `date`: tháng.
- `sku`, `title`, `category`.
- `quantity`: số order items trong tháng.
- `price`: giá trung bình trong tháng.
- `revenue`: tổng doanh thu sản phẩm.
- `gross_profit`: lợi nhuận gộp proxy.

## 5. Category Demand History

File: `data/processed/category_demand_history.csv`

Lịch sử nhu cầu hàng tháng theo category. File này dùng cho benchmark mô hình và category-level forecast vì chuỗi category ổn định hơn chuỗi SKU.

## 6. Forecast Data

Files:

- `data/outputs/forecast.csv`: SKU-level forecast.
- `data/outputs/category_forecast.csv`: category-level forecast dùng best model theo benchmark.

Cột chính:

- `date`: tháng dự báo.
- `sku`, `title`, `category`.
- `forecast_quantity`.
- `price`.
- `forecast_revenue`.

## 7. Portfolio Recommendations

File: `data/outputs/portfolio_recommendations.csv`

Danh sách SKU ưu tiên dựa trên forecast và scoring.

Cột chính:

- `forecast_quantity`
- `forecast_revenue`
- `expected_profit`
- `portfolio_score`
- `abc_class`
- `demand_pattern`
- `inventory_policy`
- `risk_flag`
- `recommendation`

## 8. Dashboard Product Metrics

File: `data/outputs/dashboard_product_metrics.csv`

Bảng tổng hợp cấp SKU cho scatter plot, ranking table và product drilldown.

## 9. Dashboard Category Metrics

File: `data/outputs/dashboard_category_metrics.csv`

Bảng tổng hợp cấp danh mục cho bar chart/KPI theo category.

## 10. Dashboard Monthly Metrics

File: `data/outputs/dashboard_monthly_metrics.csv`

Bảng tổng hợp theo tháng và category cho line chart/time-series dashboard.

## 11. Tiki Snapshot Case

Files:

- `data/raw/tiki_snapshot.csv`
- `data/outputs/tiki_portfolio_case.csv`
- `data/raw/tiki/tiki_snapshot_template.csv`

Tiki snapshot chỉ dùng để minh họa thị trường Việt Nam và portfolio optimization proxy. Không dùng để validate forecasting nếu chỉ có một snapshot.

## 12. Model Comparison

Files:

- `data/outputs/model_comparison_details.csv`
- `data/outputs/model_comparison_metrics.csv`

Dùng để đánh giá nhiều mô hình forecast ở category-level.

Cột chính trong metrics:

- `model`: tên mô hình.
- `sku`, `title`, `category`: mức tổng hợp. `__OVERALL__` là dòng tổng thể.
- `observations`: số điểm test.
- `actual_quantity`: tổng actual demand.
- `predicted_quantity`: tổng predicted demand.
- `mae`: mean absolute error.
- `rmse`: root mean squared error.
- `wape`: weighted absolute percentage error.
- `bias`: sai lệch trung bình.

## 13. Demand Pattern and Portfolio Actions

Các cột mới trong `products_clean.csv`, `dashboard_product_metrics.csv` và `portfolio_recommendations.csv`:

- `avg_monthly_quantity`: tốc độ bán trung bình trong các tháng có bán.
- `zero_month_rate`: tỷ lệ tháng không có doanh số.
- `demand_pattern`: `fast_moving`, `slow_moving`, hoặc `intermittent`.
- `inventory_policy`: đề xuất chính sách tồn kho.
- `risk_flag`: cảnh báo rủi ro portfolio.

Cách dùng dashboard:

- Dùng `Model Evaluation` để so sánh mô hình và xem actual vs predicted.
- Dùng `Portfolio` để xem sản phẩm theo demand pattern, ABC class và risk flag.
