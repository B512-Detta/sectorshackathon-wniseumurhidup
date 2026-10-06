import math
import os
import threading
import time
from datetime import date

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.narrator import narrate
from src.pipeline import build_watchlist, load_daily_cached

load_dotenv()

WATCHLIST_TTL = 3600
CHART_DAYS = 21

app = FastAPI(title="Anomali IDX API")
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,https://anomali-idx.vercel.app",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

_lock = threading.Lock()
_state: dict = {"result": None, "at": 0.0}
_narratives: dict[str, tuple[str, str]] = {}


def _clean(value):
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if math.isnan(value) or math.isinf(value) else float(value)
    if isinstance(value, date):
        return value.isoformat()
    if value is None or value is pd.NaT:
        return None
    return value


def _row_dict(row: pd.Series) -> dict:
    return {k: _clean(v) for k, v in row.to_dict().items()}


def _get_watchlist(force: bool = False) -> dict:
    with _lock:
        fresh = time.time() - _state["at"] < WATCHLIST_TTL
        if force or _state["result"] is None or not fresh:
            _state["result"] = build_watchlist()
            _state["at"] = time.time()
            _narratives.clear()
        return _state["result"]


@app.get("/api/watchlist")
def watchlist():
    result = _get_watchlist()
    frame: pd.DataFrame = result["rows"]
    return {
        "as_of": result["as_of"].isoformat() if result["as_of"] else None,
        "universe_size": result["universe_size"],
        "skipped": result["skipped"],
        "errors": result["errors"],
        "rows": [_row_dict(r) for _, r in frame.iterrows()],
    }


@app.post("/api/refresh")
def refresh(x_admin_token: str | None = Header(default=None)):
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Tidak diizinkan")
    _get_watchlist(force=True)
    return {"ok": True}


@app.get("/api/stocks/{ticker}")
def stock(ticker: str):
    frame: pd.DataFrame = _get_watchlist()["rows"]
    match = frame[frame["ticker"] == ticker]
    if match.empty:
        raise HTTPException(status_code=404, detail="Saham tidak ada di watchlist")
    row = match.iloc[0]

    if ticker not in _narratives:
        text, source = narrate(row, os.getenv("GEMINI_API_KEY"))
        _narratives[ticker] = (text, source)
    text, source = _narratives[ticker]

    daily = load_daily_cached(ticker).tail(CHART_DAYS)
    baseline = float(daily["volume"].iloc[:-1].median()) if len(daily) > 1 else None
    series = [{"date": d.isoformat(), "volume": _clean(v)}
              for d, v in zip(daily["date"], daily["volume"])]

    return {
        "row": _row_dict(row),
        "volume_series": series,
        "volume_baseline": baseline,
        "narrative": text,
        "narrative_source": source,
    }
