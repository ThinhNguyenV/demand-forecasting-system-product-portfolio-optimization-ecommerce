import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_subpackage_imports():
    """Verify that all modular business subpackages are importable."""
    from ecom_forecasting.crawlers import crawl_public_site, crawl_tiki_snapshot, scrape_books_to_scrape
    from ecom_forecasting.crawlers.public_site import PublicSiteConfig
    from ecom_forecasting.data import (
        aggregate_enriched_items_by_category,
        build_olist_inputs,
        clean_products,
        create_eda_charts,
    )
    from ecom_forecasting.models import (
        backtest_demand,
        benchmark_forecast_models,
        explain_global_random_forest,
        forecast_demand,
        forecast_series,
        reconcile_sku_to_category_forecast,
    )
    from ecom_forecasting.optimization import optimize_portfolio
    from ecom_forecasting.services import PipelineResult, export_dashboard_datasets, run_pipeline

    assert callable(crawl_public_site)
    assert callable(crawl_tiki_snapshot)
    assert callable(scrape_books_to_scrape)
    assert callable(build_olist_inputs)
    assert callable(clean_products)
    assert callable(aggregate_enriched_items_by_category)
    assert callable(create_eda_charts)
    assert callable(forecast_demand)
    assert callable(forecast_series)
    assert callable(backtest_demand)
    assert callable(benchmark_forecast_models)
    assert callable(explain_global_random_forest)
    assert callable(reconcile_sku_to_category_forecast)
    assert callable(optimize_portfolio)
    assert callable(run_pipeline)
    assert callable(export_dashboard_datasets)
    assert PublicSiteConfig is not None
    assert PipelineResult is not None


def test_root_package_exports():
    """Verify that ecom_forecasting exports subpackages and core utilities."""
    import ecom_forecasting as pkg

    assert hasattr(pkg, "data")
    assert hasattr(pkg, "models")
    assert hasattr(pkg, "optimization")
    assert hasattr(pkg, "crawlers")
    assert hasattr(pkg, "services")
    assert hasattr(pkg, "PipelinePaths")
    assert hasattr(pkg, "run_pipeline")


def test_no_redundant_root_files():
    """Ensure no leftover shim or redundant files remain in src/ecom_forecasting/."""
    pkg_dir = ROOT / "src" / "ecom_forecasting"
    expected_root_files = {"__init__.py", "config.py"}
    expected_root_dirs = {"data", "models", "optimization", "crawlers", "services", "__pycache__"}

    actual_files = {p.name for p in pkg_dir.iterdir() if p.is_file()}
    actual_dirs = {p.name for p in pkg_dir.iterdir() if p.is_dir()}

    assert actual_files == expected_root_files, f"Unexpected root files found: {actual_files - expected_root_files}"
    assert actual_dirs.issubset(expected_root_dirs), f"Unexpected directories: {actual_dirs - expected_root_dirs}"

    # Also check optimization/ has no duplicate optimization.py
    opt_files = {p.name for p in (pkg_dir / "optimization").iterdir() if p.is_file()}
    assert "optimization.py" not in opt_files, "Redundant optimization.py still exists in optimization/"
