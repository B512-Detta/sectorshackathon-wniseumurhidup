import os
import time
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.sectors.app/v2"


class SectorsAPIError(Exception):
    def __init__(self, status_code, message, url):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(f"[{status_code}] {message} ({url})")


class SectorsClient:
    def __init__(self, api_key=None, timeout=15):
        self.api_key = api_key or os.getenv("SECTORS_API_KEY")
        if not self.api_key:
            raise ValueError("SECTORS_API_KEY tidak ditemukan. Set di .env")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": self.api_key})

    def _get(self, path, params=None, retries=4):
        url = f"{BASE_URL}{path}"
        last_err = None
        for attempt in range(retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 429 and attempt < retries:
                    time.sleep(2 ** (attempt + 1))
                    continue
                if not resp.ok:
                    raise SectorsAPIError(resp.status_code, resp.text[:300], url)
                return resp.json()
            except requests.exceptions.RequestException as e:
                last_err = e
                if attempt < retries:
                    time.sleep(1)
                    continue
                raise
        if last_err:
            raise last_err

    def list_subsectors(self):
        return self._get("/subsectors/")

    def companies_by_subsector(self, sub_sector):
        return self._get("/companies/", params={"where": f"sub_sector = '{sub_sector}'"})
    
    def company_report(self, ticker, sections=None):
        params = {"sections": sections} if sections else None
        return self._get(f"/company/report/{ticker}/", params=params)

    def quarterly_financials(self, ticker):
        return self._get(f"/financials/quarterly/{ticker}/")

    def daily_price(self, ticker, start=None, end=None):
        params = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self._get(f"/daily/{ticker}/", params=params or None)

    def top_changes(self, classifications="top_gainers,top_losers", periods="7d", n_stock=5):
        return self._get("/companies/top-changes/", params={"classifications": classifications, "periods": periods, "n_stock": n_stock})

    def most_traded(self, n_stock=10):
        return self._get("/most-traded/", params={"n_stock": n_stock})
