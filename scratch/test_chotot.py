from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    url = "https://www.chotot.com/do-dien-tu"
    print("Navigating to", url)
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(4000)

    # Let's inspect a product card
    cards = page.query_selector_all("div[class*='AdItem_wrapperAdItem']")
    if not cards:
        cards = page.query_selector_all("div[class*='AdItem']")
    print(f"Found {len(cards)} cards")
    if cards:
        html = cards[0].inner_html()
        soup = BeautifulSoup(html, "lxml")
        print("\n=== Inner HTML of first card ===")
        print(html[:1000])
        print("\n=== Elements inside card ===")
        for tag in soup.find_all(['h3', 'span', 'p', 'a', 'div']):
            cls = tag.get('class', [])
            txt = tag.get_text(strip=True)
            if txt and len(txt) < 80:
                print(f"  <{tag.name} class='{' '.join(cls)}'> : {txt}")

    browser.close()
