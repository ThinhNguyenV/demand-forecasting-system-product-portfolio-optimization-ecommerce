import sys
sys.path.insert(0, "src")
from ecom_forecasting.crawlers import PublicSiteConfig, FieldSelector, crawl_public_site

config = PublicSiteConfig(
    site_name="Chợ Tốt",
    page_url_template="https://www.chotot.com/do-dien-tu",
    product_selector="div[class*='AdItem_wrapperAdItem']",
    fields={
        "title": FieldSelector(css="p[class*='adTitle']"),
        "price": FieldSelector(css="span[class*='price']"),
        "product_url": FieldSelector(css="a[href*='.htm']", attribute="href"),
    },
    constants={"category": "Đồ điện tử"},
    pages=1,
    engine="playwright",
    timeout_seconds=25,
    wait_selector="div[class*='AdItem_wrapperAdItem']",
)
print("Running crawler...")
df = crawl_public_site(config)
print("Crawl completed! Rows:", len(df))
print(df[["title", "price", "product_url", "category", "source"]].head(5))
