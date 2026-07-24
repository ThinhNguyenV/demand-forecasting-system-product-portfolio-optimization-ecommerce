# Data Strategy: Olist Forecasting Core and Tiki VN Case Study

## 1. Vai trò của từng nguồn dữ liệu

### Olist là dataset chính

Olist Brazilian E-Commerce Dataset được dùng làm dataset chính cho forecasting vì có lịch sử giao dịch thật trong giai đoạn 2016-2018. Các bảng dữ liệu có quan hệ rõ ràng: orders, order items, products, customers, payments, reviews và sellers.

Olist phù hợp để bảo vệ phần lõi kỹ thuật vì:

- Có timestamp mua hàng thật.
- Có nhiều SKU và danh mục.
- Có order status để lọc đơn `delivered`.
- Có giá bán, phí vận chuyển và review score.
- Có đủ lịch sử theo tháng để backtest forecast.

### Tiki là case study bổ trợ

Tiki Vietnam snapshot được dùng cho phần thảo luận ứng dụng tại Việt Nam. Snapshot này không thay thế Olist trong forecasting vì chỉ là ảnh chụp một thời điểm, không có lịch sử bán hàng theo tháng.

## 2. Pipeline Olist

```text
Olist raw CSV
  -> Join orders/items/products/reviews/customers
  -> Filter delivered orders
  -> Monthly SKU and category demand history
  -> Backtest category forecast for core model evaluation
  -> Forecast SKU demand for product-level portfolio scoring
  -> Portfolio optimization
  -> Dashboard datasets
```

## 3. Forecasting design

- Category-level forecast: chuỗi dày hơn, dùng để bảo vệ độ chính xác mô hình.
- SKU-level forecast: chuỗi thưa hơn do long-tail, dùng để hỗ trợ xếp hạng sản phẩm và tối ưu portfolio.
- Metrics: MAE, RMSE, WAPE và bias.

## 4. Pipeline Tiki

```text
Tiki search snapshot or manual CSV
  -> Normalize product fields
  -> Score market demand proxy
  -> Rank VN market candidates
  -> Dashboard case-study tab
```

Template: `data/raw/tiki/tiki_snapshot_template.csv`

## 5. Cách trình bày với hội đồng

- Forecasting core được xây trên Olist vì đây là dữ liệu lịch sử thật.
- Tiki chỉ là snapshot ứng dụng thực tiễn, không dùng để validate forecasting.
- Nếu muốn forecast Tiki nghiêm túc, cần crawl lặp lại theo ngày/tuần hoặc có dữ liệu đơn hàng nội bộ.
- Việc crawl cần tuân thủ điều khoản sử dụng và giới hạn tần suất request.

## 6. Kết quả hiện tại

```text
Enriched order item rows: 110,197
Forecasted SKU products: 800
SKU portfolio categories: 50
SKU demand history rows: 18,400
Category demand history rows: 1,273
SKU forecast rows: 4,800
Category forecast rows: 444
Best category model: simple_exp_smoothing
Portfolio recommendations: 30
Best category-level WAPE: 22.68%
SKU-level WAPE with exp_smoothing: 140.73%
```

## 7. Kết quả Tiki snapshot hiện tại

```text
Tiki snapshot rows: 320
Tiki portfolio case rows: 80
Tiki categories: 32
Median price: 269,000 VND
Average rating: 1.72
```

## 8. Mở rộng kỹ thuật đã bổ sung

- Benchmark 6 mô hình forecast ở category-level.
- Chọn best model theo overall WAPE.
- Xuất actual-vs-predicted details cho dashboard.
- Phân loại SKU demand pattern: fast_moving, slow_moving, intermittent.
- Bổ sung inventory policy và risk flag trong portfolio recommendation.
