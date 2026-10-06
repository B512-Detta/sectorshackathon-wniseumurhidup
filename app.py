import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.narrator import narrate
from src.pipeline import build_watchlist, load_daily_cached

load_dotenv()

INK = "#1B2430"
INK_SOFT = "#4A5568"
PAPER = "#F7F6F2"
RAISED = "#FFFFFF"
LINE = "#DCD8CE"
TEAL = "#1F5C5C"
TEAL_SOFT = "#E4EEED"
AMBER = "#B5772E"
AMBER_SOFT = "#F3E7D6"
DANGER = "#8C3B3B"
DANGER_SOFT = "#F5E6E2"
GOOD = "#2E6B4F"
GOOD_SOFT = "#E4EEE7"

st.set_page_config(page_title="Anomali IDX + Valuation Gap", page_icon=None, layout="wide")

st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {INK}; }}
  .stApp {{ background: {PAPER}; }}
  .block-container {{ padding-top: 2.5rem; max-width: 1100px; }}
  h1, h2, h3 {{ font-family: 'Fraunces', serif !important; font-weight: 600 !important; color: {INK}; letter-spacing: -0.01em; }}
  .kicker {{ font-size: 13px; color: {TEAL}; font-weight: 600; margin-bottom: 6px; }}
  .meta {{ color: {INK_SOFT}; font-size: 14px; margin-top: 6px; }}
  .meta b {{ color: {INK}; }}
  .mono {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; }}
  .pill {{ display: inline-block; font-size: 12px; font-weight: 600; padding: 2px 10px; border-radius: 20px; margin-right: 6px; }}
  .pill.unexp {{ background: {AMBER_SOFT}; color: {AMBER}; }}
  .pill.exp {{ background: {TEAL_SOFT}; color: {TEAL}; }}
  .pill.good {{ background: {GOOD_SOFT}; color: {GOOD}; }}
  .pill.bad {{ background: {DANGER_SOFT}; color: {DANGER}; }}
  .pill.neutral {{ background: {RAISED}; color: {INK_SOFT}; border: 1px solid {LINE}; }}
  .narr {{ background: {RAISED}; border: 1px solid {LINE}; border-left: 3px solid {TEAL}; border-radius: 4px; padding: 14px 16px; font-size: 15px; line-height: 1.6; }}
  .narr .src {{ font-size: 12px; color: {INK_SOFT}; margin-top: 8px; }}
  .stat {{ border-top: 1px solid {LINE}; padding-top: 8px; }}
  .stat .k {{ font-size: 12px; color: {INK_SOFT}; }}
  .stat .v {{ font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 500; }}
  .disclaimer {{ font-size: 13px; color: {INK_SOFT}; border-top: 1px solid {LINE}; margin-top: 40px; padding-top: 14px; }}
  div[data-testid="stDataFrame"] {{ background: {RAISED}; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def load_watchlist():
    return build_watchlist()


@st.cache_data(ttl=86400, show_spinner=False)
def narrative_for(ticker: str, row_dict: dict, api_key: str | None):
    return narrate(pd.Series(row_dict), api_key)


def pct(v, digits=1):
    return "n/a" if v is None or pd.isna(v) else f"{v * 100:+.{digits}f}%"


def num(v, pattern):
    return "n/a" if v is None or pd.isna(v) else pattern.format(v)


def status_pill(explained: str) -> str:
    cls = {"Unexplained": "unexp", "Explained": "exp"}.get(explained, "neutral")
    return f'<span class="pill {cls}">{explained}</span>'


def label_pill(label: str) -> str:
    cls = {
        "Potentially Undervalued": "good",
        "Value Trap Risk": "bad",
        "Overvalued Risk": "bad",
        "Priced for Quality": "neutral",
    }.get(label, "neutral")
    return f'<span class="pill {cls}">{label}</span>'


with st.sidebar:
    st.markdown("### Pengaturan")
    st.caption("Data disimpan di cache lokal. Tarik ulang hanya kalau perlu, karena pemanggilan API memakai kredit.")
    if st.button("Tarik ulang data dari API", width="stretch"):
        st.cache_data.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
    only_unexplained = st.checkbox("Cuma yang Unexplained", value=False)
    only_valued = st.checkbox("Cuma yang punya label valuasi", value=False)

with st.spinner("Lagi ngitung anomali dari cache..."):
    result = load_watchlist()

frame: pd.DataFrame = result["rows"]
as_of = result["as_of"]

st.markdown('<div class="kicker">Watchlist anomali harian IDX</div>', unsafe_allow_html=True)
st.title("Anomali IDX + Valuation Gap")
st.markdown(
    f'<div class="meta">Data per <b>{as_of or "belum ada"}</b> · '
    f'universe <b>{result["universe_size"]}</b> saham · '
    f'lolos likuiditas <b>{len(frame)}</b> · '
    f'dilewati karena corporate action <b>{len(result["skipped"])}</b></div>',
    unsafe_allow_html=True,
)

if result["errors"]:
    st.caption(f"Sebagian saham gagal diambil ({len(result['errors'])}): {', '.join(e.split(':')[0] for e in result['errors'][:8])}. Coba tarik ulang beberapa saat lagi.")

if frame.empty:
    st.info("Belum ada saham yang lolos filter. Cek kunci API di .env atau tarik ulang data.")
    st.stop()

view = frame.copy()
if only_unexplained:
    view = view[view["explained"] == "Unexplained"]
if only_valued:
    view = view[~view["gap_label"].isin(["Belum dicek", "Data peer tidak cukup"])]

st.subheader("Watchlist")
st.caption("Anomali tanpa penjelasan ada di paling atas. Skor gabungan 0–100 dari lonjakan volume dan selisih return dengan peer.")

table = view[["ticker", "name", "volume_ratio", "ret_1d", "divergence_pct", "composite", "explained", "gap_label"]].rename(columns={
    "ticker": "Ticker", "name": "Nama", "volume_ratio": "Volume vs median 20h", "ret_1d": "Return 1 hari",
    "divergence_pct": "Selisih peer (pp)", "composite": "Skor", "explained": "Status", "gap_label": "Label valuasi",
})
st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    column_config={
        "Ticker": st.column_config.TextColumn(width="small"),
        "Volume vs median 20h": st.column_config.NumberColumn(format="%.1fx"),
        "Return 1 hari": st.column_config.NumberColumn(format="%+.1f%%"),
        "Selisih peer (pp)": st.column_config.NumberColumn(format="%+.1f"),
        "Skor": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
    },
)

if view.empty:
    st.info("Tidak ada saham yang cocok dengan filter.")
    st.stop()

st.subheader("Detail saham")
ticker = st.selectbox("Pilih saham", view["ticker"].tolist(), format_func=lambda t: f"{t}  {view.set_index('ticker').at[t, 'name']}")
row = view[view["ticker"] == ticker].iloc[0]

st.markdown(
    f"<div>{status_pill(row['explained'])}{label_pill(row['gap_label'])}</div>",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="stat"><div class="k">Volume vs median 20h</div><div class="v">{num(row["volume_ratio"], "{:.1f}x")}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="stat"><div class="k">Modified z</div><div class="v">{num(row["volume_z"], "{:.1f}")}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="stat"><div class="k">Return 1 hari</div><div class="v">{pct(row["ret_1d"])}</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="stat"><div class="k">Skor gabungan</div><div class="v">{num(row["composite"], "{:.0f}")}</div></div>', unsafe_allow_html=True)

st.write("")
daily = load_daily_cached(ticker)
if not daily.empty:
    tail = daily.tail(21).copy()
    baseline_med = tail["volume"].iloc[:-1].median()
    colors = [AMBER if i == len(tail) - 1 and row["is_anomaly"] else TEAL for i in range(len(tail))]
    fig = go.Figure()
    fig.add_bar(x=tail["date"].astype(str), y=tail["volume"], marker_color=colors, name="Volume")
    fig.add_hline(y=baseline_med, line_dash="dot", line_color=INK_SOFT, annotation_text="median 20h", annotation_position="top left")
    fig.update_layout(
        height=260, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor=PAPER, plot_bgcolor=PAPER,
        font=dict(family="Inter", color=INK), yaxis=dict(gridcolor=LINE, title=None, tickformat="~s"),
        xaxis=dict(title=None), showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

st.markdown("#### Valuasi vs peer")
v1, v2, v3, v4 = st.columns(4)
v1.markdown(f'<div class="stat"><div class="k">P/E (TTM)</div><div class="v">{"n/m" if row["pe"] is None or pd.isna(row["pe"]) or row["pe"] > 100 else num(row["pe"], "{:.1f}x")}</div></div>', unsafe_allow_html=True)
v2.markdown(f'<div class="stat"><div class="k">P/BV</div><div class="v">{num(row["pb"], "{:.2f}x")}</div></div>', unsafe_allow_html=True)
v3.markdown(f'<div class="stat"><div class="k">ROE vs median peer</div><div class="v">{num(row["roe"] * 100 if row["roe"] is not None else None, "{:.1f}%")} / {num(row["peer_roe_median"] * 100 if row["peer_roe_median"] is not None else None, "{:.1f}%")}</div></div>', unsafe_allow_html=True)
v4.markdown(f'<div class="stat"><div class="k">Gap score · peer</div><div class="v">{num(row["gap"], "{:.0f}")} · {int(row["peer_count"])}</div></div>', unsafe_allow_html=True)
if row["gap_label"] == "Data peer tidak cukup":
    st.caption("Peer dalam rentang market cap 5x kurang dari 3, jadi perbandingan valuasi tidak ditampilkan.")

st.markdown("#### Narasi")
api_key = os.getenv("GEMINI_API_KEY")
text, source = narrative_for(ticker, row.to_dict(), api_key)
source_label = "Gemini" if source == "gemini" else "Template (angka saja)"
st.markdown(f'<div class="narr">{text}<div class="src">Sumber narasi: {source_label}</div></div>', unsafe_allow_html=True)

st.markdown(
    '<div class="disclaimer"><b>Disclaimer:</b> Tool ini adalah alat analisis dan informasi, bukan rekomendasi investasi. '
    "Keputusan investasi sepenuhnya tanggung jawab pengguna.</div>",
    unsafe_allow_html=True,
)
