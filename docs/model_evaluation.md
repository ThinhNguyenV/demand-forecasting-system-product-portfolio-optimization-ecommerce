# Model Evaluation Notes

## 1. Mục tiêu

Phần đánh giá mô hình nhằm chứng minh forecasting không chỉ dùng một mô hình duy nhất, mà có benchmark giữa nhiều phương pháp trên cùng tập test.

## 2. Mức dự báo

Hệ thống đánh giá ở hai mức:

- **Category-level**: chuỗi nhu cầu dày hơn, phù hợp để đánh giá năng lực forecast cốt lõi.
- **SKU-level**: chuỗi nhu cầu thưa và intermittent, phù hợp hơn cho portfolio scoring thay vì đánh giá forecast tuyệt đối.

## 3. Các mô hình benchmark

- `naive`: lấy giá trị tháng gần nhất.
- `moving_average`: trung bình trượt 6 tháng.
- `seasonal_naive`: lặp lại giá trị cùng kỳ năm trước.
- `simple_exp_smoothing`: exponential smoothing không seasonal.
- `exp_smoothing`: Holt-Winters additive trend/seasonality.
- `random_forest`: supervised learning với lag features, month, rolling mean/std.

## 4. Metrics

- **MAE**: sai số tuyệt đối trung bình.
- **RMSE**: phạt nặng lỗi lớn.
- **WAPE**: tổng sai số tuyệt đối chia tổng actual demand, dễ diễn giải ở mức business.
- **Bias**: dương là over-forecast, âm là under-forecast.

## 5. Kết quả category-level hiện tại

| Model | MAE | RMSE | WAPE | Bias |
| --- | ---: | ---: | ---: | ---: |
| simple_exp_smoothing | 21.8667 | 41.0854 | 22.68% | 11.1365 |
| naive | 21.9224 | 41.4397 | 22.74% | 10.6712 |
| random_forest | 23.7797 | 44.6736 | 24.67% | 11.0244 |
| moving_average | 29.1948 | 55.9776 | 30.29% | 7.2968 |
| exp_smoothing | 29.1948 | 55.9776 | 30.29% | 7.2968 |
| seasonal_naive | 47.0708 | 99.3598 | 48.83% | -38.0251 |

Model tốt nhất hiện tại là `simple_exp_smoothing`, nên pipeline dùng model này cho `category_forecast.csv`.

## 6. Diễn giải SKU-level

SKU-level WAPE với `exp_smoothing` hiện là 140.73%. Đây là kết quả hợp lý với dataset Olist vì nhiều SKU có long-tail demand: bán không liên tục, nhiều tháng bằng 0, khó forecast chính xác bằng mô hình time series truyền thống.

Việc này được xử lý bằng cách phân loại demand pattern:

- `fast_moving`: ưu tiên tồn kho và promotion.
- `slow_moving`: duy trì, theo dõi velocity, tránh overstock.
- `intermittent`: hạn chế tồn kho, dùng bundle/campaign test.

## 7. Cách trình bày trong báo cáo

Nên trình bày kết luận:

- Category forecast phù hợp cho planning tổng thể.
- SKU forecast kết hợp demand pattern phù hợp cho portfolio decision.
- Olist cho thấy sự khác biệt giữa dự báo chuỗi dày và chuỗi intermittent trong e-commerce.
