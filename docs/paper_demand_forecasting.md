# A Dual-Level Pattern-Routed Forecasting and Risk-Aware Portfolio Optimization Framework for E-Commerce

**Author:** Van-Thinh Nguyen (Student ID: 25730149)  
**Affiliation:** Faculty of Information Systems, University of Information Technology, Vietnam National University Ho Chi Minh City (UIT, VNU-HCM), Vietnam.  
**Email:** 25730149@uit.edu.vn  

---

## Abstract

In modern e-commerce fulfillment and marketplace management, demand forecasting and assortment planning represent critical drivers of operational resilience and profitability. However, retail data exhibits structural challenges: vast assortments dominated by long-tail items, highly intermittent and lumpy demand characterized by extensive zero-demand intervals, and cross-echelon bullwhip distortion. Applying a homogeneous forecasting model uniformly across all stock keeping units (SKUs) inevitably incurs severe inaccuracies, exacerbating stockouts and dead-stock accumulation. 

To overcome these challenges, this paper presents an integrated analytical framework featuring three core innovations: (1) **Dual-Level Pattern-Routed Forecasting Architecture**, which benchmarks 8 diverse statistical and machine learning models at the aggregate category level while dynamically segmenting 800 SKUs into three demand archetypes (*fast-moving*, *slow-moving*, and *intermittent*) to route them to tailored algorithms (Global Panel Random Forest, Croston, or Teunter-Syntetos-Babai); (2) **Top-Down Proportional Forecast Reconciliation and Forecast-Error-Driven Safety Stock**, ensuring strict mathematical coherence between granular SKU projections and category constraints while translating backtest error dispersion ($\sigma_e$) into risk-adjusted buffer inventory; and (3) **Multi-Objective Risk-Aware Portfolio Optimization and Explainability**, unifying ABC revenue stratification, margin proxies, demand velocity, and uncertainty ratios into a constrained *Portfolio Priority Score*, underpinned by SHAP (SHapley Additive exPlanations) TreeExplainer interpretability. 

Validated on the Olist Brazilian E-Commerce dataset comprising 110,197 enriched transactions across 50 categories and 800 SKUs, empirical results demonstrate that Simple Exponential Smoothing achieves superior accuracy at the category level (WAPE: 22.68%). At the granular SKU level, the proposed pattern-routed mechanism significantly suppresses WAPE from 140.73% (single Holt-Winters baseline) down to 118.78%, securing a notable 21.95-percentage-point error reduction. The framework is fully deployed as an interactive decision-support application.

**Keywords:** Demand Forecasting, Intermittent Demand, Model Routing, Top-Down Reconciliation, Safety Stock, Portfolio Optimization, SHAP, E-Commerce Analytics.

---

## 1. Introduction

Supply chain dynamics in contemporary e-commerce marketplaces present unprecedented operational complexity. Digital platforms handle millions of customer interactions with rapid catalog expansion and shortened product life cycles. Within this environment, inventory misallocation carries acute economic penalties: stockouts compromise vendor reputations and trigger customer defections, whereas excess inventory incurs prohibitive warehousing costs and markdown erosion.

Demand forecasting in digital retail is fundamentally hindered by the **"Long-Tail" distribution** and **intermittent demand patterns**. In contrast to fast-moving consumer goods that exhibit continuous consumption patterns, the majority of e-commerce SKUs experience erratic purchasing rhythms characterized by sporadic transactions separated by long sequences of zero-demand periods. Traditional time-series methods (e.g., ARIMA or Holt-Winters) struggle under such sparsity. Furthermore, decoupled forecasting across product hierarchies induces discrepancies between top-level strategic targets and bottom-up operational procurement.

To resolve these interconnected bottlenecks, this research proposes a dual-level, pattern-routed forecasting and risk-aware portfolio optimization framework.

---

## 2. Theoretical Foundations and Methodology

### 2.1. Demand Pattern Categorization
Following the canonical classification established by Syntetos and Boylan (2005), demand sequences are characterized by the Average Inter-demand Interval ($ADI = N/k$) and the Squared Coefficient of Variation ($CV^2 = (\sigma_z / \mu_z)^2$). The framework partitions 800 retail SKUs into three practical operational regimes:
- **Fast-Moving:** Characterized by sustained order frequency ($ZeroMonthRate \le 0.35$ and $CV < 1.2$).
- **Intermittent:** Dominated by sparse transaction occurrences ($ZeroMonthRate \ge 0.50$ or $ADI \ge 1.4$).
- **Slow-Moving:** Intermediate velocity requiring balanced risk controls.

### 2.2. Algorithmic Suite & Model Routing
The framework incorporates eight representative models across statistical, exponential smoothing, and machine learning paradigms:
1. **Naïve:** Persistence baseline ($\hat{y}_{T+h|T} = y_T$).
2. **Simple Moving Average (SMA):** 6-month trailing mean.
3. **Seasonal Naïve (SNaive):** 12-month seasonal recurrence.
4. **Simple Exponential Smoothing (SES):** Level tracking with optimal smoothing parameter $\alpha$.
5. **Holt-Winters Exponential Smoothing (HW-ES):** Additive trend and seasonal decomposition.
6. **Croston Method (1972):** Decoupled smoothing of non-zero demand size ($z_t$) and inter-arrival intervals ($p_t$).
7. **Teunter-Syntetos-Babai (TSB - 2011):** Continuous updating of demand probability ($d_t$) and positive magnitude ($z_t$).
8. **Global Panel Random Forest Regressor:** A cross-sectional supervised panel model utilizing multi-period lag observations, rolling statistical moments (mean, standard deviation), zero-demand frequency, calendar seasonality, and categorical embeddings.

**Routing Logic:** Fast-moving series are routed to the Global Random Forest; intermittent series are dispatched to TSB to prevent obsolescence overestimation; and slow-moving items are assigned to Croston or Global RF based on zero-rate thresholds.

### 2.3. Top-Down Proportional Forecast Reconciliation
To enforce aggregate consistency, let $\hat{Y}_{c, t}$ denote the independent top-level forecast for category $c$ and $\hat{y}_{i, t}^{\text{raw}}$ denote bottom-level SKU forecasts. Proportional reconciliation redistributes the category projection:
$$\hat{y}_{i, t}^{\text{reconciled}} = \text{round} \left( \hat{Y}_{c, t} \times \frac{\hat{y}_{i, t}^{\text{raw}}}{\sum_{j \in c} \hat{y}_{j, t}^{\text{raw}}} \right)$$

### 2.4. Forecast-Error-Driven Safety Stock & Portfolio Scoring
Rather than relying on passive historical demand volatility, the safety stock ($SS$) directly integrates out-of-sample backtest prediction errors ($\sigma_{e, i}$):
$$SS_i = \left\lceil z \cdot \sigma_{e, i} \cdot \sqrt{H} \right\rceil$$
where $z = 1.65$ corresponds to a 95% cycle service level over horizon $H$.

The multi-objective priority ranking synthesizes expected profitability, risk-adjusted volume, revenue percentile, pattern reliability, and uncertainty suppression:
$$\text{PortfolioScore}_i = 0.30 \cdot \text{Rank}(\text{Profit}_i) + 0.25 \cdot \text{Rank}(Q_i + SS_i) + 0.20 \cdot \text{Rank}(\text{Rev}_i) + 0.15 \cdot \text{PatternScore}_i + 0.10 \cdot (1 - \text{Rank}(UR_i))$$
subject to a category diversification cap preventing any individual sector from exceeding 40% of the recommended portfolio.

### 2.5. Model Explainability via SHAP TreeExplainer
For the Global Random Forest, individual SKU forecasts are decomposed using Shapley additive values:
$$f(x) = \phi_0 + \sum_{j=1}^{M} \phi_j(x)$$
enabling granular interpretation of feature contributions across demand segments.

---

## 3. Empirical Evaluation and Results

### 3.1. Category-Level Benchmark
Backtesting across a 3-month holdout set over 50 product categories reveals the performance hierarchy:

| Model | MAE | RMSE | WAPE (%) | Bias |
| :--- | :---: | :---: | :---: | :---: |
| **Simple Exponential Smoothing (SES)** | **21.87** | **41.09** | **22.68%** | **+11.14** |
| Naïve | 21.92 | 41.44 | 22.74% | +10.67 |
| Random Forest | 23.45 | 44.30 | 24.33% | +9.69 |
| Moving Average | 29.19 | 55.98 | 30.29% | +7.30 |
| Holt-Winters | 29.19 | 55.98 | 30.29% | +7.30 |
| TSB | 32.91 | 75.70 | 34.14% | -25.84 |
| Croston | 33.10 | 76.07 | 34.34% | -26.08 |
| Seasonal Naïve | 47.07 | 99.36 | 48.83% | -38.03 |

SES outperforms competing approaches due to its agile adaptation to local trend shifts without overfitting high-frequency noise.

### 3.2. SKU-Level Pattern-Routed Gains
At the granular SKU level across 800 products, evaluating the pattern-routed architecture against a uniform single-model baseline demonstrates substantial improvement:
- **Baseline (Single Holt-Winters):** MAE: 2.65, RMSE: 5.82, WAPE: **140.73%**.
- **Pattern-Routed Architecture:** MAE: **2.24**, RMSE: **5.04**, WAPE: **118.78%** (Bias: -0.37).
- **Performance Gain:** 21.95 percentage points reduction in WAPE, coupled with a 15.5% reduction in absolute error.

### 3.3. SHAP Interpretability Insights
SHAP TreeExplainer analysis highlights distinct operational mechanics:
- **Fast-Moving Segment:** Dominated by $Lag_1$ and $RollingMean_{3m}$, confirming heavy reliance on recent consumption momentum.
- **Intermittent Segment:** Strongly governed by $ZeroDemandRate$ and $RollingStd$, demonstrating that the probability of demand reoccurrence heavily outweighs instantaneous volume history.

### 3.4. Portfolio Allocation and Buffer Sizing
Optimizing for a 6-month horizon yields a curated Top-30 portfolio generating 9,791 units of baseline forecast, fortified by 520 units of dynamic safety stock (10,311 risk-adjusted units). The category diversification cap successfully broadens assortment across telephony, automotive, health/beauty, and computer accessories.

---

## 4. Conclusion and Future Directions

This paper introduced an integrated, dual-level e-commerce demand forecasting and assortment optimization system. By harmonizing pattern-routed time-series forecasting, hierarchical reconciliation, backtest-derived safety stock sizing, and SHAP explainability, the proposed framework establishes a rigorous, interpretable, and commercially viable decision-support engine. Future extensions will incorporate optimal minimum-trace (MinT) hierarchical reconciliation, deep temporal fusion transformers, and dynamic marketing spend integration.

---

## References

1. Syntetos, A. A., & Boylan, J. E. (2005). The accuracy of intermittent demand estimates. *International Journal of Forecasting*, 21(2), 303-314.
2. Croston, J. D. (1972). Forecasting and stock control for intermittent demands. *Operational Research Quarterly*, 289-303.
3. Teunter, R. H., Syntetos, A. A., & Babai, M. Z. (2011). Intermittent demand: Customer-induced interarrival times and a new forecasting method. *International Journal of Production Economics*, 133(1), 329-337.
4. Hyndman, R. J., & Athanasopoulos, G. (2018). *Forecasting: principles and practice* (2nd ed.). OTexts: Melbourne, Australia.
5. Wickramasuriya, S. L., Athanasopoulos, G., & Hyndman, R. J. (2019). Optimal forecast reconciliation for hierarchical and grouped time series through trace minimization. *Journal of the American Statistical Association*, 114(526), 804-819.
6. Breiman, L. (2001). Random forests. *Machine Learning*, 45(1), 5-32.
7. Lundberg, S. M., & Lee, S. I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems*, 30, 4765-4774.
8. Silver, E. A., Pyke, D. F., & Peterson, R. (1998). *Inventory management and production planning and scheduling* (3rd ed.). John Wiley & Sons.
