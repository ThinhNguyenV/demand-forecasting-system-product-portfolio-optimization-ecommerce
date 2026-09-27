from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecom_forecasting.config import ensure_directories
from ecom_forecasting.crawlers import (
    FieldSelector,
    PublicSiteConfig,
    crawl_public_site,
    export_market_portfolio_case,
)


def _pairs(values: list[str], option: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"{option} value must use NAME=VALUE: {value}")
        name, item = value.split("=", 1)
        name = name.strip()
        if not name or not item.strip():
            raise ValueError(f"{option} value must use non-empty NAME=VALUE: {value}")
        result[name] = item.strip()
    return result


def _config_from_arguments(args: argparse.Namespace) -> PublicSiteConfig:
    if not args.url:
        raise ValueError("Provide a JSON config path or use --url for direct mode.")
    if not args.product_selector:
        raise ValueError("Direct mode requires --product-selector.")

    field_values = _pairs(args.field, "--field")
    attributes = _pairs(args.attribute, "--attribute")
    constants = _pairs(args.constant, "--constant")
    if "title" not in field_values:
        raise ValueError("Direct mode requires at least --field title=CSS_SELECTOR.")

    unknown_attributes = set(attributes).difference(field_values)
    if unknown_attributes:
        raise ValueError(
            f"--attribute refers to fields not declared with --field: {sorted(unknown_attributes)}"
        )

    fields = {
        name: FieldSelector(css=css, attribute=attributes.get(name))
        for name, css in field_values.items()
    }
    domain = urlparse(args.url).netloc
    return PublicSiteConfig(
        site_name=args.site_name or domain or "Public website",
        page_url_template=args.url,
        product_selector=args.product_selector,
        fields=fields,
        pages=args.pages,
        start_page=args.start_page,
        delay_seconds=args.delay,
        timeout_seconds=args.timeout,
        constants=constants,
        engine=args.engine,
        wait_selector=args.wait_selector,
        wait_after_load_ms=args.wait_after_load_ms,
        scroll_count=args.scroll_count,
        scroll_delay_ms=args.scroll_delay_ms,
        load_more_selector=args.load_more_selector,
        load_more_count=args.load_more_count,
        headless=not args.show_browser,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Crawl a public product website using static HTTP or a Playwright browser. "
            "The crawler respects robots.txt and does not bypass access controls."
        )
    )
    parser.add_argument("config", nargs="?", type=Path, help="Optional public-site JSON config. Omit it when using --url direct mode.")
    parser.add_argument("--url", help="Listing-page URL or template, e.g. https://shop.test?page={page}.")
    parser.add_argument("--site-name", help="Source name stored in the snapshot.")
    parser.add_argument("--product-selector", help="CSS selector matching each product card.")
    parser.add_argument("--field", action="append", default=[], metavar="NAME=CSS", help="Field selector; repeat for title, price, rating, sold, product_url, etc.")
    parser.add_argument("--attribute", action="append", default=[], metavar="NAME=ATTRIBUTE", help="Read an HTML attribute for a declared field, e.g. product_url=href.")
    parser.add_argument("--constant", action="append", default=[], metavar="NAME=VALUE", help="Constant field value, e.g. category=Books.")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages in direct mode.")
    parser.add_argument("--start-page", type=int, default=1, help="First page number.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between page requests.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP or browser timeout in seconds.")
    parser.add_argument("--engine", choices=["static", "playwright"], default="static")
    parser.add_argument("--wait-selector", help="Selector to wait for after JavaScript rendering.")
    parser.add_argument("--wait-after-load-ms", type=int, default=1000)
    parser.add_argument("--scroll-count", type=int, default=0, help="Full-page lazy-load scrolls.")
    parser.add_argument("--scroll-delay-ms", type=int, default=750)
    parser.add_argument("--load-more-selector", help="Optional button selector to click repeatedly.")
    parser.add_argument("--load-more-count", type=int, default=0)
    parser.add_argument("--show-browser", action="store_true", help="Show Chromium while crawling.")
    parser.add_argument("--snapshot-output", type=Path, default=ROOT / "data" / "raw" / "public_market_snapshot.csv", help="Normalized public market snapshot CSV.")
    parser.add_argument("--case-output", type=Path, default=ROOT / "data" / "outputs" / "public_market_case.csv", help="Ranked public market portfolio CSV.")
    parser.add_argument("--top-n", type=int, default=50, help="Rows in portfolio case output.")
    args = parser.parse_args()

    if args.config and args.url:
        parser.error("Use either a JSON config or --url direct mode, not both.")
    try:
        config = PublicSiteConfig.from_json(args.config) if args.config else _config_from_arguments(args)
    except ValueError as exc:
        parser.error(str(exc))

    ensure_directories()
    snapshot = crawl_public_site(config)
    args.snapshot_output.parent.mkdir(parents=True, exist_ok=True)
    snapshot.to_csv(args.snapshot_output, index=False, encoding="utf-8-sig")
    case = export_market_portfolio_case(snapshot, args.case_output, top_n=args.top_n)
    print(f"Source: {config.site_name}")
    print(f"Engine: {config.engine}")
    print(f"Snapshot rows: {len(snapshot)}")
    print(f"Portfolio case rows: {len(case)}")
    print(f"Snapshot file: {args.snapshot_output.resolve()}")
    print(f"Portfolio case file: {args.case_output.resolve()}")

if __name__ == "__main__":
    main()
