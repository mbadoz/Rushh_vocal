import pytest
from api.costs import cost, percentile, compare


def test_cache_not_counted_twice_and_fx():
    result = cost(
        {"model": {"input_tokens": 1000, "cached_tokens": 200, "output_tokens": 100}},
        {
            "model": {
                "currency": "USD",
                "rates": {
                    "input_tokens": 0.001,
                    "cached_tokens": 0.0001,
                    "output_tokens": 0.002,
                },
            }
        },
        0.9,
    )
    assert result["eur"] == pytest.approx((0.8 + 0.02 + 0.2) * 0.9)
    assert result["complete"]


def test_missing_is_not_free():
    result = cost({"x": {"seconds": 60}}, {}, 1)
    assert (
        result["eur"] == 0
        and not result["complete"]
        and result["missing"] == ["x/seconds"]
    )
    assert cost(
        {"x": {"seconds": 60}}, {"x": {"rates": {"seconds": 0}, "currency": "EUR"}}, 1
    )["complete"]


def test_weighted_cost_and_percentiles():
    rows = [
        dict(
            status="completed",
            composition_version="v",
            config={"name": "A"},
            duration=d,
            cost={"eur": c, "complete": True},
            turns=[{"latency_ms": l}],
            rating=5,
            id=str(d),
        )
        for d, c, l in [(60, 1, 100), (120, 1, 1000)]
    ]
    result = compare(rows)[0]
    assert result["eur_per_min"] == pytest.approx(2 / 3)
    assert result["median_ms"] == 550 and result["p95_ms"] == 955
    assert percentile([], 0.5) is None


def test_cache_creation_excluded_from_normal_input():
    result = cost(
        {
            "m": {
                "input_tokens": 1000,
                "cached_tokens": 100,
                "cache_creation_tokens": 200,
            }
        },
        {
            "m": {
                "currency": "EUR",
                "rates": {
                    "input_tokens": 0.001,
                    "cached_tokens": 0.0001,
                    "cache_creation_tokens": 0.002,
                },
            }
        },
        1,
    )
    assert result["eur"] == pytest.approx(0.7 + 0.01 + 0.4)
