from pathlib import Path


def test_canonical_market_valuation_has_no_average_cost_fallback_for_listed_assets():
    source = Path("app/services/portfolio_canonical_valuation_service.py").read_text(
        encoding="utf-8"
    )

    assert "prices.get(ticker.upper(), float(average_price))" not in source
    assert "prices[ticker.upper()]" in source
    assert "if real_gaps:" in source
