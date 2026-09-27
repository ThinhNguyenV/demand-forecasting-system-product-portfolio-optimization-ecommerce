from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.chotot.com/do-dien-tu", wait_until="domcontentloaded")
    print("Testing wait_for_selector...")
    el = page.wait_for_selector("a[href*='.htm']", timeout=15000)
    print("a[href*='.htm'] found:", el is not None)
    el2 = page.wait_for_selector("div[class*='AdItem']", timeout=15000)
    print("div[class*='AdItem'] found:", el2 is not None)
    browser.close()
