# Thiết Kế Hệ Thống

## 1. Mục tiêu hệ thống

Hệ thống được xây dựng để xử lý dữ liệu thương mại điện tử, dự báo nhu cầu và đề xuất danh mục sản phẩm ưu tiên. Thiết kế hiện tại tách rõ hai vai trò dữ liệu:

- **Olist** là pipeline chính cho forecasting vì có lịch sử đơn hàng thật theo thời gian.
- **Tiki snapshot** là case study bổ trợ cho thị trường Việt Nam, dùng để minh họa portfolio scoring từ dữ liệu thị trường tại một thời điểm.

## 2. Luồng xử lý tổng quát

### Pipeline chính: Olist

```text
Olist raw CSV
  -> Join orders, order items, products, reviews, customers
  -> Filter delivered orders
  -> Enriched order item transactions
  -> Monthly SKU demand history
  -> Monthly category demand history
  -> Forecast model benchmark at category-level
  -> SKU-level forecast
  -> Portfolio optimization
  -> Dashboard datasets and charts
```

### Pipeline bổ trợ: Tiki case study

```text
Tiki public snapshot or manual CSV
  -> Normalize product fields
  -> Estimate market demand proxy
  -> Rank product candidates
  -> Export dashboard case-study dataset
```

## 3. Thành phần hệ thống

### Olist Data Builder

Module: `src/ecom_forecasting/data/olist.py`

Nhiệm vụ:

- Đọc các CSV Olist trong `data/raw/olist/`.
- Join orders, order items, products, category translation, reviews và customers.
- Lọc đơn hàng `delivered`.
- Tạo bảng giao dịch enriched, bảng sản phẩm sạch và monthly SKU demand history.
- Tạo các biến hỗ trợ business scoring như `estimated_margin_rate`, `demand_score`, `active_months`, `avg_monthly_quantity`, `zero_month_rate` và `demand_pattern`.

### Time-Series Aggregation

Module: `src/ecom_forecasting/data/time_series.py`

Nhiệm vụ:

- Tổng hợp enriched order items thành category-level monthly demand history.
- Chuẩn hóa input để category forecast và model evaluation dùng cùng cấu trúc dữ liệu với SKU forecast.

### Forecasting

Module: `src/ecom_forecasting/models/forecasting.py`

Nhiệm vụ:

- Chuẩn hóa chuỗi thời gian theo tháng.
- Dự báo nhu cầu bằng các mô hình như naive, moving average, seasonal naive, exponential smoothing và random forest.
- Xuất `forecast_quantity` và `forecast_revenue` cho SKU hoặc category.

### Model Evaluation

Module: `src/ecom_forecasting/models/evaluation.py`

Nhiệm vụ:

- Backtest theo time split.
- Benchmark nhiều mô hình trên category-level demand history.
- Tính MAE, RMSE, WAPE và bias.
- Chọn mô hình category-level tốt nhất theo overall WAPE.

### Portfolio Optimization

Module: `src/ecom_forecasting/optimization/portfolio.py`

Nhiệm vụ:

- Tổng hợp forecast theo SKU.
- Tính lợi nhuận kỳ vọng.
- Phân lớp ABC.
- Tính `portfolio_score`.
- Gắn `inventory_policy`, `risk_flag` và đề xuất hành động danh mục.
- Chọn top sản phẩm với ràng buộc tỷ trọng category để tránh danh mục bị lệch.

### Dashboard Data Export

Module: `src/ecom_forecasting/services/dashboard_data.py`

Nhiệm vụ:

- Xuất các bảng dashboard-ready ở `data/outputs/`.
- Chuẩn bị metric theo product, category và month để Streamlit đọc nhanh.

### Tiki Case Study

Module: `src/ecom_forecasting/crawlers/tiki_case.py`

Scripts:

- `scripts/crawl_tiki_snapshot.py`
- `scripts/build_tiki_case_from_csv.py`

Nhiệm vụ:

- Chuẩn hóa dữ liệu snapshot Tiki hoặc CSV thủ công.
- Tính demand proxy từ sold, review count, rating, discount và price.
- Xuất `data/outputs/tiki_portfolio_case.csv` cho dashboard.

### Dashboard

File: `app.py`

Nhiệm vụ:

- Hiển thị KPI tổng quan.
- Hiển thị forecast, model evaluation, portfolio map và ranking table.
- Cho phép xem dữ liệu Olist pipeline và Tiki case study trong cùng một giao diện.

## 4. Mô hình dữ liệu chính

### Product

| Trường | Ý nghĩa |
| --- | --- |
| `sku` | Mã sản phẩm, dùng `product_id` của Olist |
| `title` | Tên hiển thị tạo từ category |
| `category` | Danh mục sản phẩm |
| `price` | Giá bán trung bình |
| `rating` | Điểm đánh giá trung bình |
| `estimated_margin_rate` | Biên lợi nhuận proxy |
| `demand_score` | Điểm nhu cầu proxy từ lịch sử bán, doanh thu và rating |
| `historical_quantity` | Tổng số sản phẩm bán được trong lịch sử |
| `historical_revenue` | Tổng doanh thu lịch sử |
| `active_months` | Số tháng có phát sinh bán |
| `demand_pattern` | Nhóm nhu cầu: `fast_moving`, `slow_moving`, `intermittent` |

### Demand History

| Trường | Ý nghĩa |
| --- | --- |
| `date` | Tháng ghi nhận |
| `sku` | Mã sản phẩm hoặc mã category khi aggregate |
| `title` | Tên hiển thị |
| `category` | Danh mục |
| `quantity` | Số order items trong tháng |
| `price` | Giá trung bình trong tháng |
| `revenue` | Doanh thu tháng |
| `gross_profit` | Lợi nhuận gộp proxy |

### Forecast

| Trường | Ý nghĩa |
| --- | --- |
| `date` | Tháng dự báo |
| `sku` | Mã sản phẩm hoặc mã category |
| `title` | Tên hiển thị |
| `category` | Danh mục |
| `forecast_quantity` | Số lượng dự báo |
| `price` | Giá dùng để quy đổi doanh thu |
| `forecast_revenue` | Doanh thu dự báo |

### Portfolio Recommendation

| Trường | Ý nghĩa |
| --- | --- |
| `forecast_quantity` | Tổng nhu cầu dự báo trong horizon |
| `forecast_revenue` | Tổng doanh thu dự báo |
| `expected_profit` | Lợi nhuận kỳ vọng |
| `portfolio_score` | Điểm ưu tiên danh mục |
| `abc_class` | Nhóm A/B/C theo đóng góp kinh doanh |
| `inventory_policy` | Gợi ý chính sách tồn kho |
| `risk_flag` | Cảnh báo rủi ro |
| `recommendation` | Hành động đề xuất |

## 5. Output chính

| Nhóm | File |
| --- | --- |
| Processed | `data/processed/olist_order_items_enriched.csv` |
| Processed | `data/processed/products_clean.csv` |
| Processed | `data/processed/demand_history.csv` |
| Processed | `data/processed/category_demand_history.csv` |
| Forecast | `data/outputs/forecast.csv` |
| Forecast | `data/outputs/category_forecast.csv` |
| Evaluation | `data/outputs/model_comparison_metrics.csv` |
| Evaluation | `data/outputs/model_comparison_details.csv` |
| Evaluation | `data/outputs/forecast_backtest_metrics.csv` |
| Evaluation | `data/outputs/category_forecast_backtest_metrics.csv` |
| Portfolio | `data/outputs/portfolio_recommendations.csv` |
| Dashboard | `data/outputs/dashboard_product_metrics.csv` |
| Dashboard | `data/outputs/dashboard_category_metrics.csv` |
| Dashboard | `data/outputs/dashboard_monthly_metrics.csv` |
| Tiki case study | `data/outputs/tiki_portfolio_case.csv` |

## 6. Tiêu chí đánh giá

- Pipeline Olist chạy được từ raw CSV đến dashboard outputs.
- Dữ liệu sau xử lý không thiếu các cột quan trọng.
- Category-level benchmark có nhiều mô hình và metrics rõ ràng.
- SKU-level forecast tạo được dữ liệu phục vụ portfolio scoring.
- Danh mục đề xuất có lý do kinh doanh qua ABC class, demand pattern, inventory policy và risk flag.
- Dashboard hỗ trợ quan sát KPI, forecast, model evaluation và portfolio decision.

## 7. Rủi ro và giới hạn

- Olist là dữ liệu Brazil giai đoạn 2016-2018, nên cần giải thích rõ khi liên hệ với thị trường Việt Nam.
- SKU-level demand trong Olist rất thưa và gián đoạn, khiến sai số forecast cao hơn category-level.
- Biên lợi nhuận, tồn kho và nhu cầu thị trường hiện là proxy, chưa thay thế dữ liệu vận hành thật.
- Tiki snapshot chỉ là ảnh chụp một thời điểm, không đủ để forecast theo thời gian.
- Nếu crawl dữ liệu public, cần tuân thủ điều khoản sử dụng, `robots.txt` và giới hạn tần suất request.
