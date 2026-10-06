import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sectors_client import SectorsClient

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sectors.db")


def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS subsectors (
            sub_sector TEXT PRIMARY KEY,
            raw_json TEXT,
            fetched_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS companies_by_subsector (
            sub_sector TEXT PRIMARY KEY,
            raw_json TEXT,
            fetched_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS company_reports (
            ticker TEXT PRIMARY KEY,
            raw_json TEXT,
            fetched_at INTEGER
        );
    """)
    conn.commit()


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    client = SectorsClient()

    print("Fetching subsector list...")
    subsectors_data = client.list_subsectors()
    conn.execute(
        "INSERT OR REPLACE INTO subsectors (sub_sector, raw_json, fetched_at) VALUES (?, ?, ?)",
        ("__all__", json.dumps(subsectors_data), int(time.time())),
    )
    conn.commit()

    sub_sector_names = []
    if isinstance(subsectors_data, list):
        for item in subsectors_data:
            if isinstance(item, str):
                sub_sector_names.append(item)
            elif isinstance(item, dict) and "subsector" in item:
                sub_sector_names.append(item["subsector"])
    print(f"Ditemukan {len(sub_sector_names)} subsector.")

    for sub in sub_sector_names:
        print(f"  Fetching companies in subsector: {sub}")
        try:
            data = client.companies_by_subsector(sub)
            conn.execute(
                "INSERT OR REPLACE INTO companies_by_subsector (sub_sector, raw_json, fetched_at) VALUES (?, ?, ?)",
                (sub, json.dumps(data), int(time.time())),
            )
            conn.commit()
            time.sleep(1.5)
        except Exception as e:
            print(f"    Gagal fetch {sub}: {e}")

    print(f"\nSelesai. Data tersimpan di {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    main()
