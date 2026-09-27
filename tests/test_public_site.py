import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecom_forecasting.crawlers.public_site import (
    PublicSiteConfig,
    _parse_product,
    _parse_page,
    normalize_market_snapshot,
)


def test_public_site_config_and_product_parser(tmp_path):
    config_path = tmp_path / "site.json"
    config_path.write_text(
        json.dumps(
            {
                "site_name": "Example Shop",
                "page_url_template": "https://example.com/products?page={page}",
                "product_selector": ".product",
                "fields": {
                    "title": ".title",
                    "price": ".price",
                    "product_url": {"css": "a", "attribute": "href"},
                    "rating": {"css": ".rating", "attribute": "data-value", "default": 0},
                },
                "constants": {"category": "Books"},
            }
        ),
        encoding="utf-8",
    )
    config = PublicSiteConfig.from_json(config_path)
    card = BeautifulSoup(
        '<article class="product"><a href="/p/1"><span class="title">A Book</span></a>'
        '<span class="price">$12.50</span><span class="rating" data-value="4.5"></span></article>',
        "lxml",
    ).select_one(".product")

    result = _parse_product(card, "https://example.com/products?page=1", config)
    normalized = normalize_market_snapshot(pd.DataFrame([result]), source=config.site_name)

    assert result["product_url"] == "https://example.com/p/1"
    assert normalized.iloc[0]["title"] == "A Book"
    assert normalized.iloc[0]["price"] == 12.5
    assert normalized.iloc[0]["rating"] == 4.5
    assert normalized.iloc[0]["category"] == "Books"
    assert normalized.iloc[0]["source"] == "Example Shop"


def test_public_site_config_rejects_non_http_url(tmp_path):
    config_path = tmp_path / "site.json"
    config_path.write_text(
        json.dumps(
            {
                "site_name": "Local files",
                "page_url_template": "file:///tmp/page-{page}.html",
                "product_selector": ".product",
                "fields": {"title": ".title"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="HTTP"):
        PublicSiteConfig.from_json(config_path)


def test_dynamic_config_and_rendered_html_parser(tmp_path):
    config_path = tmp_path / "dynamic.json"
    config_path.write_text(
        json.dumps(
            {
                "site_name": "Dynamic Shop",
                "page_url_template": "https://example.com/products",
                "product_selector": ".card",
                "engine": "playwright",
                "wait_selector": ".card",
                "scroll_count": 3,
                "load_more_selector": "button.more",
                "load_more_count": 2,
                "fields": {"title": ".name", "price": ".price"},
            }
        ),
        encoding="utf-8",
    )
    config = PublicSiteConfig.from_json(config_path)
    rows = _parse_page(
        '<div class="card"><span class="name">Rendered item</span>'
        '<span class="price">199,000 VND</span></div>',
        "https://example.com/products",
        config,
    )
    assert config.engine == "playwright"
    assert config.scroll_count == 3
    assert rows[0]["title"] == "Rendered item"


def test_dynamic_config_requires_load_more_selector(tmp_path):
    config_path = tmp_path / "invalid-dynamic.json"
    config_path.write_text(
        json.dumps(
            {
                "site_name": "Dynamic Shop",
                "page_url_template": "https://example.com/products",
                "product_selector": ".card",
                "engine": "playwright",
                "load_more_count": 1,
                "fields": {"title": ".name"},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="load_more_selector"):
        PublicSiteConfig.from_json(config_path)