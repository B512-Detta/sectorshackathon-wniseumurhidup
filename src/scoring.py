from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd

Z_THRESHOLD = 3.5
LIQUIDITY_MIN_IDR = 1_000_000_000
BASELINE_DAYS = 20
PEER_CAP_RATIO = 5.0
MIN_PEERS = 3
EARNINGS_WINDOW_DAYS = 2
CHEAP_GAP_THRESHOLD = 50.0
VOLUME_Z_FULL_SCORE = 10.0
DIVERGENCE_PCT_FULL_SCORE = 5.0
CORPORATE_ACTION_MOVE = 0.35


def modified_z(baseline: pd.Series, value: float) -> float:
    med = float(baseline.median())
    if med == 0 or np.isnan(med):
        return 0.0
    mad = float((baseline - med).abs().median())
    if mad == 0:
        mean_ad = float((baseline - med).abs().mean())
        mad = 1.253314 * mean_ad if mean_ad > 0 else 0.01 * med
    return 0.6745 * (value - med) / mad


def avg_traded_value(prices: pd.DataFrame) -> float:
    tail = prices.tail(BASELINE_DAYS)
    return float((tail["close"] * tail["volume"]).mean())


def is_liquid(prices: pd.DataFrame) -> bool:
    return len(prices) >= BASELINE_DAYS and avg_traded_value(prices) >= LIQUIDITY_MIN_IDR


def looks_like_corporate_action(prices: pd.DataFrame) -> bool:
    moves = prices["close"].pct_change().abs()
    return bool((moves > CORPORATE_ACTION_MOVE).any())


def volume_anomaly(prices: pd.DataFrame) -> dict:
    today = prices.iloc[-1]
    baseline = prices["volume"].iloc[-(BASELINE_DAYS + 1):-1]
    z = modified_z(baseline, float(today["volume"]))
    base_median = float(baseline.median())
    ret_1d = float(today["close"] / prices["close"].iloc[-2] - 1) if len(prices) >= 2 else 0.0
    return {
        "date": pd.Timestamp(today["date"]).date(),
        "volume": float(today["volume"]),
        "volume_median_20d": base_median,
        "volume_ratio": float(today["volume"]) / base_median if base_median else np.nan,
        "volume_z": z,
        "ret_1d": ret_1d,
        "is_anomaly": bool(abs(z) > Z_THRESHOLD),
    }


def divergence_pct(stock_ret: float, peer_rets: list[float]) -> Optional[float]:
    if len(peer_rets) < MIN_PEERS:
        return None
    return (stock_ret - float(np.median(peer_rets))) * 100


def anomaly_composite(z: float, div_pct: Optional[float]) -> float:
    vol_score = min(abs(z) / VOLUME_Z_FULL_SCORE, 1.0) * 100
    div_score = 0.0 if div_pct is None else min(abs(div_pct) / DIVERGENCE_PCT_FULL_SCORE, 1.0) * 100
    return 0.5 * vol_score + 0.5 * div_score


def explained_tag(anomaly_date: date, quarter_dates: list[date], is_anomaly: bool) -> str:
    if not is_anomaly:
        return "Normal"
    window = timedelta(days=EARNINGS_WINDOW_DAYS)
    if any(abs(anomaly_date - q) <= window for q in quarter_dates):
        return "Explained"
    return "Unexplained"


def peer_frame(report: dict) -> pd.DataFrame:
    companies = report.get("peers", [{}])[0].get("peers_data", {}).get("companies", [])
    df = pd.DataFrame(companies)
    if df.empty:
        return df
    return df[["symbol", "market_cap", "pe_ttm", "pb_mrq", "net_income", "total_equity"]].copy()


def roe(net_income, total_equity) -> Optional[float]:
    if net_income is None or not total_equity:
        return None
    return float(net_income) / float(total_equity)


def valuation_gap(report: dict, ticker: str) -> dict:
    df = peer_frame(report)
    empty = {"gap": None, "gap_label": "Data peer tidak cukup", "peer_count": 0,
             "pe": None, "pb": None, "roe": None, "peer_roe_median": None}
    if df.empty:
        return empty

    self_row = df[df["symbol"] == ticker]
    if self_row.empty:
        return empty
    me = self_row.iloc[0]
    if not (me["pe_ttm"] > 0 and me["pb_mrq"] > 0):
        empty.update(pe=me["pe_ttm"], pb=me["pb_mrq"])
        return empty
    peers = df[(df["symbol"] != ticker)
               & (df["market_cap"] > 0)
               & (df["market_cap"] <= me["market_cap"] * PEER_CAP_RATIO)
               & (df["market_cap"] >= me["market_cap"] / PEER_CAP_RATIO)]
    peers = peers[(peers["pe_ttm"] > 0) & (peers["pb_mrq"] > 0)]
    empty["peer_count"] = len(peers)
    empty.update(pe=me["pe_ttm"], pb=me["pb_mrq"])
    if len(peers) < MIN_PEERS:
        return empty

    pct_pe = (peers["pe_ttm"] > me["pe_ttm"]).mean() * 100
    pct_pb = (peers["pb_mrq"] > me["pb_mrq"]).mean() * 100
    gap = (pct_pe + pct_pb) / 2

    peer_roe = peers.apply(lambda r: roe(r["net_income"], r["total_equity"]), axis=1).dropna()
    my_roe = roe(me["net_income"], me["total_equity"])
    peer_roe_med = float(peer_roe.median()) if len(peer_roe) else None
    quality_ok = my_roe is not None and peer_roe_med is not None and my_roe >= peer_roe_med
    cheap = gap >= CHEAP_GAP_THRESHOLD

    if cheap:
        label = "Potentially Undervalued" if quality_ok else "Value Trap Risk"
    else:
        label = "Priced for Quality" if quality_ok else "Overvalued Risk"

    return {"gap": float(gap), "gap_label": label, "peer_count": len(peers),
            "pe": float(me["pe_ttm"]), "pb": float(me["pb_mrq"]), "roe": my_roe,
            "peer_roe_median": peer_roe_med}
