"""
Script sinh toàn bộ 9 biểu đồ sơ đồ học thuật chuyên sâu (Chương 1, 2, 3 và 5)
chuẩn quy cách xuất bản chất lượng cao (DPI 300) cho Báo cáo Chuyên đề tốt nghiệp.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path

# Thiết lập font và style chung
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#CBD5E1'
plt.rcParams['axes.linewidth'] = 1.2

CHART_DIR = Path("data/outputs/charts")
CHART_DIR.mkdir(parents=True, exist_ok=True)

# 1. HÌNH 1.1: Long-tail distribution
def generate_fig_1_1():
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=300)
    x = np.linspace(1, 100, 500)
    y = 1000 / (x ** 0.95)

    ax.plot(x, y, color="#1A365D", lw=3, label="Phân bố nhu cầu sản phẩm (Demand Curve)")
    
    # Khu vực Head (A - Fast-moving)
    ax.fill_between(x[x <= 20], y[x <= 20], color="#2B6CB0", alpha=0.35, label="Nhóm Đầu (Head / Fast-Moving): ~20% SKU, 80% Doanh số")
    # Khu vực Torso (B - Slow-moving)
    ax.fill_between(x[(x > 20) & (x <= 50)], y[(x > 20) & (x <= 50)], color="#D69E2E", alpha=0.35, label="Nhóm Thân (Torso / Slow-Moving): ~30% SKU, 15% Doanh số")
    # Khu vực Long Tail (C - Intermittent)
    ax.fill_between(x[x > 50], y[x > 50], color="#E53E3E", alpha=0.3, label="Đuôi Dài (Long-Tail / Intermittent): ~50% SKU, 5% Doanh số (Zero-demand cao)")

    ax.axvline(20, color="#2B6CB0", ls="--", lw=1.5)
    ax.axvline(50, color="#D69E2E", ls="--", lw=1.5)

    ax.set_title("HIỆU ỨNG ĐUÔI DÀI (LONG-TAIL) VÀ PHÂN MẢNH NHU CẦU TRONG E-COMMERCE", fontsize=12, fontweight="bold", pad=15, color="#1A365D")
    ax.set_xlabel("Xếp hạng danh mục sản phẩm theo doanh số (Top SKU %)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Khối lượng nhu cầu trung bình / tháng (Units)", fontsize=10, fontweight="bold")
    ax.set_xlim(1, 100)
    ax.set_ylim(0, 1050)
    ax.grid(True, ls=":", alpha=0.6, color="#CBD5E1")
    ax.legend(loc="upper right", frameon=True, facecolor="#F8FAFC", edgecolor="#CBD5E1", fontsize=8.5)
    
    out_path = CHART_DIR / "long_tail_distribution.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")

# 2. HÌNH 2.1: Croston Mechanism
def generate_fig_2_1():
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(9, 6), sharex=True, dpi=300)
    
    t = np.arange(1, 19)
    # Nhu cầu gián đoạn y_t
    y = np.array([0, 8, 0, 0, 12, 0, 0, 0, 6, 0, 10, 0, 0, 14, 0, 0, 0, 9])
    
    # 1. Nhu cầu gốc
    markerline, stemlines, baseline = ax1.stem(t, y, linefmt="-", markerfmt="o", basefmt="-")
    plt.setp(stemlines, color="#2B6CB0", linewidth=1.8)
    plt.setp(markerline, color="#1A365D", markersize=6)
    plt.setp(baseline, color="#718096", linewidth=1)
    ax1.set_title("Nhu cầu quan sát thực tế (Observed Demand y_t) - Chứa nhiều chu kỳ 0", fontsize=10, fontweight="bold", color="#1A365D")

    ax1.set_ylabel("Số lượng đơn", fontsize=8.5)
    ax1.grid(True, ls=":", alpha=0.5)
    ax1.set_ylim(-1, 16)

    # 2. Tách kích thước nhu cầu z_t
    z_smooth = [8.0]
    p_smooth = [2.0]
    alpha = 0.3
    last_z = 8.0
    last_p = 2.0
    p_counter = 1
    
    z_vals = []
    p_vals = []
    for val in y:
        if val > 0:
            last_z = alpha * val + (1 - alpha) * last_z
            last_p = alpha * p_counter + (1 - alpha) * last_p
            p_counter = 1
        else:
            p_counter += 1
        z_vals.append(last_z)
        p_vals.append(last_p)
        
    ax2.plot(t, z_vals, color="#38A169", marker="s", lw=2, label="Độ lớn nhu cầu làm mượt (Demand Size z_t)")
    ax2.set_title("Chuỗi độ lớn nhu cầu phi zero z_t (Chỉ cập nhật khi y_t > 0)", fontsize=10, fontweight="bold", color="#22543D")
    ax2.set_ylabel("Quy mô z_t", fontsize=8.5)
    ax2.grid(True, ls=":", alpha=0.5)
    ax2.legend(loc="upper left", fontsize=8.5)

    # 3. Tách khoảng cách p_t
    ax3.plot(t, p_vals, color="#DD6B20", marker="^", lw=2, label="Khoảng cách giữa các lần mua (Interval p_t)")
    forecast_croston = [z / p for z, p in zip(z_vals, p_vals)]
    ax3.plot(t, forecast_croston, color="#805AD5", ls="--", lw=2.5, label="Dự báo Croston = z_t / p_t")
    ax3.set_title("Khoảng cách chu kỳ p_t và Tỷ lệ dự báo đều Croston = z_t / p_t", fontsize=10, fontweight="bold", color="#742A2A")
    ax3.set_xlabel("Chu kỳ thời gian (Tháng)", fontsize=9.5, fontweight="bold")
    ax3.set_ylabel("Giá trị", fontsize=8.5)
    ax3.grid(True, ls=":", alpha=0.5)
    ax3.set_xticks(t)
    ax3.legend(loc="upper left", fontsize=8.5)

    out_path = CHART_DIR / "croston_mechanism.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")

# 3. HÌNH 2.2: Sliding Window Features
def generate_fig_2_2():
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=300)
    ax.axis("off")
    
    # Vẽ timeline
    months = ["T-5", "T-4", "T-3", "T-2", "T-1", "T (Mục tiêu dự báo)"]
    x_coords = [0.1, 0.25, 0.40, 0.55, 0.70, 0.88]
    
    for x, m in zip(x_coords[:-1], months[:-1]):
        rect = patches.FancyBboxPatch((x-0.05, 0.65), 0.1, 0.18, boxstyle="round,pad=0.02",
                                      edgecolor="#2B6CB0", facecolor="#EBF8FF", lw=2)
        ax.add_patch(rect)
        ax.text(x, 0.74, m, ha="center", va="center", fontsize=9.5, fontweight="bold", color="#1A365D")
        ax.text(x, 0.68, f"y_{m.lower()}", ha="center", va="center", fontsize=8.5, color="#4A5568")

    # Target box
    rect_target = patches.FancyBboxPatch((x_coords[-1]-0.06, 0.65), 0.12, 0.18, boxstyle="round,pad=0.02",
                                         edgecolor="#38A169", facecolor="#C6F6D5", lw=2.5)
    ax.add_patch(rect_target)
    ax.text(x_coords[-1], 0.74, "Mục tiêu (y_T)", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#22543D")
    ax.text(x_coords[-1], 0.68, "Target Label", ha="center", va="center", fontsize=8.5, color="#276749")

    # Mũi tên trích xuất đặc trưng
    ax.annotate("", xy=(0.5, 0.45), xytext=(0.4, 0.62),
                arrowprops=dict(arrowstyle="->", lw=2, color="#2B6CB0"))
    
    # Hộp đặc trưng trích xuất
    feat_box = patches.FancyBboxPatch((0.15, 0.15), 0.7, 0.3, boxstyle="round,pad=0.03",
                                      edgecolor="#805AD5", facecolor="#FAF5FF", lw=2)
    ax.add_patch(feat_box)
    
    features_text = (
        "BỘ ĐẶC TRƯNG HỌC MÁY TRÍCH XUẤT CHO RANDOM FOREST (PANEL ML):\n"
        "• Lag Features: y_{T-1}, y_{T-2}, y_{T-3} (Nhu cầu các tháng liền trước)\n"
        "• Rolling Stats: Mean(y_{T-3...T-1}), Std(y_{T-3...T-1}), Min, Max\n"
        "• Pattern Signals: Tỷ lệ tháng 0 đơn (ZeroDemandRate), Tần suất giao dịch\n"
        "• Calendar & Assortment: Tháng mùa vụ (Month), Mã hóa nhóm ngành hàng (Category Enc)"
    )
    ax.text(0.5, 0.3, features_text, ha="center", va="center", fontsize=8.5, color="#44337A", linespacing=1.5)
    
    ax.set_title("CƠ CHẾ CỬA SỔ TRƯỢT (SLIDING WINDOW) VÀ TRÍCH XUẤT ĐẶC TRƯNG BẢNG", fontsize=11, fontweight="bold", color="#1A365D", pad=10)
    
    out_path = CHART_DIR / "sliding_window_features.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")

# 4. HÌNH 2.3: Top-Down Reconciliation
def generate_fig_2_3():
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    ax.axis("off")

    # Cấp Category
    cat_box = patches.FancyBboxPatch((0.3, 0.75), 0.4, 0.16, boxstyle="round,pad=0.02",
                                     edgecolor="#1A365D", facecolor="#E2E8F0", lw=2.5)
    ax.add_patch(cat_box)
    ax.text(0.5, 0.85, "DỰ BÁO CẤP DANH MỤC (CATEGORY LEVEL)", ha="center", va="center", fontsize=10, fontweight="bold", color="#1A365D")
    ax.text(0.5, 0.79, "Mô hình tối ưu: SES (WAPE = 22.68%) → Trần kiểm soát: Ŷ_{c,t} = 500 units", ha="center", va="center", fontsize=8.5, color="#2D3748")

    # Các SKU bên dưới
    skus = [
        ("SKU 1 (Fast-moving)", "ŷ_1 thô = 200", "w_1 = 40%", "ŷ_1 điều hòa = 200"),
        ("SKU 2 (Slow-moving)", "ŷ_2 thô = 180", "w_2 = 36%", "ŷ_2 điều hòa = 180"),
        ("SKU 3 (Intermittent)", "ŷ_3 thô = 120", "w_3 = 24%", "ŷ_3 điều hòa = 120"),
    ]
    x_positions = [0.12, 0.5, 0.88]
    
    for x_pos, (title, raw, weight, recon) in zip(x_positions, skus):
        # Mũi tên từ Category xuống SKU
        ax.annotate("", xy=(x_pos, 0.48), xytext=(0.5, 0.74),
                    arrowprops=dict(arrowstyle="->", lw=1.8, color="#4A5568", connectionstyle="arc3,rad=0"))
        
        # Hộp SKU
        box = patches.FancyBboxPatch((x_pos-0.16, 0.12), 0.32, 0.34, boxstyle="round,pad=0.02",
                                     edgecolor="#2B6CB0", facecolor="#F7FAFC", lw=1.8)
        ax.add_patch(box)
        ax.text(x_pos, 0.40, title, ha="center", va="center", fontsize=9, fontweight="bold", color="#1A365D")
        ax.text(x_pos, 0.33, raw, ha="center", va="center", fontsize=8.5, color="#718096")
        ax.text(x_pos, 0.26, f"Tỷ trọng: {weight}", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#D69E2E")
        
        recon_box = patches.FancyBboxPatch((x_pos-0.14, 0.15), 0.28, 0.08, boxstyle="round,pad=0.01",
                                           edgecolor="#38A169", facecolor="#C6F6D5", lw=1.2)
        ax.add_patch(recon_box)
        ax.text(x_pos, 0.19, recon, ha="center", va="center", fontsize=8.5, fontweight="bold", color="#22543D")

    # Ghi chú tổng hợp
    ax.text(0.5, 0.04, "Tổng dự báo SKU thô (500) = Trần Category (500) ⇒ Triệt tiêu hiện tượng Bullwhip & Lệch số liệu",
            ha="center", va="center", fontsize=9, style="italic", color="#2B6CB0", fontweight="bold")

    ax.set_title("NGUYÊN LÝ ĐIỀU HÒA DỰ BÁO TỶ LỆ TỪ TRÊN XUỐNG (TOP-DOWN RECONCILIATION)", fontsize=11, fontweight="bold", color="#1A365D", pad=10)

    out_path = CHART_DIR / "top_down_reconciliation.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")

# 5. HÌNH 3.1: System Architecture Diagram
def generate_fig_3_1():
    fig, ax = plt.subplots(figsize=(10, 6.8), dpi=300)
    ax.axis("off")

    layers = [
        ("TẦNG DỮ LIỆU (DATA LAYER)", "#E2E8F0", "#1A365D", [
            "Olist E-Commerce Raw CSVs (110k dòng giao dịch)",
            "Public Web Sources (Books to Scrape HTML / Tiki Snapshot CSV)"
        ], 0.80),
        ("TẦNG XỬ LÝ LÕI & MÔ HÌNH HÓA (CORE PIPELINE)", "#EBF8FF", "#2B6CB0", [
            "Data Builder & Cleaning (olist.py)",
            "Category Benchmark 8 Models (evaluation.py)",
            "SKU Pattern Classifier (Fast, Slow, Intermittent)",
            "Adaptive Model Routing (Global RF, Croston, TSB)",
            "Top-Down Reconciliation & Safety Stock Estimator",
            "Multi-Objective Portfolio Optimizer & SHAP TreeExplainer"
        ], 0.48),
        ("TẦNG LƯU TRỮ ĐẦU RA (OUTPUT STORAGE)", "#FEFCBF", "#B7791F", [
            "Processed Datasets (clean_products, demand_history)",
            "Forecasts & Backtest Metrics CSVs",
            "Portfolio Recommendations & Risk Indicators CSV",
            "High-Resolution PNG Visualization Charts"
        ], 0.22),
        ("TẦNG TRÌNH DIỄN (STREAMLIT DASHBOARD)", "#C6F6D5", "#22543D", [
            "7 Phân hệ Tabs: Overview, Forecast Explorer, Evaluation, Portfolio Matrix, SHAP Explain, Market Case, Data Dict"
        ], 0.05)
    ]

    for title, bg_color, border_color, items, y_pos in layers:
        height = 0.06 + len(items) * 0.038
        box = patches.FancyBboxPatch((0.08, y_pos - height/2), 0.84, height, boxstyle="round,pad=0.02",
                                     edgecolor=border_color, facecolor=bg_color, lw=2.2)
        ax.add_patch(box)
        ax.text(0.12, y_pos + height/2 - 0.04, title, ha="left", va="center", fontsize=9.5, fontweight="bold", color=border_color)
        
        # Vẽ các bullet item
        for i, item in enumerate(items):
            item_y = y_pos + height/2 - 0.08 - i * 0.036
            ax.text(0.14, item_y, f"• {item}", ha="left", va="center", fontsize=8.5, color="#2D3748")

    # Mũi tên kết nối các tầng
    for y_arrow in [0.67, 0.35, 0.13]:
        ax.annotate("", xy=(0.5, y_arrow - 0.03), xytext=(0.5, y_arrow + 0.03),
                    arrowprops=dict(arrowstyle="->", lw=2.5, color="#4A5568"))

    ax.set_title("SƠ ĐỒ KIẾN TRÚC TỔNG THỂ HỆ THỐNG DỰ BÁO VÀ TỐI ƯU HÓA DANH MỤC", fontsize=12, fontweight="bold", color="#1A365D", pad=12)

    out_path = CHART_DIR / "system_architecture.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")

# 6. HÌNH 3.2: Dual-Track Data Flow Pipeline
def generate_fig_3_2():
    fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=300)
    ax.axis("off")

    # Track 1
    t1_box = patches.FancyBboxPatch((0.05, 0.52), 0.42, 0.38, boxstyle="round,pad=0.02",
                                    edgecolor="#2B6CB0", facecolor="#EBF8FF", lw=2)
    ax.add_patch(t1_box)
    ax.text(0.26, 0.85, "TRỤC 1: DỮ LIỆU THỜI GIAN OLIST (CORE)", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#1A365D")
    t1_text = (
        "• 110.197 giao dịch đơn hàng Olist Brazil (2016-2018)\n"
        "• Chuỗi lịch sử nhu cầu tháng liên tục (Monthly Demand)\n"
        "• Huấn luyện & Backtest Benchmark 8 mô hình dự báo\n"
        "• Tính toán độ lệch chuẩn sai số backtest σ_e\n"
        "• Xác lập mức tồn kho an toàn Safety Stock (SS)"
    )
    ax.text(0.08, 0.68, t1_text, ha="left", va="center", fontsize=8, color="#2D3748", linespacing=1.4)

    # Track 2
    t2_box = patches.FancyBboxPatch((0.53, 0.52), 0.42, 0.38, boxstyle="round,pad=0.02",
                                    edgecolor="#38A169", facecolor="#F0FFF4", lw=2)
    ax.add_patch(t2_box)
    ax.text(0.74, 0.85, "TRỤC 2: DỮ LIỆU THỊ TRƯỜNG CÔNG KHAI", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#22543D")
    t2_text = (
        "• Adapter thu thập web công khai (BooksToScrape / Tiki)\n"
        "• Tuân thủ nghiêm ngặt robots.txt & Rate Limiting\n"
        "• Trích xuất thông tin ảnh chụp tại một thời điểm (Snapshot)\n"
        "• Lượng hóa điểm tiềm năng thị trường (Market Scoring)\n"
        "• Minh họa ứng dụng danh mục mở rộng cho thị trường VN"
    )
    ax.text(0.56, 0.68, t2_text, ha="left", va="center", fontsize=8, color="#2D3748", linespacing=1.4)

    # Output hội tụ
    out_box = patches.FancyBboxPatch((0.2, 0.08), 0.6, 0.28, boxstyle="round,pad=0.02",
                                     edgecolor="#805AD5", facecolor="#FAF5FF", lw=2.2)
    ax.add_patch(out_box)
    ax.text(0.5, 0.30, "HỘI TỤ TẠI TẦNG TỐI ƯU HÓA DANH MỤC & DASHBOARD RA QUYẾT ĐỊNH", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#44337A")
    out_text = (
        "• Tổng hợp ma trận ưu tiên đa tiêu chí (Portfolio Priority Matrix: ABC + Margin + Demand + Risk)\n"
        "• Trực quan hóa giải thích đóng góp đặc trưng SHAP TreeExplainer\n"
        "• Cung cấp giao diện tương tác đa kịch bản (What-if Scenario) phục vụ nhà quản trị chuỗi cung ứng"
    )
    ax.text(0.5, 0.18, out_text, ha="center", va="center", fontsize=8, color="#4A5568", linespacing=1.3)

    # Mũi tên hội tụ
    ax.annotate("", xy=(0.35, 0.38), xytext=(0.26, 0.51), arrowprops=dict(arrowstyle="->", lw=2, color="#4A5568"))
    ax.annotate("", xy=(0.65, 0.38), xytext=(0.74, 0.51), arrowprops=dict(arrowstyle="->", lw=2, color="#4A5568"))

    ax.set_title("BIỂU ĐỒ LUỒNG DỮ LIỆU 2 TẦNG (DUAL-TRACK DATA FLOW PIPELINE)", fontsize=11, fontweight="bold", color="#1A365D", pad=12)

    out_path = CHART_DIR / "dual_track_data_flow.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")

# 7. HÌNH 3.3: Model Routing Flowchart
def generate_fig_3_3():
    fig, ax = plt.subplots(figsize=(9.5, 5.5), dpi=300)
    ax.axis("off")

    # Bắt đầu
    p_start = patches.FancyBboxPatch((0.38, 0.88), 0.24, 0.08, boxstyle="round,pad=0.02",
                                     edgecolor="#1A365D", facecolor="#E2E8F0", lw=2)
    ax.add_patch(p_start)
    ax.text(0.5, 0.92, "Tập dữ liệu 800 SKU", ha="center", va="center", fontsize=9, fontweight="bold", color="#1A365D")

    # Quyết định phân loại pattern
    diamond = patches.Polygon([[0.5, 0.80], [0.68, 0.72], [0.5, 0.64], [0.32, 0.72]],
                              closed=True, edgecolor="#D69E2E", facecolor="#FEFCBF", lw=2)
    ax.add_patch(diamond)
    ax.text(0.5, 0.72, "Phân loại Demand Pattern\n(Syntetos & Boylan, 2005)", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#744210")

    ax.annotate("", xy=(0.5, 0.80), xytext=(0.5, 0.88), arrowprops=dict(arrowstyle="->", lw=1.8, color="#4A5568"))

    # 3 nhánh
    # Nhánh 1: Fast-moving
    b_fast = patches.FancyBboxPatch((0.05, 0.40), 0.26, 0.14, boxstyle="round,pad=0.02",
                                    edgecolor="#2B6CB0", facecolor="#EBF8FF", lw=1.8)
    ax.add_patch(b_fast)
    ax.text(0.18, 0.50, "Fast-Moving (Nhanh)", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#1A365D")
    ax.text(0.18, 0.44, "Định tuyến sang:\nGlobal Random Forest", ha="center", va="center", fontsize=8, color="#2B6CB0")

    # Nhánh 2: Intermittent
    b_inter = patches.FancyBboxPatch((0.69, 0.40), 0.26, 0.14, boxstyle="round,pad=0.02",
                                     edgecolor="#E53E3E", facecolor="#FFF5F5", lw=1.8)
    ax.add_patch(b_inter)
    ax.text(0.82, 0.50, "Intermittent (Gián đoạn)", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#742A2A")
    ax.text(0.82, 0.44, "Định tuyến sang:\nTSB Method", ha="center", va="center", fontsize=8, color="#C53030")

    # Nhánh 3: Slow-moving
    b_slow = patches.FancyBboxPatch((0.37, 0.40), 0.26, 0.14, boxstyle="round,pad=0.02",
                                    edgecolor="#38A169", facecolor="#F0FFF4", lw=1.8)
    ax.add_patch(b_slow)
    ax.text(0.5, 0.50, "Slow-Moving (Chậm)", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#22543D")
    ax.text(0.5, 0.44, "Định tuyến sang:\nCroston / Random Forest", ha="center", va="center", fontsize=8, color="#276749")

    # Mũi tên từ kim cương sang 3 nhánh
    ax.annotate("", xy=(0.18, 0.55), xytext=(0.33, 0.72), arrowprops=dict(arrowstyle="->", lw=1.8, color="#2B6CB0"))
    ax.annotate("", xy=(0.5, 0.55), xytext=(0.5, 0.64), arrowprops=dict(arrowstyle="->", lw=1.8, color="#38A169"))
    ax.annotate("", xy=(0.82, 0.55), xytext=(0.67, 0.72), arrowprops=dict(arrowstyle="->", lw=1.8, color="#E53E3E"))

    # Hộp điều hòa dự báo
    b_recon = patches.FancyBboxPatch((0.2, 0.14), 0.6, 0.16, boxstyle="round,pad=0.02",
                                     edgecolor="#805AD5", facecolor="#FAF5FF", lw=2)
    ax.add_patch(b_recon)
    ax.text(0.5, 0.24, "ĐIỀU HÒA DỰ BÁO TỶ LỆ TỪ TRÊN XUỐNG (TOP-DOWN RECONCILIATION)", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#44337A")
    ax.text(0.5, 0.17, "Chuẩn hóa theo trần Category SES → Tính Safety Stock & Chấm điểm Portfolio", ha="center", va="center", fontsize=8, color="#4A5568")

    # Mũi tên vào điều hòa
    for x_b in [0.18, 0.5, 0.82]:
        ax.annotate("", xy=(0.5, 0.31), xytext=(x_b, 0.39), arrowprops=dict(arrowstyle="->", lw=1.6, color="#4A5568"))

    ax.set_title("SƠ ĐỒ QUY TRÌNH ĐỊNH TUYẾN MÔ HÌNH VÀ ĐIỀU HÒA DỰ BÁO (MODEL ROUTING)", fontsize=11, fontweight="bold", color="#1A365D", pad=12)

    out_path = CHART_DIR / "model_routing_flowchart.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")

# 8. HÌNH 3.4: Portfolio Matrix Schema
def generate_fig_3_4():
    fig, ax = plt.subplots(figsize=(8.5, 5.5), dpi=300)

    # 4 góc phần tư
    ax.axhline(50, color="#CBD5E1", ls="--", lw=1.5)
    ax.axvline(50, color="#CBD5E1", ls="--", lw=1.5)

    # Vùng 1: Top-Right (Ưu tiên số 1 - Đầu tư chủ lực)
    ax.fill_between([50, 100], 50, 100, color="#C6F6D5", alpha=0.35)
    ax.text(75, 82, "GÓC PHẦN TƯ I: SẢN PHẨM CHỦ LỰC\n(High Profit, High Demand)\n• Phân loại: Nhóm A / Fast-moving\n• Chiến lược: Ưu tiên vốn & Tối đa hóa khả năng đáp ứng",
            ha="center", va="center", fontsize=8, fontweight="bold", color="#22543D")

    # Vùng 2: Top-Left (Lợi nhuận cao nhưng nhu cầu biến động)
    ax.fill_between([0, 50], 50, 100, color="#FEFCBF", alpha=0.35)
    ax.text(25, 82, "GÓC PHẦN TƯ II: CƠ HỘI LỢI NHUẬN\n(High Profit, Lower / Risky Demand)\n• Phân loại: Nhóm B / Slow-moving\n• Chiến lược: Đặt hàng theo lô & Duy trì Safety Stock",
            ha="center", va="center", fontsize=8, fontweight="bold", color="#744210")

    # Vùng 3: Bottom-Right (Nhu cầu cao nhưng biên lợi nhuận mỏng)
    ax.fill_between([50, 100], 0, 50, color="#EBF8FF", alpha=0.35)
    ax.text(75, 25, "GÓC PHẦN TƯ III: HÀNG HÓA DUY TRÌ\n(Low Profit, High Volume)\n• Phân loại: Nhóm B / Hàng tiêu dùng\n• Chiến lược: Tối ưu chi phí vận chuyển & Đặt hàng tự động",
            ha="center", va="center", fontsize=8, fontweight="bold", color="#1A365D")

    # Vùng 4: Bottom-Left (Rủi ro cao, lợi nhuận thấp)
    ax.fill_between([0, 50], 0, 50, color="#FFF5F5", alpha=0.35)
    ax.text(25, 25, "GÓC PHẦN TƯ IV: HÀNG ĐUÔI DÀI / TINH GIẢN\n(Low Profit, Intermittent)\n• Phân loại: Nhóm C / Đuôi dài\n• Chiến lược: Giảm lưu kho, Just-in-Time hoặc loại bỏ",
            ha="center", va="center", fontsize=8, fontweight="bold", color="#742A2A")

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Nhu cầu dự báo điều chỉnh rủi ro (Risk-Adjusted Quantity Q = Q_forecast + SS)", fontsize=9.5, fontweight="bold")
    ax.set_ylabel("Lợi nhuận gộp kỳ vọng (Expected Profit Proxy)", fontsize=9.5, fontweight="bold")
    ax.set_title("MA TRẬN PHÂN BỔ THỨ TỰ ƯU TIÊN DANH MỤC SẢN PHẨM (PORTFOLIO MATRIX)", fontsize=11, fontweight="bold", color="#1A365D", pad=12)
    ax.grid(True, ls=":", alpha=0.5)

    out_path = CHART_DIR / "portfolio_matrix_schema.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")

# 9. HÌNH 5.9: Streamlit Dashboard Overview
def generate_fig_5_9():
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.axis("off")

    # Tiêu đề Dashboard UI
    header_box = patches.FancyBboxPatch((0.05, 0.85), 0.90, 0.12, boxstyle="round,pad=0.01",
                                        edgecolor="#1A365D", facecolor="#1A365D", lw=1.5)
    ax.add_patch(header_box)
    ax.text(0.08, 0.93, "DEMAND FORECASTING & PRODUCT PORTFOLIO OPTIMIZATION DASHBOARD",
            ha="left", va="center", fontsize=11, fontweight="bold", color="#FFFFFF")
    ax.text(0.08, 0.88, "Streamlit Decision-Support System • Olist E-Commerce Core & VN Public Market Case Study",
            ha="left", va="center", fontsize=8.5, color="#CBD5E1")

    # Sidebar bên trái
    side_box = patches.FancyBboxPatch((0.05, 0.08), 0.22, 0.74, boxstyle="round,pad=0.01",
                                      edgecolor="#CBD5E1", facecolor="#F8FAFC", lw=1.5)
    ax.add_patch(side_box)
    ax.text(0.16, 0.77, "THIẾT LẬP THAM SỐ", ha="center", va="center", fontsize=9, fontweight="bold", color="#1A365D")
    sidebar_items = [
        "Forecast Horizon: 6M",
        "Portfolio Size: Top 30",
        "Assortment: 800 SKUs",
        "Min Active Months: 4",
        "Service Level: 95%",
        "Category Cap: 40%",
        "[ RUN PIPELINE ]"
    ]
    for i, itm in enumerate(sidebar_items):
        ax.text(0.08, 0.70 - i * 0.08, itm, ha="left", va="center", fontsize=8, color="#2D3748")

    # Vùng hiển thị Tabs chính bên phải
    tabs = [
        ("Tab 1: Olist Overview", "KPI Cards (Revenue, SKUs, Orders) & Monthly Revenue / Margin Trend"),
        ("Tab 2: Forecast Explorer", "Category Growth Projections & Granular 800 SKU Demand Forecasts"),
        ("Tab 3: Model Benchmark", "WAPE / RMSE Bar Chart (8 Models) & Actual vs Predicted Time-Series"),
        ("Tab 4: Portfolio Matrix", "Interactive Bubble Chart (Profit vs SS vs Uncertainty) & Top 30 Table"),
        ("Tab 5: SHAP Explainability", "TreeExplainer Feature Drivers & Segment Waterfall Visualizations"),
        ("Tab 6: Market Case Study", "Public Web Scraping Snapshot & VN Assortment Application Case"),
        ("Tab 7: Data & Export", "Data Dictionaries & Automated Reports Generation (.docx / .tex)")
    ]
    
    for i, (tab_title, tab_desc) in enumerate(tabs):
        y_t = 0.75 - i * 0.095
        t_box = patches.FancyBboxPatch((0.30, y_t), 0.65, 0.08, boxstyle="round,pad=0.01",
                                       edgecolor="#2B6CB0", facecolor="#EBF8FF" if i < 4 else "#F7FAFC", lw=1.2)
        ax.add_patch(t_box)
        ax.text(0.32, y_t + 0.05, tab_title, ha="left", va="center", fontsize=8.5, fontweight="bold", color="#1A365D")
        ax.text(0.32, y_t + 0.02, tab_desc, ha="left", va="center", fontsize=7.5, color="#4A5568")

    ax.set_title("GIAO DIỆN HỆ THỐNG RA QUYẾT ĐỊNH STREAMLIT DASHBOARD (7 PHÂN HỆ CHUYÊN SÂU)",
                 fontsize=11, fontweight="bold", color="#1A365D", pad=12)

    out_path = CHART_DIR / "streamlit_dashboard_overview.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")

if __name__ == "__main__":
    generate_fig_1_1()
    generate_fig_2_1()
    generate_fig_2_2()
    generate_fig_2_3()
    generate_fig_3_1()
    generate_fig_3_2()
    generate_fig_3_3()
    generate_fig_3_4()
    generate_fig_5_9()
    print("ALL 9 DIAGRAMS GENERATED SUCCESSFULLY!")
