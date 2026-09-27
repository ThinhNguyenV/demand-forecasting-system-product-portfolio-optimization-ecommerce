import sys
sys.path.insert(0, "src")
from ecom_forecasting.crawlers import PublicSiteConfig, FieldSelector, crawl_public_site

config = PublicSiteConfig(
    site_name="Chợ Tốt - Đồ điện tử",
    page_url_template="https://www.chotot.com/do-dien-tu",
    product_selector="div[class*='AdItem']",
    fields={
        "title": FieldSelector(css="[class*='adTitle']"),
        "price": FieldSelector(css="[class*='price']"),
        "product_url": FieldSelector(css="a[href*='.htm']", attribute="href"),
    },
    constants={"category": "Đồ điện tử"},
    pages=1,
    engine="playwright",
    timeout_seconds=30,
    wait_selector="a[href*='.htm']",
    wait_after_load_ms=2000,
)
print("Crawling Chợ Tốt with Playwright...")
df = crawl_public_site(config)
print(f"SUCCESS! Extracted {len(df)} items.")
print(df[["title", "price", "product_url", "source"]].head(5))
