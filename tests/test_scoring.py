from datetime import date, timedelta

import pandas as pd

from src.scoring import (
    anomaly_composite,
    looks_like_corporate_action,
    avg_traded_value,
    divergence_pct,
    explained_tag,
    is_liquid,
    modified_z,
    valuation_gap,
    volume_anomaly,
)


def make_prices(volumes, closes=None, price=1000):
    n = len(volumes)
    start = date(2026, 9, 1)
    return pd.DataFrame({
        "date": [start + timedelta(days=i) for i in range(n)],
        "close": closes if closes is not None else [price] * n,
        "volume": volumes,
    })


def test_modified_z_is_robust_to_single_outlier_in_baseline():
    baseline = pd.Series([100, 101, 99, 102, 98, 100, 103, 97, 100, 5000])
    assert abs(modified_z(baseline, 100)) < 1
    assert modified_z(baseline, 1000) > 3.5


def test_modified_z_constant_baseline_flags_deviation():
    assert modified_z(pd.Series([50] * 20), 50) == 0.0
    assert modified_z(pd.Series([50] * 20), 500) > 3.5


def test_volume_anomaly_flags_spike():
    vols = [1_000_000] * 20 + [9_000_000]
    result = volume_anomaly(make_prices(vols))
    assert result["is_anomaly"] is True
    assert result["volume_ratio"] == 9.0


def test_volume_anomaly_no_spike_not_flagged():
    vols = [1_000_000 + i * 1000 for i in range(21)]
    assert volume_anomaly(make_prices(vols))["is_anomaly"] is False


def test_liquidity_filter_threshold():
    illiquid = make_prices([1000] * 25, price=500)
    liquid = make_prices([2_000_000] * 25, price=1000)
    assert avg_traded_value(illiquid) == 500_000
    assert is_liquid(illiquid) is False
    assert is_liquid(liquid) is True


def test_liquidity_requires_full_baseline():
    assert is_liquid(make_prices([10_000_000] * 5)) is False


def test_divergence_needs_minimum_peers():
    assert divergence_pct(0.05, [0.01, 0.0]) is None
    assert divergence_pct(0.05, [0.01, 0.0, 0.02]) == (0.05 - 0.01) * 100


def test_composite_bounds():
    assert anomaly_composite(0, None) == 0
    assert anomaly_composite(50, 50) == 100


def test_explained_tag():
    q = [date(2026, 6, 30)]
    assert explained_tag(date(2026, 7, 1), q, True) == "Explained"
    assert explained_tag(date(2026, 8, 15), q, True) == "Unexplained"
    assert explained_tag(date(2026, 8, 15), q, False) == "Normal"


def _report(target_pe, target_pb, target_roe, peers):
    rows = [{"symbol": "AAA.JK", "market_cap": 1e12, "pe_ttm": target_pe, "pb_mrq": target_pb,
             "net_income": target_roe * 100, "total_equity": 100}]
    for i, (pe, pb, roe_, mcap) in enumerate(peers):
        rows.append({"symbol": f"P{i}.JK", "market_cap": mcap, "pe_ttm": pe, "pb_mrq": pb,
                     "net_income": roe_ * 100, "total_equity": 100})
    return {"peers": [{"peers_data": {"companies": rows}}]}


def test_gap_cheap_and_high_quality_is_undervalued():
    peers = [(15, 2.0, 0.10, 1e12), (16, 2.2, 0.12, 2e12), (14, 1.9, 0.11, 0.5e12), (18, 2.5, 0.09, 3e12)]
    res = valuation_gap(_report(7, 0.8, 0.20, peers), "AAA.JK")
    assert res["gap_label"] == "Potentially Undervalued"
    assert res["peer_count"] == 4


def test_gap_cheap_but_low_roe_is_value_trap():
    peers = [(15, 2.0, 0.20, 1e12), (16, 2.2, 0.18, 2e12), (14, 1.9, 0.19, 0.5e12)]
    res = valuation_gap(_report(7, 0.8, 0.05, peers), "AAA.JK")
    assert res["gap_label"] == "Value Trap Risk"


def test_gap_excludes_peers_outside_market_cap_tier():
    peers = [(15, 2.0, 0.1, 1e12), (16, 2.2, 0.1, 1e12), (14, 1.9, 0.1, 1e12),
             (30, 5.0, 0.1, 1e14)]  # 100x larger, excluded
    res = valuation_gap(_report(7, 0.8, 0.2, peers), "AAA.JK")
    assert res["peer_count"] == 3


def test_gap_insufficient_peers():
    res = valuation_gap(_report(7, 0.8, 0.2, [(15, 2.0, 0.1, 1e12)]), "AAA.JK")
    assert res["gap"] is None
    assert res["gap_label"] == "Data peer tidak cukup"


def test_gap_negative_earnings_target_is_not_scored():
    peers = [(15, 2.0, 0.1, 1e12), (16, 2.2, 0.1, 1e12), (14, 1.9, 0.1, 1e12)]
    res = valuation_gap(_report(-4, 0.8, -0.1, peers), "AAA.JK")
    assert res["gap"] is None



def test_corporate_action_detected_from_large_daily_move():
    split = make_prices([1_000_000] * 25, closes=[2560] * 22 + [176, 180, 182])
    assert looks_like_corporate_action(split) is True
    normal = make_prices([1_000_000] * 25, closes=[1000 + i for i in range(25)])
    assert looks_like_corporate_action(normal) is False
