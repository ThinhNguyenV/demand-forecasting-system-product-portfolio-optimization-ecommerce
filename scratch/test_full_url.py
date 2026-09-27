import sys
sys.path.insert(0, "src")
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

url = "https://www.chotot.com/do-dien-tu?_ga=2.1790384361535.1689839662.1790384350&ctfp=c4e075ee-b2c0-4276-afa0-460433e11fa4&event_source=ct_home_highlight_category"

# Test 1: Static
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
soup = BeautifulSoup(r.text, "lxml")
cards_static = soup.select("div[class*='AdItem']")
print(f"Test 1 (Static): cards count = {len(cards_static)}")

# Test 2: Playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    cards_pw = page.query_selector_all("div[class*='AdItem']")
    print(f"Test 2 (Playwright): cards count = {len(cards_pw)}")
    browser.close()
