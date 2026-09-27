from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


@dataclass(frozen=True)
class ScrapeConfig:
    base_url: str = "https://books.toscrape.com/"
    pages: int = 5
    delay_seconds: float = 0.5
    timeout_seconds: int = 20


def scrape_books_to_scrape(config: ScrapeConfig) -> pd.DataFrame:
    """Scrape public product listing pages from books.toscrape.com."""
    rows: list[dict[str, object]] = []
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; GraduationResearchBot/1.0; "
                "+https://example.edu/research)"
            )
        }
    )

    for page in range(1, config.pages + 1):
        page_url = urljoin(config.base_url, f"catalogue/page-{page}.html")
        response = session.get(page_url, timeout=config.timeout_seconds)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        for card in soup.select("article.product_pod"):
            product = _parse_product_card(card, page_url)
            product["category"] = _fetch_product_category(
                session,
                str(product["product_url"]),
                timeout_seconds=config.timeout_seconds,
            )
            rows.append(product)

        time.sleep(config.delay_seconds)

    return pd.DataFrame(rows)


def _parse_product_card(card: BeautifulSoup, page_url: str) -> dict[str, object]:
    title_link = card.select_one("h3 a")
    title = title_link.get("title", "").strip() if title_link else ""
    product_url = urljoin(page_url, title_link.get("href", "")) if title_link else ""
    price_text = _text(card.select_one(".price_color"))
    stock_text = _text(card.select_one(".availability"))
    rating_class = _extract_rating_class(card)

    return {
        "sku": _slugify(title),
        "title": title,
        "category": "Unknown",
        "price": _parse_price(price_text),
        "rating": RATING_MAP.get(rating_class, 0),
        "stock_status": stock_text,
        "in_stock": "in stock" in stock_text.lower(),
        "product_url": product_url,
        "source_page": page_url,
    }


def _fetch_product_category(
    session: requests.Session,
    product_url: str,
    timeout_seconds: int,
) -> str:
    try:
        response = session.get(product_url, timeout=timeout_seconds)
        response.raise_for_status()
    except requests.RequestException:
        return "Unknown"

    soup = BeautifulSoup(response.text, "lxml")
    breadcrumb_links = [
        _text(link)
        for link in soup.select("ul.breadcrumb li a")
        if _text(link) not in {"Home", "Books"}
    ]
    return breadcrumb_links[-1] if breadcrumb_links else "Books"


def _extract_rating_class(card: BeautifulSoup) -> str:
    rating = card.select_one("p.star-rating")
    if not rating:
        return ""
    classes: Iterable[str] = rating.get("class", [])
    return next((item for item in classes if item in RATING_MAP), "")


def _parse_price(value: str) -> float:
    match = re.search(r"[\d.]+", value)
    return float(match.group(0)) if match else 0.0


def _text(node: BeautifulSoup | None) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "unknown-product"
