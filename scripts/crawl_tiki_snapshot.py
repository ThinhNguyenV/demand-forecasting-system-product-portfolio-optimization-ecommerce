from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecom_forecasting.config import PipelinePaths, ensure_directories
from ecom_forecasting.tiki_case import (
    TikiScrapeConfig,
    crawl_tiki_snapshot,
    export_tiki_portfolio_case,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a lightweight Tiki VN snapshot for portfolio case study.")
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=["tai nghe", "ban phim", "chuot may tinh", "sac du phong"],
        help="Vietnamese search keywords.",
    )
    parser.add_argument("--pages", type=int, default=2, help="Pages per keyword.")
    parser.add_argument("--limit", type=int, default=40, help="Items per page.")
    parser.add_argument("--top-n", type=int, default=50, help="Rows in portfolio case output.")
    args = parser.parse_args()

    ensure_directories()
    paths = PipelinePaths()
    snapshot = crawl_tiki_snapshot(
        TikiScrapeConfig(
            keywords=tuple(args.keywords),
            pages_per_keyword=args.pages,
            limit=args.limit,
        )
    )
    snapshot.to_csv(paths.tiki_snapshot, index=False, encoding="utf-8-sig")
    case = export_tiki_portfolio_case(snapshot, paths.tiki_portfolio_case, top_n=args.top_n)
    print(f"Tiki snapshot rows: {len(snapshot)}")
    print(f"Tiki portfolio case rows: {len(case)}")
    print(f"Snapshot file: {paths.tiki_snapshot}")
    print(f"Portfolio case file: {paths.tiki_portfolio_case}")


if __name__ == "__main__":
    main()
