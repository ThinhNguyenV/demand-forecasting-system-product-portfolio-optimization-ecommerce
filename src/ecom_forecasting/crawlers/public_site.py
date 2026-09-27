from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag


DEFAULT_USER_AGENT = "GraduationResearchBot/1.0 (public-data research crawler)"

MARKET_COLUMNS = [
    "sku",
    "title",
    "category",
    "brand",
    "seller",
    "price",
    "original_price",
    "discount_rate",
    "rating",
    "review_count",
    "sold",
    "is_official_store",
    "official_store_score",
    "product_url",
    "source",
]


@dataclass(frozen=True)
class FieldSelector:
    css: str
    attribute: str | None = None
    default: Any = ""


@dataclass(frozen=True)
class PublicSiteConfig:
    site_name: str
    page_url_template: str
    product_selector: str
    fields: dict[str, FieldSelector]
    pages: int = 1
    start_page: int = 1
    delay_seconds: float = 1.0
    timeout_seconds: int = 20
    user_agent: str = DEFAULT_USER_AGENT
    constants: dict[str, Any] = field(default_factory=dict)
    engine: str = "static"
    wait_selector: str | None = None
    wait_after_load_ms: int = 1000
    scroll_count: int = 0
    scroll_delay_ms: int = 750
    load_more_selector: str | None = None
    load_more_count: int = 0
    headless: bool = True
    @classmethod
    def from_json(cls, path: str | Path) -> "PublicSiteConfig":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        required = {"site_name", "page_url_template", "product_selector", "fields"}
        missing = required.difference(raw)
        if missing:
            raise ValueError(f"Missing public-site config keys: {sorted(missing)}")

        selectors: dict[str, FieldSelector] = {}
        for name, value in raw["fields"].items():
            if isinstance(value, str):
                selectors[name] = FieldSelector(css=value)
            elif isinstance(value, dict) and value.get("css"):
                selectors[name] = FieldSelector(
                    css=str(value["css"]),
                    attribute=value.get("attribute"),
                    default=value.get("default", ""),
                )
            else:
                raise ValueError(f"Invalid selector for field '{name}'")

        config = cls(
            site_name=str(raw["site_name"]),
            page_url_template=str(raw["page_url_template"]),
            product_selector=str(raw["product_selector"]),
            fields=selectors,
            pages=int(raw.get("pages", 1)),
            start_page=int(raw.get("start_page", 1)),
            delay_seconds=float(raw.get("delay_seconds", 1.0)),
            timeout_seconds=int(raw.get("timeout_seconds", 20)),
            user_agent=str(raw.get("user_agent", DEFAULT_USER_AGENT)),
            constants=dict(raw.get("constants", {})),
            engine=str(raw.get("engine", "static")),
            wait_selector=raw.get("wait_selector"),
            wait_after_load_ms=int(raw.get("wait_after_load_ms", 1000)),
            scroll_count=int(raw.get("scroll_count", 0)),
            scroll_delay_ms=int(raw.get("scroll_delay_ms", 750)),
            load_more_selector=raw.get("load_more_selector"),
            load_more_count=int(raw.get("load_more_count", 0)),
            headless=bool(raw.get("headless", True)),
        )
        _validate_config(config)
        return config


def crawl_public_site(config: PublicSiteConfig) -> pd.DataFrame:
    """Crawl public product pages using static HTTP or a Playwright browser."""
    _validate_config(config)
    session = requests.Session()
    session.headers.update({"User-Agent": config.user_agent, "Accept": "text/html,application/xhtml+xml"})
    first_url = config.page_url_template.format(page=config.start_page)
    allowed_origin = _origin(first_url)
    robots = _load_robots_policy(session, first_url, config)
    page_urls = [config.page_url_template.format(page=page) for page in range(config.start_page, config.start_page + config.pages)]
    for page_url in page_urls:
        if _origin(page_url) != allowed_origin:
            raise ValueError("All configured pages must stay on the same origin.")
        if not robots.can_fetch(config.user_agent, page_url):
            raise PermissionError(f"robots.txt does not allow crawling: {page_url}")
    rows = _crawl_with_playwright(config, page_urls) if config.engine == "playwright" else _crawl_static(config, session, page_urls)
    snapshot = pd.DataFrame(rows)
    if snapshot.empty:
        return pd.DataFrame(columns=MARKET_COLUMNS)
    snapshot = normalize_market_snapshot(snapshot, source=config.site_name)
    return snapshot.drop_duplicates(subset=["sku"]).reset_index(drop=True)


def _crawl_static(config: PublicSiteConfig, session: requests.Session, page_urls: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, page_url in enumerate(page_urls):
        response = session.get(page_url, timeout=config.timeout_seconds)
        if response.status_code in {401, 403, 429}:
            raise RuntimeError(_access_error(config, response.status_code))
        response.raise_for_status()
        if "html" not in response.headers.get("Content-Type", "").lower():
            raise ValueError(f"Expected an HTML page, received {response.headers.get('Content-Type', '')}")
        rows.extend(_parse_page(response.text, page_url, config))
        if index < len(page_urls) - 1:
            time.sleep(config.delay_seconds)
    return rows


def _crawl_with_playwright(config: PublicSiteConfig, page_urls: list[str]) -> list[dict[str, Any]]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed. Run 'pip install playwright' and 'python -m playwright install chromium'.") from exc
    rows: list[dict[str, Any]] = []
    timeout_ms = config.timeout_seconds * 1000
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=config.headless)
        context = browser.new_context(user_agent=config.user_agent)
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        try:
            for index, page_url in enumerate(page_urls):
                response = page.goto(page_url, wait_until="domcontentloaded", timeout=timeout_ms)
                status = response.status if response else 0
                if status in {401, 403, 429}:
                    raise RuntimeError(_access_error(config, status))
                if status >= 400:
                    raise RuntimeError(f"{config.site_name} returned HTTP {status}: {page_url}")
                selector = config.wait_selector or config.product_selector
                try:
                    page.wait_for_selector(selector, state="attached", timeout=timeout_ms)
                except PlaywrightTimeoutError as exc:
                    raise ValueError(f"Timed out waiting for selector '{selector}' on {page_url}") from exc
                if config.wait_after_load_ms:
                    page.wait_for_timeout(config.wait_after_load_ms)
                for _ in range(config.scroll_count):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(config.scroll_delay_ms)
                for _ in range(config.load_more_count):
                    button = page.locator(config.load_more_selector).first
                    if not button.is_visible():
                        break
                    button.click()
                    page.wait_for_timeout(config.scroll_delay_ms)
                rows.extend(_parse_page(page.content(), page_url, config))
                if index < len(page_urls) - 1 and config.delay_seconds:
                    page.wait_for_timeout(round(config.delay_seconds * 1000))
        finally:
            context.close()
            browser.close()
    return rows


def _parse_page(html: str, page_url: str, config: PublicSiteConfig) -> list[dict[str, Any]]:
    cards = BeautifulSoup(html, "lxml").select(config.product_selector)
    if not cards:
        raise ValueError(f"No products matched selector '{config.product_selector}' on {page_url}. Check the selector and rendered page structure.")
    return [_parse_product(card, page_url, config) for card in cards]


def _access_error(config: PublicSiteConfig, status: int) -> str:
    return f"{config.site_name} rejected the public request with HTTP {status}. Do not bypass access controls; use an approved API or manual CSV."

def normalize_market_snapshot(snapshot: pd.DataFrame, source: str = "Public website") -> pd.DataFrame:
    data = snapshot.copy()
    defaults: dict[str, Any] = {
        "sku": "",
        "title": "",
        "category": "Unknown",
        "brand": "",
        "seller": "",
        "price": 0.0,
        "original_price": 0.0,
        "discount_rate": 0.0,
        "rating": 0.0,
        "review_count": 0.0,
        "sold": 0.0,
        "is_official_store": False,
        "official_store_score": 0.0,
        "product_url": "",
        "source": source,
    }
    for column, default in defaults.items():
        if column not in data.columns:
            data[column] = default
        data[column] = data[column].fillna(default)

    for column in ["price", "original_price", "discount_rate", "rating", "review_count", "sold"]:
        data[column] = data[column].map(_parse_number).astype(float)
    data["is_official_store"] = data["is_official_store"].map(_parse_bool)
    data["official_store_score"] = data["is_official_store"].astype(float)
    data["source"] = data["source"].replace("", source)
    data["title"] = data["title"].astype(str).str.strip()
    data["category"] = data["category"].astype(str).str.strip().replace("", "Unknown")
    data["sku"] = data.apply(_stable_sku, axis=1)
    return data[MARKET_COLUMNS]


def export_market_portfolio_case(
    snapshot: pd.DataFrame,
    output_path: str | Path,
    top_n: int = 50,
) -> pd.DataFrame:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = normalize_market_snapshot(snapshot)
    if data.empty:
        data.to_csv(output, index=False, encoding="utf-8-sig")
        return data

    data["market_demand_score"] = (
        0.40 * _rank01(data["sold"])
        + 0.25 * _rank01(data["review_count"])
        + 0.20 * (data["rating"].clip(0, 5) / 5)
        + 0.15 * _rank01(data["discount_rate"])
    ).round(4)
    data["estimated_margin_rate"] = (
        0.16
        + 0.10 * _rank01(data["price"])
        - 0.04 * (data["discount_rate"].clip(0, 80) / 80)
    ).clip(0.08, 0.32).round(4)
    demand_proxy = data["sold"].where(data["sold"] > 0, data["review_count"])
    data["expected_profit_proxy"] = (
        data["price"] * demand_proxy * data["estimated_margin_rate"]
    ).round(2)
    data["portfolio_score"] = (
        0.50 * data["market_demand_score"]
        + 0.30 * _rank01(data["expected_profit_proxy"])
        + 0.20 * data["official_store_score"]
    ).round(4)
    data["recommendation"] = data.apply(_recommend_action, axis=1)
    result = data.sort_values("portfolio_score", ascending=False).head(top_n)
    result.to_csv(output, index=False, encoding="utf-8-sig")
    return result


def _parse_product(card: Tag, page_url: str, config: PublicSiteConfig) -> dict[str, Any]:
    row = dict(config.constants)
    for name, selector in config.fields.items():
        node = card.select_one(selector.css)
        if node is None:
            row[name] = selector.default
        elif selector.attribute:
            row[name] = node.get(selector.attribute, selector.default)
        else:
            row[name] = " ".join(node.get_text(" ", strip=True).split())

    if row.get("product_url"):
        row["product_url"] = urljoin(page_url, str(row["product_url"]))
        if _origin(row["product_url"]) != _origin(page_url):
            raise ValueError("Product links must stay on the configured website origin.")
    row["source"] = config.site_name
    return row


def _load_robots_policy(
    session: requests.Session,
    page_url: str,
    config: PublicSiteConfig,
) -> RobotFileParser:
    parsed = urlparse(page_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    response = session.get(robots_url, timeout=config.timeout_seconds)
    parser = RobotFileParser()
    parser.set_url(robots_url)
    if response.status_code == 404:
        parser.parse([])
        return parser
    response.raise_for_status()
    parser.parse(response.text.splitlines())
    crawl_delay = parser.crawl_delay(config.user_agent) or parser.crawl_delay("*")
    if crawl_delay is not None and config.delay_seconds < float(crawl_delay):
        raise ValueError(
            f"Configured delay {config.delay_seconds}s is lower than robots.txt crawl-delay "
            f"{crawl_delay}s."
        )
    return parser


def _validate_config(config: PublicSiteConfig) -> None:
    if config.engine not in {"static", "playwright"}:
        raise ValueError("engine must be 'static' or 'playwright'")
    if config.pages <= 0:
        raise ValueError("pages must be positive")
    if config.delay_seconds < 0:
        raise ValueError("delay_seconds cannot be negative")
    if min(config.wait_after_load_ms, config.scroll_count, config.scroll_delay_ms, config.load_more_count) < 0:
        raise ValueError("Dynamic crawl timing and action counts cannot be negative")
    if config.load_more_count and not config.load_more_selector:
        raise ValueError("load_more_selector is required when load_more_count is positive")
    if config.pages > 1 and "{page}" not in config.page_url_template:
        raise ValueError("Multi-page crawling requires a '{page}' placeholder in the URL")
    parsed = urlparse(config.page_url_template.format(page=config.start_page))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Only absolute HTTP(S) public page URLs are supported")
    if "title" not in config.fields:
        raise ValueError("A title field selector is required")

def _origin(value: str) -> tuple[str, str]:
    parsed = urlparse(value)
    return parsed.scheme.lower(), parsed.netloc.lower()


def _parse_number(value: Any) -> float:
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    text = str(value or "").strip().lower()
    rating_words = {"one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0}
    for word, rating in rating_words.items():
        if re.search(rf"\b{word}\b", text):
            return rating
    multiplier = 1.0
    if re.search(r"\d(?:[.,]\d+)?\s*k\b", text):
        multiplier = 1_000.0
    elif re.search(r"\d(?:[.,]\d+)?\s*m\b", text):
        multiplier = 1_000_000.0

    match = re.search(r"-?\d[\d.,]*", text)
    if not match:
        return 0.0
    number = match.group(0)
    if "," in number and "." in number:
        decimal = "." if number.rfind(".") > number.rfind(",") else ","
        thousands = "," if decimal == "." else "."
        number = number.replace(thousands, "").replace(decimal, ".")
    elif number.count(",") == 1 and len(number.rsplit(",", 1)[1]) <= 2:
        number = number.replace(",", ".")
    else:
        number = number.replace(",", "").replace(".", "") if number.count(".") > 1 else number
    try:
        return float(number) * multiplier
    except ValueError:
        return 0.0


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "official", "verified"}


def _stable_sku(row: pd.Series) -> str:
    sku = str(row.get("sku", "")).strip()
    if sku:
        return sku
    identity = f"{row.get('product_url', '')}|{row.get('title', '')}"
    return hashlib.sha1(identity.encode("utf-8")).hexdigest()[:20]


def _rank01(series: pd.Series) -> pd.Series:
    return series.rank(pct=True).fillna(0)


def _recommend_action(row: pd.Series) -> str:
    if row["portfolio_score"] >= 0.8 and row["rating"] >= 4.0:
        return "High-priority public-market candidate"
    if row["market_demand_score"] >= 0.65:
        return "Monitor demand, price and competition"
    return "Use as a long-tail market benchmark"
