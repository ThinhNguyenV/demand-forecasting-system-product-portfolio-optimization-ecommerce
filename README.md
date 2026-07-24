# Demand Forecasting System and Product Portfolio Optimization for E-commerce

Du an chuyen de tot nghiep xay dung he thong du bao nhu cau va toi uu danh muc san pham cho e-commerce.

## Chien luoc du lieu

### Dataset chinh: Olist

Olist Brazilian E-Commerce Dataset duoc dung lam dataset chinh cho forecasting vi co lich su don hang that tu 2016 den 2018. Pipeline xu ly orders, order items, products, customers, reviews, payments va sellers.

Forecasting duoc trien khai o hai muc:

- Category-level forecast: dung lam phan loi de danh gia mo hinh vi chuoi du lieu day hon.
- SKU-level forecast: dung cho portfolio optimization theo san pham.

He thong da bo sung model comparison cho category-level forecast:

- naive
- moving_average
- seasonal_naive
- simple_exp_smoothing
- exp_smoothing
- random_forest

### Dataset bo tro: Tiki

Tiki Vietnam snapshot duoc dung nhu case study ung dung tai thi truong VN. Snapshot chi la anh chup mot thoi diem, khong thay the Olist trong phan forecasting.

## Cai dat

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Tai Olist

```powershell
.\.venv\Scripts\python.exe scripts\download_olist.py
```

## Chay pipeline Olist

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline.py --horizon 6 --top-n 30 --max-products 800 --min-months 4
```

## Output du lieu

Processed:

- `data/processed/olist_order_items_enriched.csv`
- `data/processed/products_clean.csv`
- `data/processed/demand_history.csv`
- `data/processed/category_demand_history.csv`

Forecast, evaluation and optimization:

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

## Tiki snapshot optional

```powershell
.\.venv\Scripts\python.exe scripts\crawl_tiki_snapshot.py --keywords "tai nghe" "ban phim" "chuot may tinh" "sac du phong" --pages 2 --limit 40 --top-n 80
```

Neu Tiki chan request public, tao CSV theo template roi chay:

```powershell
.\.venv\Scripts\python.exe scripts\build_tiki_case_from_csv.py data\raw\tiki\your_snapshot.csv --top-n 50
```

## Chay dashboard

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

## Ket qua Olist hien tai

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

Ghi chu bao ve: SKU-level demand trong Olist rat intermittent, nen WAPE cao hon. Category-level forecast on dinh hon va nen duoc dung lam phan danh gia mo hinh chinh; SKU-level forecast phu hop hon cho ranking/portfolio decision.

## Ket qua Tiki snapshot hien tai

```text
Tiki snapshot rows: 320
Tiki portfolio case rows: 80
Tiki categories: 32
Median price: 269,000 VND
Average rating: 1.72
```
