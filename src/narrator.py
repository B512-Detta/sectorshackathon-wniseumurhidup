import os

import pandas as pd

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_TIMEOUT_MS = 8000

SYSTEM_PROMPT = """Kamu adalah narrator data, bukan analis yang membuat opini pasar.
ATURAN:
1. Hanya sebutkan angka yang diberikan (volume, deviasi, return, gap, ROE). Jangan menghitung angka baru.
2. DILARANG menyebut motif atau kausalitas yang tidak ada di data
   (contoh terlarang: "insider", "manipulasi", "bandar", "akan naik", "karena berita").
3. Kalau status "Unexplained", tulis bahwa itu perlu investigasi lanjutan, bukan kesimpulan.
4. Tutup dengan status Explained/Unexplained dan label valuasi bila tersedia.
5. Maksimal 3 kalimat, bahasa Indonesia santai tapi jelas."""


def _fmt(value, pattern, fallback="n/a"):
    if value is None or pd.isna(value):
        return fallback
    return pattern.format(value)


def _pe_text(pe) -> str:
    if pe is None or pd.isna(pe) or pe > 100:
        return "n/m (laba mendekati nol)"
    return f"{pe:.1f}x"


def template_narrative(row: pd.Series) -> str:
    parts = [
        f"Volume {row['ticker'].replace('.JK', '')} hari ini "
        f"{_fmt(row['volume_ratio'], '{:.1f}x')} median 20 hari "
        f"(modified z {_fmt(row['volume_z'], '{:.1f}')}), return harian "
        f"{_fmt(row['ret_1d'] * 100, '{:+.1f}%')}."
    ]
    if not pd.isna(row["divergence_pct"]) and row["divergence_pct"] is not None:
        parts.append(f"Selisih dengan median peer subsector: {row['divergence_pct']:+.1f} poin persen.")
    if row["gap_label"] not in ("Belum dicek", "Data peer tidak cukup"):
        parts.append(
            f"P/E {_pe_text(row['pe'])}, P/BV {_fmt(row['pb'], '{:.2f}x')}, "
            f"ROE {_fmt(row['roe'] * 100 if row['roe'] is not None else None, '{:.1f}%')} "
            f"dibanding median peer {_fmt(row['peer_roe_median'] * 100 if row['peer_roe_median'] is not None else None, '{:.1f}%')}. "
            f"Label: {row['gap_label']}."
        )
    if row["explained"] == "Unexplained":
        parts.append("Status Unexplained, jadi ini perlu investigasi lanjutan dan belum bisa disimpulkan.")
    elif row["explained"] == "Explained":
        parts.append("Status Explained: tanggal anomali berdekatan dengan tanggal laporan keuangan.")
    return " ".join(parts)


def gemini_narrative(row: pd.Series, api_key: str) -> str:
    from google import genai
    from google.genai import types

    facts = {k: (None if pd.isna(row[k]) else row[k]) if not isinstance(row[k], (str, bool)) else row[k]
             for k in ("ticker", "volume_ratio", "volume_z", "ret_1d", "divergence_pct",
                       "gap", "gap_label", "pe", "pb", "roe", "peer_roe_median", "explained")}
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS))
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"{SYSTEM_PROMPT}\n\nData:\n{facts}",
    )
    return response.text.strip()


def narrate(row: pd.Series, api_key: str | None = None) -> tuple[str, str]:
    if api_key:
        try:
            return gemini_narrative(row, api_key), "gemini"
        except Exception:
            pass
    return template_narrative(row), "template"
