from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecom_forecasting.config import PipelinePaths, ensure_directories
from ecom_forecasting.crawlers import export_tiki_portfolio_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Tiki portfolio case from a manual/crawled CSV snapshot.")
    parser.add_argument("input_csv", type=Path, help="Tiki snapshot CSV path.")
    parser.add_argument("--top-n", type=int, default=50, help="Rows in portfolio case output.")
    args = parser.parse_args()

    ensure_directories()
    paths = PipelinePaths()
    snapshot = pd.read_csv(args.input_csv)
    snapshot.to_csv(paths.tiki_snapshot, index=False, encoding="utf-8-sig")
    case = export_tiki_portfolio_case(snapshot, paths.tiki_portfolio_case, top_n=args.top_n)
    print(f"Tiki snapshot rows: {len(snapshot)}")
    print(f"Tiki portfolio case rows: {len(case)}")
    print(f"Snapshot file: {paths.tiki_snapshot}")
    print(f"Portfolio case file: {paths.tiki_portfolio_case}")


if __name__ == "__main__":
    main()
