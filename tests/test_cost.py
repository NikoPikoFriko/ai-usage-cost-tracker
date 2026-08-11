from pathlib import Path

from src.cost import compute_cost_usd, load_pricing, price_event_fields, resolve_rate

ROOT = Path(__file__).resolve().parents[1]
PRICING = ROOT / "config" / "PRICING_MODELS.csv"


def test_compute_cost_with_cache():
    rates = load_pricing(PRICING)
    rate = resolve_rate(rates, "gpt-5.6-terra")
    assert rate is not None
    # 1M uncached in @2 + 0 out = $2
    c = compute_cost_usd(1_000_000, 0, rate, cached_input_tokens=0)
    assert abs(c - 2.0) < 1e-6
    # all cached @0.20
    c2 = compute_cost_usd(1_000_000, 0, rate, cached_input_tokens=1_000_000)
    assert abs(c2 - 0.2) < 1e-6


def test_reasoning_not_double_counted():
    rates = load_pricing(PRICING)
    rate = resolve_rate(rates, "gpt-5")
    # output already includes reasoning
    c = compute_cost_usd(0, 1_000_000, rate)
    assert abs(c - 10.0) < 1e-6


def test_unknown_model_gap():
    rates = load_pricing(PRICING)
    p = price_event_fields(rates, "not-a-real-model", "2026-08-10T00:00:00Z", 100, 50)
    assert p["priced"] is False
    assert p["cost_usd"] is None


def test_price_known_model():
    rates = load_pricing(PRICING)
    p = price_event_fields(
        rates,
        "gpt-5.6-terra",
        "2026-08-10T00:00:00Z",
        input_tokens=1000,
        output_tokens=500,
        cached_input_tokens=200,
    )
    assert p["priced"] is True
    assert p["cost_usd"] is not None
    assert p["cost_usd"] > 0
