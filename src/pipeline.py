import json
import os
import sqlite3
import time
from datetime import date, datetime, timedelta
from typing import Callable

import pandas as pd

from src import scoring
from src.sectors_client import SectorsAPIError, SectorsClient

ROOT = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(ROOT, "data", "sectors.db")

UNIVERSE_SIZE = 50
DEEP_CANDIDATES = 15
DAILY_TTL = 12 * 3600
REPORT_TTL = 24 * 3600
HISTORY_DAYS = 45

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_prices (
    ticker TEXT PRIMARY KEY, raw_json TEXT, fetched_at INTEGER
);
CREATE TABLE IF NOT EXISTS quarterly_financials (
    ticker TEXT PRIMARY KEY, raw_json TEXT, fetched_at INTEGER
);
CREATE TABLE IF NOT EXISTS company_reports (
    ticker TEXT PRIMARY KEY, raw_json TEXT, fetched_at INTEGER
);
CREATE TABLE IF NOT EXISTS subsectors (
    sub_sector TEXT PRIMARY KEY, raw_json TEXT, fetched_at INTEGER
);
CREATE TABLE IF NOT EXISTS companies_by_subsector (
    sub_sector TEXT PRIMARY KEY, raw_json TEXT, fetched_at INTEGER
);
"""


def connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def _cached(conn, table: str, key: str, ttl: int, fetch: Callable):
    row = conn.execute(f"SELECT raw_json, fetched_at FROM {table} WHERE ticker = ?", (key,)).fetchone()
    if row and time.time() - row[1] < ttl:
        return json.loads(row[0])
    data = fetch()
    conn.execute(
        f"INSERT OR REPLACE INTO {table} (ticker, raw_json, fetched_at) VALUES (?, ?, ?)",
        (key, json.dumps(data), int(time.time())),
    )
    conn.commit()
    return data


def load_directory(conn) -> tuple[dict, dict]:
    """Map ticker -> subsector and ticker -> company name, from the cached subsector scan."""
    subsector_of, name_of = {}, {}
    rows = conn.execute(
        "SELECT sub_sector, raw_json FROM companies_by_subsector WHERE sub_sector != '__all__'"
    ).fetchall()
    for sub, raw in rows:
        for item in (json.loads(raw) or {}).get("results", []):
            subsector_of[item["symbol"]] = sub
            name_of[item["symbol"]] = item.get("company_name", item["symbol"])
    return subsector_of, name_of


def fetch_universe(client: SectorsClient) -> list[str]:
    data = client.most_traded(n_stock=UNIVERSE_SIZE)
    seen = []
    for day in sorted(data.keys(), reverse=True):
        for item in data[day]:
            if item["symbol"] not in seen:
                seen.append(item["symbol"])
    return seen[:UNIVERSE_SIZE]


def _daily_frame(raw: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(raw)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df.sort_values("date").reset_index(drop=True)


def build_watchlist(client: SectorsClient | None = None, progress: Callable[[str], None] = lambda _: None) -> dict:
    client = client or SectorsClient()
    conn = connect()
    subsector_of, name_of = load_directory(conn)
    start = (date.today() - timedelta(days=HISTORY_DAYS)).isoformat()

    universe = fetch_universe(client)
    errors = []
    skipped = []

    liquid = {}
    for i, ticker in enumerate(universe, 1):
        progress(f"Harga harian {i}/{len(universe)}: {ticker}")
        try:
            raw = _cached(conn, "daily_prices", ticker, DAILY_TTL,
                          lambda t=ticker: client.daily_price(t, start=start))
        except SectorsAPIError as e:
            errors.append(f"{ticker}: {e.status_code}")
            continue
        df = _daily_frame(raw)
        if scoring.looks_like_corporate_action(df):
            skipped.append(ticker)
        elif scoring.is_liquid(df):
            liquid[ticker] = df

    rows = []
    for ticker, df in liquid.items():
        v = scoring.volume_anomaly(df)
        rows.append({"ticker": ticker, "name": name_of.get(ticker, ticker),
                     "subsector": subsector_of.get(ticker, "-"),
                     "close": float(df["close"].iloc[-1]), **v})

    if not rows:
        return {"as_of": None, "rows": pd.DataFrame(), "errors": errors, "skipped": skipped,
                "universe_size": len(universe)}

    frame = pd.DataFrame(rows)
    frame["divergence_pct"] = None
    for sub, group in frame.groupby("subsector"):
        for idx, row in group.iterrows():
            peers = group.drop(idx)["ret_1d"].tolist()
            frame.at[idx, "divergence_pct"] = scoring.divergence_pct(row["ret_1d"], peers)
    frame["composite"] = [
        scoring.anomaly_composite(z, d) for z, d in zip(frame["volume_z"], frame["divergence_pct"])
    ]
    frame = frame.sort_values("composite", ascending=False).reset_index(drop=True)

    frame["explained"] = "Belum dicek"
    frame["gap"] = None
    frame["gap_label"] = "Belum dicek"
    frame["pe"] = None
    frame["pb"] = None
    frame["roe"] = None
    frame["peer_roe_median"] = None
    frame["peer_count"] = 0

    for idx in frame.index[:DEEP_CANDIDATES]:
        ticker = frame.at[idx, "ticker"]
        progress(f"Laporan {ticker}")
        try:
            report = _cached(conn, "company_reports", ticker, REPORT_TTL,
                             lambda t=ticker: client.company_report(t))
            quarterly = _cached(conn, "quarterly_financials", ticker, REPORT_TTL,
                                lambda t=ticker: client.quarterly_financials(t))
        except SectorsAPIError as e:
            errors.append(f"{ticker}: {e.status_code}")
            continue

        quarter_dates = [datetime.strptime(q["date"], "%Y-%m-%d").date() for q in quarterly if q.get("date")]
        frame.at[idx, "explained"] = scoring.explained_tag(
            frame.at[idx, "date"], quarter_dates, frame.at[idx, "is_anomaly"])
        gap = scoring.valuation_gap(report, ticker)
        for key in ("gap", "gap_label", "pe", "pb", "roe", "peer_roe_median", "peer_count"):
            frame.at[idx, key] = gap[key]

    frame["_priority"] = (
        frame["is_anomaly"].astype(int) * 2 + (frame["explained"] == "Unexplained").astype(int)
    )
    frame = frame.sort_values(["_priority", "composite"], ascending=[False, False]).drop(columns="_priority")
    frame = frame.reset_index(drop=True)

    conn.close()
    return {
        "as_of": max(df["date"].max() for df in liquid.values()),
        "rows": frame,
        "errors": errors,
        "skipped": skipped,
        "universe_size": len(universe),
    }


def load_daily_cached(ticker: str) -> pd.DataFrame:
    conn = connect()
    row = conn.execute("SELECT raw_json FROM daily_prices WHERE ticker = ?", (ticker,)).fetchone()
    conn.close()
    return _daily_frame(json.loads(row[0])) if row else pd.DataFrame()
