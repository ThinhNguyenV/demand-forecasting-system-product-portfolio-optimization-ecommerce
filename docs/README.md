# Tài Liệu Dự Án

Thư mục này gom các tài liệu phục vụ báo cáo, bảo vệ chuyên đề và vận hành hệ thống dự báo nhu cầu - tối ưu danh mục sản phẩm.

## Thứ tự đọc đề xuất

1. [Chiến lược dữ liệu](data_strategy.md)
2. [Thiết kế hệ thống](system_design.md)
3. [Đánh giá mô hình](model_evaluation.md)
4. [Dashboard data dictionary](dashboard_data_dictionary.md)

## Vai trò từng tài liệu

| File | Nội dung chính |
| --- | --- |
| `data_strategy.md` | Giải thích vì sao Olist là dataset forecasting chính và Tiki chỉ là case study bổ trợ cho thị trường Việt Nam. |
| `system_design.md` | Kiến trúc pipeline, module code, luồng dữ liệu, output và giới hạn hệ thống. |
| `model_evaluation.md` | Cách benchmark mô hình, metrics, kết quả category-level và diễn giải SKU-level. |
| `dashboard_data_dictionary.md` | Từ điển dữ liệu cho các file raw, processed, outputs và dashboard-ready. |

## Nguyên tắc trình bày

- Olist là nguồn dữ liệu chính để đánh giá forecasting vì có lịch sử đơn hàng theo thời gian.
- Tiki snapshot là phần minh họa khả năng áp dụng tại Việt Nam, không dùng để validate forecasting nếu chỉ có một thời điểm dữ liệu.
- Category-level forecast dùng để bảo vệ chất lượng mô hình vì chuỗi dữ liệu ổn định hơn.
- SKU-level forecast dùng chủ yếu cho ranking, portfolio scoring và chính sách tồn kho vì nhu cầu SKU trong e-commerce thường thưa và gián đoạn.
