import pytest

from tokentoll.pricing import engine


@pytest.fixture(autouse=True)
def _bundled_pricing_only(tmp_path, monkeypatch):
    """Run every test against the bundled pricing file.

    Without this, PricingEngine reads ~/.tokentoll or fetches live LiteLLM data,
    so results depend on the machine and on upstream model removals.
    """
    monkeypatch.setattr(engine, "_CACHE_FILE", tmp_path / "model_prices.json")
    monkeypatch.setattr(engine, "_CACHE_META", tmp_path / "cache_meta.json")
    monkeypatch.setattr(engine.PricingEngine, "_try_fetch_and_cache", lambda self: False)
