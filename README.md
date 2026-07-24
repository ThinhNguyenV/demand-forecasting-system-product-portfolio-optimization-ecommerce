# Demand Forecasting and Product Portfolio Optimization for E-commerce

Hệ thống dự báo nhu cầu và tối ưu danh mục sản phẩm cho thương mại điện tử. Dự án xử lý dữ liệu đơn hàng, tạo chuỗi nhu cầu theo tháng, benchmark mô hình dự báo, đề xuất danh mục SKU ưu tiên và trực quan hóa kết quả bằng Streamlit dashboard.

## Điểm chính

- Dùng **Olist Brazilian E-Commerce Dataset** làm dữ liệu chính cho forecasting vì có lịch sử đơn hàng thật từ 2016 đến 2018.
- Dự báo ở hai mức: category-level để đánh giá mô hình và SKU-level để hỗ trợ portfolio optimization.
- Benchmark 6 mô hình forecast: `naive`, `moving_average`, `seasonal_naive`, `simple_exp_smoothing`, `exp_smoothing`, `random_forest`.
- Phân loại nhu cầu SKU thành `fast_moving`, `slow_moving`, `intermittent` để hỗ trợ chính sách tồn kho.
- Dùng **Tiki Vietnam snapshot** như case study bổ trợ cho thị trường Việt Nam, không dùng để validate forecasting nếu chỉ có một snapshot.

## Cấu trúc dự án

```text
.
├── app.py
├── requirements.txt
├── README.md
├── data/
│   ├── raw/
│   ├── processed/
│   └── outputs/
├── docs/
├── scripts/
├── src/ecom_forecasting/
└── tests/
```

## Tài liệu

Các tài liệu chi tiết nằm trong [docs/README.md](docs/README.md):

- [Chiến lược dữ liệu](docs/data_strategy.md)
- [Thiết kế hệ thống](docs/system_design.md)
- [Đánh giá mô hình](docs/model_evaluation.md)
- [Dashboard data dictionary](docs/dashboard_data_dictionary.md)

## Cài đặt

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Tải dữ liệu Olist

```powershell
.\.venv\Scripts\python.exe scripts\download_olist.py
```

Dữ liệu Olist sau khi tải nằm ở `data/raw/olist/`.

## Chạy pipeline Olist

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline.py --horizon 6 --top-n 30 --max-products 800 --min-months 4
```

Pipeline sẽ tạo dữ liệu processed, forecast, model evaluation, portfolio recommendations và dataset phục vụ dashboard.

## Chạy dashboard

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

## Tiki snapshot optional

Có thể crawl snapshot public từ Tiki để minh họa case study Việt Nam:

```powershell
.\.venv\Scripts\python.exe scripts\crawl_tiki_snapshot.py --keywords "tai nghe" "ban phim" "chuot may tinh" "sac du phong" --pages 2 --limit 40 --top-n 80
```

Nếu request public bị chặn, tạo CSV theo template `data/raw/tiki/tiki_snapshot_template.csv`, rồi chạy:

```powershell
.\.venv\Scripts\python.exe scripts\build_tiki_case_from_csv.py data\raw\tiki\your_snapshot.csv --top-n 50
```

## Output chính

Processed:

- `data/processed/olist_order_items_enriched.csv`
- `data/processed/products_clean.csv`
- `data/processed/demand_history.csv`
- `data/processed/category_demand_history.csv`

Forecast, evaluation và optimization:

- `data/outputs/forecast.csv`
- `data/outputs/category_forecast.csv`
- `data/outputs/model_comparison_details.csv`
- `data/outputs/model_comparison_metrics.csv`
- `data/outputs/forecast_backtest_metrics.csv`
- `data/outputs/category_forecast_backtest_metrics.csv`
- `data/outputs/portfolio_recommendations.csv`

Dashboard-ready:

- `data/outputs/dashboard_product_metrics.csv`
- `data/outputs/dashboard_category_metrics.csv`
- `data/outputs/dashboard_monthly_metrics.csv`

Tiki case study:

- `data/raw/tiki/tiki_snapshot_template.csv`
- `data/raw/tiki_snapshot.csv`
- `data/outputs/tiki_portfolio_case.csv`

## Kết quả hiện tại

```text
Olist enriched order item rows: 110,197
Forecasted SKU products: 800
SKU portfolio categories: 50
SKU demand history rows: 18,400
Category demand history rows: 1,273
SKU forecast rows: 4,800
Category forecast rows: 444
Portfolio recommendations: 30
Best category model: simple_exp_smoothing
Best category-level WAPE: 22.68%
SKU-level WAPE with exp_smoothing: 140.73%
Demand pattern mix: 93 fast_moving, 430 slow_moving, 277 intermittent
```

Ghi chú: SKU-level demand trong Olist có tính intermittent cao, nên WAPE cao hơn category-level. Vì vậy, category-level forecast phù hợp để đánh giá mô hình chính, còn SKU-level forecast phù hợp hơn cho ranking và portfolio decision.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest
```
