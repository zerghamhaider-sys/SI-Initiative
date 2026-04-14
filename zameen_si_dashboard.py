"""
Zameen.com — Unified Classifieds Strategic Intelligence Dashboard
Merges: FC vs Actual Revenue Intelligence + ZSM-level SI Performance
Live data from two Google Sheets. Premium dark/light theme. Badge labels throughout.
"""

import streamlit as st
import math
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io
import requests

# ─────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Zameen.com | Strategic Intelligence",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True
DM = st.session_state.dark_mode

D = dict(
    bg="#080C14", surface="#0D1525", surface2="#111D30", surface3="#172033",
    border="#1E2D47", border2="#243452",
    text="#F0F4FF", subtext="#5E7499", subtext2="#8BA3C7",
    green="#10D97A", green2="#0BAF62", gold="#F0B429", gold2="#C4901A",
    red="#F04060", blue="#4D9FFF", purple="#9B7FFF",
    grid="#0F1A2C", tag_bg="#0D2238", tag_border="#10D97A", tag_text="#10D97A",
)
L = dict(
    bg="#F5F7FC", surface="#FFFFFF", surface2="#EDF1FA", surface3="#E3E9F5",
    border="#D0DAF0", border2="#BFC9E8",
    text="#0A1628", subtext="#4E6080", subtext2="#6B7FA0",
    green="#008A48", green2="#006A36", gold="#C47B00", gold2="#9A5F00",
    red="#D42050", blue="#2563EB", purple="#7C3AED",
    grid="#E8EEF8", tag_bg="#E0F5EC", tag_border="#008A48", tag_text="#006A36",
)
T = D if DM else L
GREEN  = T["green"];  GOLD = T["gold"];  RED  = T["red"]
BLUE   = T["blue"];   PURPLE = T["purple"]

PAL = [GREEN, GOLD, BLUE, PURPLE, RED, "#20C4D8", "#FF8C42", "#E040FB", "#00BFA5", "#FFB300"]

def rgba(h, a=0.15):
    h = h.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{a})"

# Semantic colour aliases (match old dashboard)
G_DIM  = rgba(GREEN, 0.10); G_MED = rgba(GREEN, 0.35); G_LINE = rgba(GREEN, 0.70)
G_FILL = rgba(GREEN, 0.12); AU_DIM = rgba(GOLD, 0.10);  AU_MED = rgba(GOLD, 0.40)
AU_LINE = rgba(GOLD, 0.80); R_DIM = rgba(RED, 0.10);   B_DIM  = rgba(T["border"], 0.5)

# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────
def fmt_pkr(n, short=False, signed=False):
    if n == 0: return "—"
    neg = n < 0; a = abs(n)
    sign = ("−" if neg else ("+" if signed else ""))
    if short:
        if a >= 1e9: return f"{sign}₨{a/1e9:.1f}B"
        if a >= 1e6: return f"{sign}₨{a/1e6:.1f}M"
        if a >= 1e3: return f"{sign}₨{a/1e3:.0f}K"
        return f"{sign}₨{a:.0f}"
    else:
        if a >= 1e9: return f"{sign}₨ {a/1e9:.2f}B"
        if a >= 1e6: return f"{sign}₨ {a/1e6:.2f}M"
        if a >= 1e3: return f"{sign}₨ {a/1e3:.1f}K"
        return f"{sign}₨ {a:,.0f}"

def fmt(n):
    try:
        n = float(n)
        if n >= 1_000_000: return f"{n/1_000_000:.2f}M"
        if n >= 1_000:     return f"{n/1_000:.1f}K"
        return f"{n:,.0f}"
    except: return "0"

def pct_bar_html(pct, color):
    w = min(max(float(pct), 0), 100)
    return (f'<div style="background:{T["surface3"]};border-radius:3px;height:4px;'
            f'width:100%;overflow:hidden;margin-top:6px;">'
            f'<div style="background:{color};height:100%;width:{w}%;border-radius:3px;"></div></div>')

def section_hdr(icon, title, sub=""):
    s = f' <span style="color:{T["subtext"]};font-size:0.68rem;font-weight:400;">{sub}</span>' if sub else ""
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin:1.6rem 0 0.85rem;">
      <div style="width:26px;height:26px;background:{G_DIM};border-radius:7px;
           border:1px solid {rgba(GREEN,0.3)};display:flex;align-items:center;
           justify-content:center;font-size:0.78rem;">{icon}</div>
      <span style="font-weight:700;font-size:0.9rem;color:{T['text']};">{title}</span>{s}
    </div>""", unsafe_allow_html=True)

def pill_stat(label, val, color):
    return (f'<div><div style="font-size:0.55rem;text-transform:uppercase;letter-spacing:0.12em;'
            f'color:{T["subtext"]};font-weight:700;margin-bottom:3px;">{label}</div>'
            f'<div style="font-family:DM Mono,monospace;font-size:1rem;font-weight:600;'
            f'color:{color};">{val}</div></div>')

# ─────────────────────────────────────────────────────────────────────
# CHART HELPERS — no shared dicts, no key conflicts
# ─────────────────────────────────────────────────────────────────────
def base(h=380, l=8, r=80, t=16, b=8):
    return dict(
        paper_bgcolor=T["surface"], plot_bgcolor=T["surface"],
        font=dict(family="DM Sans, sans-serif", color=T["subtext2"], size=11),
        margin=dict(l=l, r=r, t=t, b=b), height=h,
    )

def ax(fig, angle=0, show_x_grid=False):
    fig.update_xaxes(gridcolor=T["grid"] if show_x_grid else "rgba(0,0,0,0)",
                     tickcolor="rgba(0,0,0,0)", linecolor=T["border"],
                     tickfont=dict(color=T["subtext2"], size=10),
                     zeroline=False, tickangle=angle, showgrid=show_x_grid)
    fig.update_yaxes(gridcolor=T["grid"], tickcolor="rgba(0,0,0,0)",
                     linecolor="rgba(0,0,0,0)",
                     tickfont=dict(color=T["subtext2"], size=10),
                     zeroline=False, showgrid=True)
    return fig

def leg(fig, ori="v", y=0.5, x=1.02):
    fig.update_layout(legend=dict(
        bgcolor=T["surface2"], bordercolor=T["border"], borderwidth=1,
        font=dict(size=10, color=T["text"]), orientation=ori, y=y, x=x, itemsizing="constant",
    ))
    return fig

# Badge annotation helpers
def badge_hbar(fig, values, labels):
    for val, lbl in zip(values, labels):
        fig.add_annotation(x=val, y=lbl, text=f"<b>{fmt(val)}</b>",
            showarrow=False, xanchor="left", xshift=8,
            font=dict(size=12, color=T["text"], family="DM Mono"),
            bgcolor=T["surface2"], bordercolor=T["border"], borderwidth=1, borderpad=5)
    return fig

def badge_hbar_pkr(fig, values, labels):
    for val, lbl in zip(values, labels):
        fig.add_annotation(x=val, y=lbl, text=f"<b>{fmt_pkr(val,short=True)}</b>",
            showarrow=False, xanchor="left", xshift=8,
            font=dict(size=12, color=T["text"], family="DM Mono"),
            bgcolor=T["surface2"], bordercolor=T["border"], borderwidth=1, borderpad=5)
    return fig

def badge_vbar(fig, x_vals, y_vals, shift=10, pkr=False):
    for x, y in zip(x_vals, y_vals):
        if float(y) <= 0: continue
        txt = f"<b>{fmt_pkr(y, short=True)}</b>" if pkr else f"<b>{fmt(y)}</b>"
        fig.add_annotation(x=x, y=y, text=txt,
            showarrow=False, yanchor="bottom", yshift=shift,
            font=dict(size=11, color=T["text"], family="DM Mono"),
            bgcolor=T["surface2"], bordercolor=T["border"], borderwidth=1, borderpad=4)
    return fig

def badge_scatter(fig, x_vals, y_vals, pkr=False):
    for x, y in zip(x_vals, y_vals):
        txt = f"<b>{fmt_pkr(y, short=True)}</b>" if pkr else f"<b>{fmt(y)}</b>"
        fig.add_annotation(x=x, y=y, text=txt,
            showarrow=False, yanchor="bottom", yshift=14,
            font=dict(size=12, color=T["text"], family="DM Mono"),
            bgcolor=T["surface2"], bordercolor=GREEN, borderwidth=1, borderpad=5)
    return fig

# ─────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────
_b = T["border"]; _bg = T["bg"]; _sf = T["surface"]; _s2 = T["surface2"]
_tx = T["text"];  _st = T["subtext"]; _s2t = T["subtext2"]; _b2 = T["border2"]

st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

st.markdown(f"""
<style>
*, *::before, *::after {{ box-sizing: border-box; }}
html, body, [class*="css"], .stApp,
[data-testid="stApp"], [data-testid="stAppViewContainer"],
[data-testid="stMain"], .main {{
  font-family: 'DM Sans', sans-serif !important;
  background: {_bg} !important;
  color: {_tx} !important;
}}
.block-container {{ padding: 0 2.2rem 3rem !important; max-width: 100% !important; }}
[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], #MainMenu, footer {{ display: none !important; }}

/* ── KPI METRIC CARDS ── */
[data-testid="metric-container"] {{
  background: {_sf} !important; border: 1px solid {_b} !important;
  border-radius: 12px !important; padding: 1.1rem 1.3rem !important;
  position: relative !important; overflow: hidden !important;
}}
[data-testid="metric-container"]::before {{
  content:''; position:absolute; top:0; left:0; right:0; height:3px;
  background: linear-gradient(90deg, {GREEN}, transparent); z-index:1;
}}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{
  color: {_st} !important; font-size: 0.62rem !important;
  letter-spacing: 0.12em !important; text-transform: uppercase !important;
  font-weight: 700 !important;
}}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {{
  color: {_tx} !important; font-size: 1.35rem !important;
  font-weight: 700 !important; font-family: 'DM Mono', monospace !important;
}}
[data-testid="stMetricDelta"] {{ font-size: 0.72rem !important; }}

/* ── TABS ── */
[data-testid="stTabs"] [role="tablist"] {{
  background: {_sf} !important; border-radius: 10px !important;
  border: 1px solid {_b} !important; padding: 4px !important; gap: 3px !important;
}}
[data-testid="stTabs"] [role="tab"] {{
  color: {_st} !important; background: transparent !important;
  border-radius: 7px !important; font-size: 0.78rem !important;
  font-weight: 600 !important; padding: 0.4rem 1.1rem !important;
  border: none !important; transition: all 0.18s !important;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
  background: {GREEN} !important; color: #fff !important;
}}
[data-testid="stTabs"] [role="tab"]:hover {{ color: {_tx} !important; }}

/* ── MULTISELECT / DROPDOWNS ── */
div[data-baseweb="select"] > div {{
  background: {_s2} !important; border: 1px solid {_b} !important;
  border-radius: 8px !important; min-height: 38px !important;
}}
div[data-baseweb="select"] > div:focus-within {{
  border-color: {GREEN} !important; box-shadow: 0 0 0 2px {rgba(GREEN,0.15)} !important;
}}
div[data-baseweb="select"] input {{
  color: {_tx} !important; font-size: 0.82rem !important;
  font-family: 'DM Sans', sans-serif !important;
}}
/* Tags — compact, themed */
div[data-testid="stMultiSelect"] [data-baseweb="tag"] {{
  background: {T["tag_bg"]} !important;
  border: 1px solid {T["tag_border"]} !important;
  color: {T["tag_text"]} !important;
  border-radius: 5px !important;
  font-size: 0.68rem !important; font-weight: 600 !important;
  padding: 1px 6px !important; margin: 1px !important;
  max-width: 120px !important;
}}
div[data-testid="stMultiSelect"] [data-baseweb="tag"] span {{
  overflow: hidden !important; text-overflow: ellipsis !important;
  white-space: nowrap !important; max-width: 90px !important;
}}
/* Popover */
div[data-baseweb="popover"] {{
  background: {_sf} !important;
}}
div[data-baseweb="popover"] ul {{
  background: {_sf} !important; border: 1px solid {_b2} !important;
  border-radius: 10px !important; padding: 4px !important;
  box-shadow: 0 16px 40px rgba(0,0,0,0.5) !important;
}}
div[data-baseweb="popover"] li {{
  color: {_tx} !important; font-size: 0.82rem !important;
  background: {_sf} !important; border-radius: 6px !important;
  margin: 2px 0 !important; padding: 7px 12px !important;
  font-family: 'DM Sans', sans-serif !important;
}}
div[data-baseweb="popover"] li:hover {{
  background: {_s2} !important; color: {GREEN} !important;
}}
div[data-baseweb="popover"] [aria-selected="true"] {{
  background: {rgba(GREEN, 0.1)} !important; color: {GREEN} !important;
}}
div[data-testid="stMultiSelect"] label,
div[data-testid="stSelectbox"] label {{
  font-size: 0.6rem !important; font-weight: 700 !important;
  letter-spacing: 1.4px !important; text-transform: uppercase !important;
  color: {_st} !important; margin-bottom: 3px !important;
}}

/* ── BUTTONS ── */
.stButton > button {{
  font-family: 'DM Sans', sans-serif !important; font-size: 0.76rem !important;
  font-weight: 600 !important; border-radius: 8px !important;
  background: {_s2} !important; color: {_tx} !important;
  border: 1px solid {_b} !important; transition: all 0.15s !important;
}}
.stButton > button:hover {{ border-color: {GREEN} !important; color: {GREEN} !important; }}
.btn-primary > button {{
  background: linear-gradient(135deg, {GREEN} 0%, {T["green2"]} 100%) !important;
  color: #fff !important; border: none !important; font-weight: 700 !important;
  padding: 12px 14px !important; border-radius: 10px !important;
  box-shadow: 0 6px 20px {rgba(GREEN,0.35)} !important;
}}

/* ── TEXT INPUT ── */
div[data-testid="stTextInput"] > div > div > input {{
  background: {_s2} !important; border: 1px solid {_b} !important;
  border-radius: 10px !important; color: {_tx} !important;
  font-family: 'DM Sans', sans-serif !important; font-size: 0.92rem !important;
  padding: 12px 16px !important;
}}
div[data-testid="stTextInput"] > div > div > input:focus {{
  border-color: {GREEN} !important; box-shadow: 0 0 0 3px {rgba(GREEN,0.14)} !important;
}}
div[data-testid="stTextInput"] label {{ display: none !important; }}

/* ── SECTION LABEL ── */
.slbl {{
  font-size: 0.65rem; font-weight: 600; letter-spacing: 1.8px;
  text-transform: uppercase; color: {_s2t}; margin-bottom: 0.75rem;
  display: flex; align-items: center; gap: 8px;
}}
.slbl::before {{
  content: ''; display: block; width: 3px; height: 12px;
  background: linear-gradient(180deg, {GREEN}, {T["green2"]}); border-radius: 2px;
}}

/* ── LIVE BADGE ── */
.live-pill {{
  display: inline-flex; align-items: center; gap: 5px;
  background: {rgba(GREEN,0.09)}; border: 1px solid {rgba(GREEN,0.22)};
  color: {GREEN}; font-size: 0.63rem; font-weight: 600;
  letter-spacing: 1.2px; padding: 4px 12px; border-radius: 20px; text-transform: uppercase;
}}
.live-dot {{
  width: 6px; height: 6px; background: {GREEN}; border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}}
@keyframes pulse {{ 0%,100% {{ opacity:1; transform:scale(1); }} 50% {{ opacity:0.3; transform:scale(0.8); }} }}

/* ── DATAFRAME ── */
div[data-testid="stDataFrame"] {{ border-radius: 10px; overflow: hidden; }}

/* ── SCROLLBAR ── */
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: {_bg}; }}
::-webkit-scrollbar-thumb {{ background: {_b2}; border-radius: 10px; }}
</style>
""", unsafe_allow_html=True)

# JS removed — using native Streamlit multiselect without tag hiding

# ─────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────
if "auth" not in st.session_state:  st.session_state.auth = False
if "err"  not in st.session_state:  st.session_state.err  = False

if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.05, 1])
    with col:
        st.markdown("<div style='height:12vh'></div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:{_sf};border:1px solid {_b2};border-radius:20px;
             padding:3rem 2.6rem 2.2rem;box-shadow:0 32px 80px rgba(0,0,0,0.6);text-align:center;">
          <div style="width:60px;height:60px;background:linear-gradient(135deg,{GREEN},{T['green2']});
               border-radius:16px;margin:0 auto 1.4rem;display:flex;align-items:center;
               justify-content:center;font-size:1.5rem;font-weight:900;color:#fff;
               box-shadow:0 8px 24px {rgba(GREEN,0.35)};">Z</div>
          <div style="font-family:'DM Sans',sans-serif;font-size:1.6rem;font-weight:800;
               color:{_tx};letter-spacing:-0.5px;margin-bottom:4px;">
               zameen<span style="color:{GREEN};">.com</span></div>
          <div style="font-size:0.62rem;font-weight:600;letter-spacing:2px;text-transform:uppercase;
               color:{GREEN};margin-bottom:8px;">Restricted Access</div>
          <div style="font-size:0.8rem;color:{_st};line-height:1.65;margin-bottom:1.8rem;">
               Enter your access password to view<br>the Strategic Intelligence Portal.</div>
        </div>""", unsafe_allow_html=True)
        pwd = st.text_input("pw", type="password", placeholder="Enter access password",
                            label_visibility="collapsed")
        st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
        if st.button("Sign In →", use_container_width=True):
            if pwd == "7862":
                st.session_state.auth = True
                st.session_state.err  = False
                st.rerun()
            else:
                st.session_state.err = True
        st.markdown('</div>', unsafe_allow_html=True)
        if st.session_state.err:
            st.markdown(f'<p style="color:{RED};font-size:0.8rem;text-align:center;'
                        f'margin-top:10px;font-weight:500;">⚠ Incorrect password</p>',
                        unsafe_allow_html=True)
        st.markdown(f'<p style="text-align:center;font-size:0.65rem;color:{_st};'
                    f'margin-top:1.2rem;">Zameen.com · Strategic Intelligence · Confidential</p>',
                    unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────────────
# DATA SOURCE 1 — FC vs Actual (original dashboard sheet)
# ─────────────────────────────────────────────────────────────────────
FC_SHEET = ("https://docs.google.com/spreadsheets/d/"
            "1gegnSeFaH84_pwSrGMc3EADTnK-SNPwpv4ymMeO9wJY/export?format=csv&gid=0")
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def to_num(v):
    if pd.isna(v): return 0.0
    s = str(v).strip().replace(",","").replace("₨","").replace("%","").strip()
    if s in ("-","","—","–"): return 0.0
    try: return float(s)
    except: return 0.0

@st.cache_data(ttl=300, show_spinner=False)
def load_fc():
    raw = pd.read_csv(FC_SHEET, header=None, dtype=str)
    COL_NAME=1; COL_FCREV=2; COL_MON=list(range(3,15)); COL_YTD=15

    def block(r0, r1):
        rows = []
        for i in range(r0, r1):
            if i >= len(raw): break
            r = raw.iloc[i]
            entry = {"Initiative": str(r.iloc[COL_NAME]).strip(),
                     "FC_Rev": to_num(r.iloc[COL_FCREV]),
                     "YTD": to_num(r.iloc[COL_YTD]) if COL_YTD < len(r) else 0.0}
            for j, m in enumerate(MONTHS):
                c = COL_MON[j]
                entry[m] = to_num(r.iloc[c]) if c < len(r) else 0.0
            rows.append(entry)
        return pd.DataFrame(rows)

    def totrow(idx):
        if idx >= len(raw): return {}
        r = raw.iloc[idx]
        out = {"FC_Rev": to_num(r.iloc[COL_FCREV]),
               "YTD": to_num(r.iloc[COL_YTD]) if COL_YTD < len(r) else 0.0}
        for j, m in enumerate(MONTHS):
            c = COL_MON[j]; out[m] = to_num(r.iloc[c]) if c < len(r) else 0.0
        return out

    df_fc  = block(2,  8)
    df_act = block(12, 18)
    fc_tot = totrow(8)
    ac_tot = totrow(18)
    return df_fc, df_act, fc_tot, ac_tot

# ─────────────────────────────────────────────────────────────────────
# DATA SOURCE 2 — ZSM SI Performance (ZSM sheet)
# ─────────────────────────────────────────────────────────────────────
ZSM_SHEET_ID = "14UEnSMs1GAuvUVxp7aq_q71YYc_d0VaEVrygarXzaxs"
ZSM_CSV = f"https://docs.google.com/spreadsheets/d/{ZSM_SHEET_ID}/export?format=csv&gid=0"

@st.cache_data(ttl=300, show_spinner=False)
def load_zsm():
    resp = requests.get(ZSM_CSV, timeout=15); resp.raise_for_status()
    raw = pd.read_csv(io.StringIO(resp.text), header=None, dtype=str).fillna('')
    hr = 0; best = -1
    for i in range(min(10, len(raw))):
        row = raw.iloc[i]; score = (row.str.strip()!='').sum()
        score += sum(k in ' '.join(row.str.lower())
                     for k in ['jan','feb','mar','regional','initiative','zsm','ytd'])*3
        if score > best: best = score; hr = i
    df = pd.read_csv(io.StringIO(resp.text), skiprows=hr, dtype=str).fillna('')
    df.columns = [str(c).strip() for c in df.columns]
    df = df[[c for c in df.columns if not c.lower().startswith('unnamed') and c.strip()!='']]
    df = df[df.apply(lambda r: r.str.strip().ne('').any(), axis=1)].reset_index(drop=True)
    tc_list, nc = [], []
    for col in df.columns:
        ne = df[col][df[col].str.strip()!='']
        if ne.empty: continue
        ratio = pd.to_numeric(ne.str.replace(',','',regex=False).str.strip(),
                              errors='coerce').notna().mean()
        (nc if ratio >= 0.5 else tc_list).append(col)
    if len(tc_list) < 2: tc_list = list(df.columns[:2]); nc = list(df.columns[2:])
    tc, sc = tc_list[0], tc_list[1]
    for col in nc:
        df[col] = pd.to_numeric(df[col].str.replace(',','',regex=False).str.strip(),
                                errors='coerce').fillna(0)
    df[tc] = df[tc].replace('', np.nan).ffill().fillna('')
    df = df[df[sc].str.strip()!=''].reset_index(drop=True)
    df = df[df[tc].str.strip()!=''].reset_index(drop=True)
    return df, tc, sc, nc

# ── Load both sources ─────────────────────────────────────────────────
fc_ok = zsm_ok = True
with st.spinner(""):
    try:
        df_fc, df_act, fc_tot, ac_tot = load_fc()
    except Exception as e:
        fc_ok = False; fc_err = str(e)

    try:
        df_zsm, team_col, si_col, num_cols = load_zsm()
    except Exception as e:
        zsm_ok = False; zsm_err = str(e)

if not fc_ok and not zsm_ok:
    st.error("Both data sources failed to load. Ensure Google Sheets are shared publicly.")
    if st.button("🔄 Retry"): st.cache_data.clear(); st.rerun()
    st.stop()

# ── FC derived metrics ────────────────────────────────────────────────
if fc_ok:
    fc_mon  = [float(df_fc[m].sum())  for m in MONTHS]
    act_mon = [float(df_act[m].sum()) for m in MONTHS]
    rep     = [m for m in MONTHS if act_mon[MONTHS.index(m)] > 0]
    n_rep   = len(rep)
    TOTAL_FC  = fc_tot.get("FC_Rev", df_fc["FC_Rev"].sum())
    TOTAL_ACT = ac_tot.get("YTD", sum(act_mon))
    rep_temp  = [m for m in MONTHS if act_mon[MONTHS.index(m)] > 0]
    FC_YTD_COMP = sum(fc_mon[MONTHS.index(m)] for m in rep_temp)
    TOTAL_VAR = TOTAL_ACT - FC_YTD_COMP
    YTD_PCT   = (TOTAL_ACT / FC_YTD_COMP * 100) if FC_YTD_COMP > 0 else 0.0
    run_rate  = (TOTAL_ACT / n_rep * 12) if n_rep > 0 else 0
else:
    rep = []; n_rep = 0

# ── ZSM derived ───────────────────────────────────────────────────────
if zsm_ok:
    ytd_cols   = [c for c in num_cols if 'ytd' in c.lower()]
    month_cols = [c for c in num_cols if 'ytd' not in c.lower()]
    all_vc     = month_cols
    teams = sorted(df_zsm[team_col].dropna().unique().tolist())
    sis   = sorted(df_zsm[si_col].dropna().unique().tolist())

# ─────────────────────────────────────────────────────────────────────
# UNIFIED HEADER — brand + filters + controls in ONE tight row
# ─────────────────────────────────────────────────────────────────────
rep_str = ", ".join(rep) if rep else "—"

# ── TOPBAR: brand left, action buttons right (in HTML — no Streamlit column gap)
_theme_lbl   = "☀ Light" if DM else "🌙 Dark"
_theme_key   = "btn_theme"
_refresh_key = "btn_refresh"
_logout_key  = "btn_logout"

# Render topbar as pure HTML — no columns, no gap
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
     padding:0.75rem 0 0.65rem;border-bottom:1px solid {_b};margin-bottom:0.8rem;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="width:34px;height:34px;background:linear-gradient(135deg,{GREEN},{T['green2']});
         border-radius:9px;display:flex;align-items:center;justify-content:center;
         font-size:0.95rem;font-weight:800;color:#fff;
         box-shadow:0 4px 12px {rgba(GREEN,0.3)};flex-shrink:0;">Z</div>
    <div>
      <div style="font-size:0.95rem;font-weight:700;color:{_tx};letter-spacing:-0.3px;">
           zameen<span style="color:{GREEN};">.com</span>
           <span style="color:{_st};font-weight:400;font-size:0.75rem;"> · Strategic Intelligence</span></div>
      <div style="font-size:0.63rem;color:{_st};margin-top:1px;">
           Classifieds · ZSM Revenue Intelligence · FY 2026
           &nbsp;·&nbsp;
           <span style="font-family:'DM Mono',monospace;">Reported: {rep_str}</span></div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <div class="live-pill"><div class="live-dot"></div>Live · 5 min</div>
  </div>
</div>""", unsafe_allow_html=True)

# Action buttons in a tight horizontal row — use st.columns with minimal ratio
_b1, _b2, _b3, _bpad = st.columns([1, 1, 1, 9])
with _b1:
    if st.button("☀" if DM else "🌙", use_container_width=True, key="btn_theme"):
        st.session_state.dark_mode = not DM; st.rerun()
with _b2:
    if st.button("🔄", use_container_width=True, key="btn_refresh"):
        st.cache_data.clear(); st.rerun()
with _b3:
    if st.button("⏻", use_container_width=True, key="btn_logout"):
        st.session_state.auth = False; st.rerun()

# Filters — full width, 3 equal columns, no extra column for buttons
if zsm_ok:
    _fc1, _fc2, _fc3 = st.columns([2, 2, 1], gap="small")
    with _fc1:
        sel_teams = st.multiselect(
            "ZSM / Region", options=teams, default=teams,
            placeholder="Select ZSMs…", key="ms_teams"
        )
    with _fc2:
        sel_si = st.multiselect(
            "Strategic Initiative", options=sis, default=sis,
            placeholder="Select initiatives…", key="ms_si"
        )
    with _fc3:
        sel_months = st.multiselect(
            "Month", options=month_cols, default=month_cols,
            placeholder="All months", key="ms_months"
        ) if month_cols else []

    sel_teams  = sel_teams  or teams
    sel_si     = sel_si     or sis
    sel_months = sel_months or month_cols
    dff    = df_zsm[df_zsm[team_col].isin(sel_teams) & df_zsm[si_col].isin(sel_si)].copy()
    use_mc = [m for m in sel_months if m in dff.columns]

st.markdown(f"<div style='height:1px;background:{_b};margin:0.2rem 0 0.8rem;'></div>",
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# EXECUTIVE KPI ROW — FC + ZSM combined
# ─────────────────────────────────────────────────────────────────────
if fc_ok and zsm_ok:
    zsm_ts  = dff.groupby(team_col)[use_mc].sum().sum(axis=1) if use_mc else pd.Series(dtype=float)
    si_ts   = dff.groupby(si_col)[use_mc].sum().sum(axis=1)   if use_mc else pd.Series(dtype=float)
    top_zsm = str(zsm_ts.idxmax()) if (not zsm_ts.empty and zsm_ts.sum()>0) else "N/A"
    top_ini = str(si_ts.idxmax())  if (not si_ts.empty  and si_ts.sum()>0)  else "N/A"

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    with k1: st.metric("Full-Year FC",    fmt_pkr(TOTAL_FC),  f"{len(df_fc)} initiatives")
    with k2: st.metric("YTD Actual",      fmt_pkr(TOTAL_ACT), f"{YTD_PCT:.0f}% of FC")
    with k3: st.metric("YTD Variance",    fmt_pkr(TOTAL_VAR, signed=True),
                        "▲ Ahead" if TOTAL_VAR >= 0 else "▼ Below")
    with k4: st.metric("Run Rate (Ann.)", fmt_pkr(run_rate),  f"vs FC {fmt_pkr(TOTAL_FC,short=True)}")
    with k5: st.metric("Top ZSM",         top_zsm[:18],       fmt(float(zsm_ts.max())) if not zsm_ts.empty else "—")
    with k6: st.metric("Top Initiative",  top_ini[:18],        fmt(float(si_ts.max()))  if not si_ts.empty  else "—")
elif fc_ok:
    k1,k2,k3,k4,k5 = st.columns(5)
    with k1: st.metric("Full-Year FC",    fmt_pkr(TOTAL_FC))
    with k2: st.metric("YTD Actual",      fmt_pkr(TOTAL_ACT), f"{YTD_PCT:.0f}% achieved")
    with k3: st.metric("YTD Variance",    fmt_pkr(TOTAL_VAR, signed=True))
    with k4: st.metric("Run Rate (Ann.)", fmt_pkr(run_rate))
    with k5: st.metric("FC Remaining",    fmt_pkr(TOTAL_FC - TOTAL_ACT))
elif zsm_ok:
    zsm_tot = float(dff[use_mc].sum().sum()) if use_mc else 0
    k1,k2,k3 = st.columns(3)
    with k1: st.metric("ZSM Total Revenue", fmt(zsm_tot))
    with k2: st.metric("Active ZSMs",       str(dff[team_col].nunique()))
    with k3: st.metric("Initiatives",       str(len(sel_si)))

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# MONTHLY PERFORMANCE CARDS (FC sheet)
# ─────────────────────────────────────────────────────────────────────
if fc_ok and rep:
    section_hdr("📅", "Monthly Performance", f"Reported: {' · '.join(rep)}")
    mcols = st.columns(n_rep)
    for col, m in zip(mcols, rep):
        mi    = MONTHS.index(m); act_v = act_mon[mi]; fc_v = fc_mon[mi]
        var_v = act_v - fc_v; pct_v = (act_v/fc_v*100) if fc_v > 0 else 0
        clr   = GREEN if pct_v >= 100 else (GOLD if pct_v >= 80 else RED)
        vc    = GREEN if var_v >= 0 else RED
        with col:
            st.markdown(f"""
            <div style="background:{_sf};border:1px solid {_b};border-radius:12px;
                 padding:1.1rem;position:relative;overflow:hidden;">
              <div style="position:absolute;top:0;left:0;right:0;height:3px;
                   background:linear-gradient(90deg,{clr},transparent);"></div>
              <div style="display:flex;justify-content:space-between;align-items:flex-start;
                   margin-bottom:0.6rem;">
                <div style="font-size:0.58rem;font-weight:800;letter-spacing:0.15em;
                     text-transform:uppercase;color:{_st};">{m} 2026</div>
                <div style="background:{clr}22;border:1px solid {clr}55;border-radius:6px;
                     padding:2px 8px;font-family:'DM Mono',monospace;
                     font-size:0.82rem;font-weight:700;color:{clr};">{pct_v:.0f}%</div>
              </div>
              <div style="font-family:'DM Mono',monospace;font-size:1.2rem;
                   font-weight:600;color:{_tx};margin-bottom:2px;">{fmt_pkr(act_v)}</div>
              <div style="font-size:0.64rem;color:{_st};margin-bottom:0.7rem;">
                   FC: <span style="color:{_tx};font-family:'DM Mono',monospace;">{fmt_pkr(fc_v)}</span></div>
              {pct_bar_html(pct_v, clr)}
              <div style="font-size:0.63rem;color:{vc};margin-top:0.55rem;
                   font-family:'DM Mono',monospace;">{fmt_pkr(var_v,signed=True)} vs plan</div>
            </div>""", unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# TABS — 7 total
# ─────────────────────────────────────────────────────────────────────
tab_labels = ["📊  FC Overview", "📈  Monthly Trends",
              "🏆  ZSM Performance", "🎯  Initiatives",
              "🔍  Initiative Drill-Down", "🔥  Trends & Heatmap", "🗃  Data"]
tabs = st.tabs(tab_labels)
tab_fc, tab_trend, tab_zsm, tab_init, tab_drill, tab_heat, tab_data = tabs

# ══════════════════════════════════════════════════════════════════════
# TAB 1 — FC OVERVIEW
# ══════════════════════════════════════════════════════════════════════
with tab_fc:
    if not fc_ok:
        st.warning(f"FC data unavailable: {fc_err}")
    else:
        r1a, r1b = st.columns([1.65, 1], gap="large")
        with r1a:
            section_hdr("📊", "Forecast vs Actual — Full Year")
            fig = go.Figure()
            # Forecast bars — all 12 months
            fig.add_trace(go.Bar(x=MONTHS, y=fc_mon, name="Forecast",
                marker=dict(color=AU_MED, line=dict(color=GOLD, width=1.2)),
                hovertemplate="<b>%{x}</b><br>FC: <b>₨%{y:,.0f}</b><extra></extra>"))
            if rep:
                av = [act_mon[MONTHS.index(m)] for m in rep]
                # Actual bars
                fig.add_trace(go.Bar(x=rep, y=av, name="Actual",
                    marker=dict(color=G_MED, line=dict(color=GREEN, width=1.2)),
                    hovertemplate="<b>%{x}</b><br>Actual: <b>₨%{y:,.0f}</b><extra></extra>"))
                # % Achievement line — markers only, no inline text (avoids overlap)
                pct_ach = [(a/f*100) if f>0 else 0
                           for a,f in zip(av,[fc_mon[MONTHS.index(m)] for m in rep])]
                fig.add_trace(go.Scatter(
                    x=rep, y=pct_ach,
                    name="% Achievement",
                    mode="lines+markers",
                    yaxis="y2",
                    line=dict(color=RED, width=3),
                    marker=dict(size=13, color=RED, symbol="diamond",
                                line=dict(color="white", width=2)),
                    hovertemplate="<b>%{x}</b><br>Achievement: <b>%{y:.1f}%</b><extra></extra>",
                ))
                # Badge annotations for % achievement — staggered to avoid overlap
                for mi, (m, pct_v) in enumerate(zip(rep, pct_ach)):
                    yshift_v = 28 if mi % 2 == 0 else 48  # alternate heights
                    fig.add_annotation(
                        x=m, y=pct_v, yref="y2",
                        text=f"<b>{pct_v:.0f}%</b>",
                        showarrow=True, arrowhead=0, arrowwidth=1,
                        arrowcolor=RED, ax=0, ay=-yshift_v,
                        font=dict(size=11, color=RED, family="DM Mono"),
                        bgcolor=_s2, bordercolor=RED, borderwidth=1, borderpad=4,
                    )
                # Actual value badges below bars — only for small rep sets
                if len(rep) <= 4:
                    badge_vbar(fig, rep, av, shift=6, pkr=True)
            lay = base(340, r=60, b=55)
            lay["barmode"] = "group"
            lay["bargap"]  = 0.28
            lay["yaxis2"]  = dict(
                overlaying="y", side="right",
                ticksuffix="%", tickfont=dict(color=RED, size=10, family="DM Mono"),
                gridcolor="rgba(0,0,0,0)", showgrid=False, zeroline=False,
                range=[0, 160],
            )
            fig.update_layout(lay); ax(fig, show_x_grid=True)
            leg(fig, ori="h", y=-0.22, x=0)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with r1b:
            section_hdr("🍩", "Revenue Mix by Initiative")
            colors6 = [GREEN, GOLD, BLUE, RED, PURPLE, "#FB923C"]
            fig2 = go.Figure(go.Pie(
                labels=df_fc["Initiative"].tolist(), values=df_fc["FC_Rev"].tolist(),
                hole=0.60, marker=dict(colors=colors6, line=dict(color=T["bg"], width=3)),
                textinfo="none",
                hovertemplate="<b>%{label}</b><br>₨%{value:,.0f}<br>%{percent}<extra></extra>"))
            total_fc_val = float(df_fc["FC_Rev"].sum())
            # Use Plotly native outside labels — avoids manual overlap entirely
            # Only label slices >= 5% to prevent crowding
            fc_vals_list  = [float(v) for v in df_fc["FC_Rev"]]
            fc_pcts       = [v/total_fc_val*100 if total_fc_val>0 else 0 for v in fc_vals_list]
            fc_labels_out = [
                f"{fmt_pkr(v,short=True)}<br>{p:.0f}%" if p >= 5 else ""
                for v, p in zip(fc_vals_list, fc_pcts)
            ]
            fig2.update_traces(
                text=fc_labels_out,
                textinfo="text",
                textposition="outside",
                textfont=dict(size=10, family="DM Mono", color=_tx),
                outsidetextfont=dict(size=10, family="DM Mono"),
                pull=[0.04 if p >= 5 else 0.01 for p in fc_pcts],
            )
            fig2.add_annotation(
                text=f"<b>{fmt_pkr(total_fc_val,short=True)}</b><br>Full-Year FC",
                x=0.38, y=0.5, showarrow=False,
                font=dict(size=13, color=_tx, family="DM Mono"),
                bgcolor=_s2, bordercolor=_b, borderwidth=1, borderpad=8)
            lay2 = base(380, r=140, b=8)
            lay2["title"] = dict(text="Full-Year Forecast Share",
                                 font=dict(size=11, color=_st), x=0.01, y=0.99)
            fig2.update_layout(lay2)
            leg(fig2, ori="v", y=0.5, x=1.02)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        if rep:
            r2a, r2b = st.columns([1.5, 1], gap="large")
            with r2a:
                section_hdr("🌊", "Initiative % Achievement (YTD)")
                inits = df_fc["Initiative"].tolist()
                fc_r  = [float(df_fc.loc[df_fc["Initiative"]==i, rep].values[0].sum()) for i in inits]
                act_r = [float(df_act.loc[df_act["Initiative"]==i, rep].values[0].sum()) for i in inits]
                pct_r = [(a/f*100) if f>0 else 0 for a,f in zip(act_r,fc_r)]
                dot_colors = [GREEN if p>=100 else (GOLD if p>=80 else RED) for p in pct_r]
                fig3 = go.Figure()
                # 100% target reference line
                fig3.add_hline(y=100, line_dash="dot", line_color=GOLD, line_width=1.5,
                    annotation_text="Target 100%", annotation_font_color=GOLD,
                    annotation_font_size=9, annotation_position="right")
                # % Achievement line
                fig3.add_trace(go.Scatter(
                    x=inits, y=pct_r, mode="lines+markers+text",
                    name="% Achievement",
                    line=dict(color=RED, width=3, shape="spline", smoothing=0.7),
                    marker=dict(size=14, color=dot_colors, symbol="circle",
                                line=dict(color="white", width=2)),
                    text=[f"{p:.0f}%" for p in pct_r],
                    textposition="top center",
                    textfont=dict(color=dot_colors, size=12, family="DM Mono"),
                    hovertemplate="<b>%{x}</b><br>Achievement: <b>%{y:.1f}%</b><extra></extra>",
                    fill="tozeroy", fillcolor=rgba(RED, 0.06),
                ))
                # Badge annotations
                for xi, (init_name, pct_v) in enumerate(zip(inits, pct_r)):
                    clr = GREEN if pct_v>=100 else (GOLD if pct_v>=80 else RED)
                    fig3.add_annotation(x=init_name, y=pct_v,
                        text=f"<b>{pct_v:.0f}%</b>",
                        showarrow=False, yanchor="bottom", yshift=22,
                        font=dict(size=11,color=clr,family="DM Mono"),
                        bgcolor=_s2, bordercolor=clr, borderwidth=1, borderpad=4)
                lay3 = base(330, r=20, b=60)
                lay3["yaxis"] = dict(ticksuffix="%", gridcolor=T["grid"],
                    tickcolor="rgba(0,0,0,0)", linecolor=T["border"],
                    tickfont=dict(color=T["subtext2"],size=10), zeroline=False,
                    showgrid=True, range=[0, max(pct_r)*1.3 if pct_r else 150])
                fig3.update_layout(lay3); ax(fig3, -15)
                st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

            with r2b:
                section_hdr("📋", "Initiative Scorecard")
                sorted_inits = sorted(zip(inits, fc_r, act_r, pct_r,
                                          [a-f for a,f in zip(act_r,fc_r)]),
                                      key=lambda x: x[3], reverse=True)
                rows_html = ""
                for name, fc_v, act_v, pct_v, var_v in sorted_inits:
                    clr = GREEN if pct_v>=100 else (GOLD if pct_v>=80 else RED)
                    vc  = GREEN if var_v>=0 else RED
                    sn  = name[:20]+"…" if len(name)>20 else name
                    rows_html += f"""
                    <tr>
                      <td style="padding:0.65rem 0.8rem;border-bottom:1px solid {_b};">
                        <div style="font-size:0.72rem;font-weight:600;color:{_tx};margin-bottom:4px;">{sn}</div>
                        <div style="background:{_s2};border-radius:3px;height:4px;width:100%;">
                          <div style="background:{clr};height:100%;width:{min(pct_v,100)}%;border-radius:3px;"></div>
                        </div>
                      </td>
                      <td style="padding:0.65rem 0.6rem;border-bottom:1px solid {_b};text-align:right;
                           font-family:'DM Mono',monospace;font-size:0.72rem;color:{GOLD};">{fmt_pkr(fc_v,short=True)}</td>
                      <td style="padding:0.65rem 0.6rem;border-bottom:1px solid {_b};text-align:right;
                           font-family:'DM Mono',monospace;font-size:0.72rem;color:{_tx};">{fmt_pkr(act_v,short=True)}</td>
                      <td style="padding:0.65rem 0.6rem;border-bottom:1px solid {_b};text-align:center;">
                        <span style="background:{clr}22;border:1px solid {clr}55;border-radius:5px;
                              padding:2px 7px;font-size:0.72rem;font-weight:700;color:{clr};
                              font-family:'DM Mono',monospace;">{pct_v:.0f}%</span></td>
                      <td style="padding:0.65rem 0.6rem;border-bottom:1px solid {_b};text-align:right;
                           font-family:'DM Mono',monospace;font-size:0.7rem;color:{vc};">{fmt_pkr(var_v,short=True,signed=True)}</td>
                    </tr>"""
                st.markdown(f"""
                <div style="background:{_sf};border:1px solid {_b};border-radius:12px;overflow:hidden;margin-top:2.4rem;">
                  <table style="width:100%;border-collapse:collapse;">
                    <thead><tr style="background:{_s2};">
                      <th style="padding:0.6rem 0.8rem;text-align:left;color:{_st};font-size:0.58rem;
                           letter-spacing:0.12em;text-transform:uppercase;font-weight:700;
                           border-bottom:1px solid {_b};">Initiative</th>
                      <th style="padding:0.6rem 0.6rem;text-align:right;color:{GOLD};font-size:0.58rem;
                           letter-spacing:0.12em;text-transform:uppercase;font-weight:700;
                           border-bottom:1px solid {_b};">FC Rev</th>
                      <th style="padding:0.6rem 0.6rem;text-align:right;color:{_st};font-size:0.58rem;
                           letter-spacing:0.12em;text-transform:uppercase;font-weight:700;
                           border-bottom:1px solid {_b};">Actual</th>
                      <th style="padding:0.6rem 0.6rem;text-align:center;color:{_st};font-size:0.58rem;
                           letter-spacing:0.12em;text-transform:uppercase;font-weight:700;
                           border-bottom:1px solid {_b};">Ach%</th>
                      <th style="padding:0.6rem 0.6rem;text-align:right;color:{_st};font-size:0.58rem;
                           letter-spacing:0.12em;text-transform:uppercase;font-weight:700;
                           border-bottom:1px solid {_b};">Var</th>
                    </tr></thead>
                    <tbody>{rows_html}</tbody>
                  </table>
                </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 2 — MONTHLY TRENDS (FC)
# ══════════════════════════════════════════════════════════════════════
with tab_trend:
    if not fc_ok:
        st.warning("FC data unavailable.")
    else:
        ta, tb = st.columns([1,1], gap="large")
        with ta:
            section_hdr("📈", "Cumulative Revenue Trajectory")
            cum_fc = list(np.cumsum(fc_mon))
            fig6 = go.Figure()
            fig6.add_trace(go.Scatter(x=MONTHS, y=cum_fc, name="Cumulative FC",
                mode="lines+markers", line=dict(color=GOLD, width=2, dash="dot"),
                marker=dict(size=5, color=GOLD), fill="tozeroy", fillcolor=AU_DIM,
                hovertemplate="<b>%{x}</b><br>Cum FC: <b>₨%{y:,.0f}</b><extra></extra>"))
            if rep:
                av = [act_mon[MONTHS.index(m)] for m in rep]
                cum_act = list(np.cumsum(av))
                fig6.add_trace(go.Scatter(x=rep, y=cum_act, name="Cumulative Actual",
                    mode="lines+markers", line=dict(color=GREEN, width=2.5),
                    marker=dict(size=9, color=GREEN, line=dict(color=T["bg"], width=2)),
                    fill="tozeroy", fillcolor=G_FILL,
                    hovertemplate="<b>%{x}</b><br>Cum Actual: <b>₨%{y:,.0f}</b><extra></extra>"))
                badge_scatter(fig6, rep, cum_act, pkr=True)
            fig6.add_hline(y=TOTAL_FC, line_dash="dash", line_color=RED, line_width=1.2,
                annotation_text=f"Target {fmt_pkr(TOTAL_FC, short=True)}",
                annotation_font_color=RED, annotation_font_size=9)
            fig6.update_layout(base(320, r=8, b=60))
            ax(fig6, show_x_grid=True); leg(fig6, ori="h", y=-0.28, x=0)
            st.plotly_chart(fig6, use_container_width=True, config={"displayModeBar": False})

        with tb:
            section_hdr("🏆", "YTD Initiative Ranking")
            df_r = df_act.copy()
            df_r["_ytd"] = df_r[MONTHS].sum(axis=1)
            df_r = df_r[df_r["_ytd"]>0].sort_values("_ytd", ascending=True)
            if not df_r.empty:
                n = len(df_r)
                bcolors = [GREEN if i==n-1 else (G_MED if i>=n-2 else G_DIM) for i in range(n)]
                fig7 = go.Figure(go.Bar(
                    x=df_r["_ytd"].astype(float), y=df_r["Initiative"],
                    orientation="h", marker=dict(color=bcolors, line=dict(color=G_LINE,width=1)),
                    hovertemplate="<b>%{y}</b><br>₨%{x:,.0f}<extra></extra>"))
                badge_hbar_pkr(fig7, df_r["_ytd"].astype(float).tolist(), df_r["Initiative"].tolist())
                lay7 = base(320, r=150, b=8)
                lay7["showlegend"] = False
                fig7.update_layout(lay7); ax(fig7)
                st.plotly_chart(fig7, use_container_width=True, config={"displayModeBar": False})

# ══════════════════════════════════════════════════════════════════════
# TAB 3 — ZSM PERFORMANCE
# ══════════════════════════════════════════════════════════════════════
with tab_zsm:
    if not zsm_ok:
        st.warning(f"ZSM data unavailable: {zsm_err}")
    else:
        ch, ct = st.columns([3,2], gap="medium")
        with ch:
            st.markdown('<div class="slbl">ZSM × Month Revenue Heatmap</div>', unsafe_allow_html=True)
            if use_mc:
                ph = dff.groupby(team_col)[use_mc].sum()
                ph = ph[ph.sum(axis=1) > 0]
                # Sort: KHI first, then LHR, then ISB (reversed for heatmap y so KHI is at top)
                def zsm_sort_key(name):
                    n = str(name).upper()
                    if "KHI" in n: return 0
                    if "LHR" in n: return 1
                    if "ISB" in n: return 2
                    return 3
                sorted_idx = sorted(range(len(ph)), key=lambda i: zsm_sort_key(ph.index[i]))
                # Reverse so KHI appears at top of heatmap (plotly renders bottom-up)
                ph = ph.iloc[sorted_idx[::-1]]
                if not ph.empty:
                    fig_h = go.Figure(go.Heatmap(
                        z=ph.values, x=ph.columns.tolist(),
                        y=[str(t)[:30] for t in ph.index],
                        colorscale=[
                            [0.0,  "#8B0000"],
                            [0.25, "#CC2200"],
                            [0.5,  "#FF8C00"],
                            [0.75, "#90C040"],
                            [1.0,  "#00C050"],
                        ],
                        hovertemplate="<b>%{y}</b> · <b>%{x}</b><br>Revenue: <b>%{z:,.0f}</b><extra></extra>",
                        showscale=True,
                        colorbar=dict(tickfont=dict(color=T["subtext2"],size=9,family="DM Mono"),
                                      bgcolor=T["surface"],bordercolor=T["border"],
                                      borderwidth=1,len=0.85,thickness=12)))
                    max_val = ph.values.max() if ph.values.max()>0 else 1
                    for ri in range(ph.values.shape[0]):
                        for ci in range(ph.values.shape[1]):
                            val = ph.values[ri,ci]
                            if val <= 0: continue
                            intensity = val/max_val
                            txt_color = "white" if intensity>0.3 else T["text"]
                            fig_h.add_annotation(x=ph.columns[ci], y=ph.index[ri],
                                text=f"<b>{fmt(val)}</b>", showarrow=False,
                                font=dict(size=11,color=txt_color,family="DM Mono"),
                                bgcolor=rgba(T["surface"],0.55),
                                bordercolor=rgba(T["border"],0.6),borderwidth=1,borderpad=4)
                    fig_h.update_layout(base(480)); ax(fig_h)
                    st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar":False})

        with ct:
            st.markdown('<div class="slbl">Revenue Leaderboard</div>', unsafe_allow_html=True)
            lb = dff.groupby(team_col)[all_vc].sum().sum(axis=1).sort_values(ascending=False).reset_index()
            lb.columns = ['ZSM','Revenue']
            lb.insert(0,'Rank',[f"#{i+1}" for i in range(len(lb))])
            ts_ = lb['Revenue'].sum()
            lb['Share'] = ((lb['Revenue']/ts_*100).round(1).astype(str)+'%') if ts_>0 else "—"
            lb['Revenue'] = lb['Revenue'].apply(fmt)
            st.dataframe(lb, use_container_width=True, height=480, hide_index=True)

        # ZSM bar chart — sorted KHI → LHR → ISB → others, then by revenue within group
        st.markdown('<div class="slbl" style="margin-top:0.8rem;">Revenue by ZSM Region</div>', unsafe_allow_html=True)
        def zsm_group(name):
            n = str(name).upper()
            if "KHI" in n: return 0
            if "LHR" in n: return 1
            if "ISB" in n: return 2
            return 3
        tr2_raw = dff.groupby(team_col)[all_vc].sum().sum(axis=1)
        tr2_df  = tr2_raw.reset_index()
        tr2_df.columns = ["ZSM","Rev"]
        tr2_df["grp"] = tr2_df["ZSM"].map(zsm_group)
        tr2_df = tr2_df.sort_values(["grp","Rev"], ascending=[False, True])
        tr2_vals  = tr2_df["Rev"].tolist()
        tr2_names = tr2_df["ZSM"].tolist()
        fig_z = go.Figure(go.Bar(x=tr2_vals, y=tr2_names, orientation='h',
            marker=dict(color=[PAL[i%len(PAL)] for i in range(len(tr2_names))], line=dict(width=0), opacity=0.92),
            hovertemplate="<b>%{y}</b><br>Revenue: <b>%{x:,.0f}</b><extra></extra>"))
        badge_hbar(fig_z, tr2_vals, tr2_names)
        fig_z.update_layout(base(320, r=140)); ax(fig_z)
        leg(fig_z); st.plotly_chart(fig_z, use_container_width=True, config={"displayModeBar":False})

# ══════════════════════════════════════════════════════════════════════
# TAB 4 — INITIATIVES (ZSM sheet)
# ══════════════════════════════════════════════════════════════════════
with tab_init:
    if not zsm_ok:
        st.warning("ZSM data unavailable.")
    else:
        ci1, ci2 = st.columns(2, gap="medium")
        with ci1:
            st.markdown('<div class="slbl">Initiative Revenue Ranking</div>', unsafe_allow_html=True)
            sir = dff.groupby(si_col)[all_vc].sum().sum(axis=1).sort_values(ascending=True)
            fig_si = go.Figure(go.Bar(x=sir.values, y=sir.index, orientation='h',
                marker=dict(color=PAL[:len(sir)], line=dict(width=0), opacity=0.92),
                hovertemplate="<b>%{y}</b>: <b>%{x:,.0f}</b><extra></extra>"))
            badge_hbar(fig_si, sir.values, sir.index.tolist())
            fig_si.update_layout(base(380, r=140)); ax(fig_si); leg(fig_si)
            st.plotly_chart(fig_si, use_container_width=True, config={"displayModeBar":False})

        with ci2:
            st.markdown('<div class="slbl">Revenue Mix by Initiative (ZSM data)</div>', unsafe_allow_html=True)
            sr = dff.groupby(si_col)[all_vc].sum().sum(axis=1).sort_values(ascending=False)
            sr = sr[sr>0]
            if not sr.empty:
                fig_pie = go.Figure(go.Pie(
                    labels=sr.index, values=sr.values, hole=0.60,
                    marker=dict(colors=PAL[:len(sr)], line=dict(color=T["bg"],width=3)),
                    textinfo='none',
                    hovertemplate="<b>%{label}</b><br>%{value:,.0f} (%{percent})<extra></extra>"))
                tv = sr.sum()
                zsm_pcts = [float(v)/tv*100 if tv>0 else 0 for v in sr.values]
                zsm_labels_out = [
                    f"{fmt(float(v))}<br>{p:.0f}%" if p >= 5 else ""
                    for v, p in zip(sr.values, zsm_pcts)
                ]
                fig_pie.update_traces(
                    text=zsm_labels_out,
                    textinfo="text",
                    textposition="outside",
                    textfont=dict(size=10, family="DM Mono", color=_tx),
                    outsidetextfont=dict(size=10, family="DM Mono"),
                    pull=[0.04 if p >= 5 else 0.01 for p in zsm_pcts],
                )
                fig_pie.add_annotation(text=f"<b>{fmt(tv)}</b><br>Total",
                    x=0.38, y=0.5, showarrow=False,
                    font=dict(size=13,color=_tx,family="DM Mono"),
                    bgcolor=_s2, bordercolor=_b, borderwidth=1, borderpad=8)
                fig_pie.update_layout(base(380, r=140)); leg(fig_pie, ori="v", y=0.5, x=1.02)
                st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar":False})

        # Stacked bar + MoM
        st.markdown('<div class="slbl" style="margin-top:0.6rem;">Stacked Revenue — ZSM × Initiative</div>', unsafe_allow_html=True)
        p2 = dff.groupby([team_col,si_col])[all_vc].sum().sum(axis=1).reset_index()
        p2.columns=[team_col,si_col,'Rev']
        p2 = p2[p2['Rev']>0]
        if not p2.empty:
            fig5 = go.Figure()
            for i, si in enumerate(p2[si_col].unique()):
                sub = p2[p2[si_col]==si]
                fig5.add_trace(go.Bar(x=sub[team_col], y=sub['Rev'], name=si,
                    marker=dict(color=PAL[i%len(PAL)], line=dict(width=0), opacity=0.92),
                    hovertemplate=f"<b>{si}</b><br>%{{x}}: <b>%{{y:,.0f}}</b><extra></extra>"))
            zsm_totals = p2.groupby(team_col)['Rev'].sum()
            badge_vbar(fig5, zsm_totals.index.tolist(), zsm_totals.values.tolist(), shift=8)
            fig5.update_layout(base(340, r=8, b=60), barmode='stack')
            ax(fig5, -15); leg(fig5, ori="h", y=-0.35, x=0)
            st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar":False})

        # Monthly trend for ZSM data
        if use_mc:
            st.markdown('<div class="slbl" style="margin-top:0.6rem;">Monthly Revenue Trend (ZSM)</div>', unsafe_allow_html=True)
            mt = dff[use_mc].sum()
            fig_mt = go.Figure()
            fig_mt.add_trace(go.Scatter(x=use_mc, y=mt.values, mode='lines+markers',
                name='Total', line=dict(color=GREEN, width=3, shape='spline'),
                marker=dict(size=10, color=GREEN, line=dict(color=T["bg"],width=2)),
                fill='tozeroy', fillcolor=rgba(GREEN,0.07),
                hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>"))
            badge_scatter(fig_mt, use_mc, mt.values)
            fig_mt.update_layout(base(300, r=8, b=50))
            ax(fig_mt, show_x_grid=True); leg(fig_mt, ori="h", y=-0.3, x=0)
            st.plotly_chart(fig_mt, use_container_width=True, config={"displayModeBar":False})

# ══════════════════════════════════════════════════════════════════════
# TAB 5 — INITIATIVE DRILL-DOWN (FC sheet)
# ══════════════════════════════════════════════════════════════════════
with tab_drill:
    if not fc_ok:
        st.warning("FC data unavailable.")
    else:
        section_hdr("🔍", "Initiative Deep Dive")
        sel = st.selectbox("Select Initiative", df_fc["Initiative"].tolist(),
                           label_visibility="visible")
        fr = df_fc[df_fc["Initiative"]==sel].iloc[0]
        ar = df_act[df_act["Initiative"]==sel].iloc[0]
        fc_vals  = [float(fr[m]) for m in MONTHS]
        act_vals = [float(ar[m]) for m in MONTHS]
        rep_fc   = sum(float(fr[m]) for m in rep) if rep else 0
        rep_act  = sum(float(ar[m]) for m in rep) if rep else 0
        rep_var  = rep_act - rep_fc
        rep_pct  = (rep_act/rep_fc*100) if rep_fc>0 else 0

        d1,d2,d3,d4 = st.columns(4)
        with d1: st.metric("Full-Year FC", fmt_pkr(float(fr["FC_Rev"])))
        with d2: st.metric("YTD Actual",   fmt_pkr(rep_act))
        with d3: st.metric("YTD FC",       fmt_pkr(rep_fc))
        with d4: st.metric("Achievement",  f"{rep_pct:.1f}%", fmt_pkr(rep_var, signed=True))

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        da, db = st.columns([1.6,1], gap="large")
        with da:
            section_hdr("📈", f"{sel} · Monthly Detail — FC (bars) vs Actual (line)")
            fig4 = go.Figure()
            # Forecast as bars — all 12 months
            fig4.add_trace(go.Bar(x=MONTHS, y=fc_vals, name="Forecast",
                marker=dict(color=AU_MED, line=dict(color=GOLD, width=1.2)),
                hovertemplate="<b>%{x}</b><br>FC: <b>₨%{y:,.0f}</b><extra></extra>"))
            if rep:
                av = [act_vals[MONTHS.index(m)] for m in rep]
                # Actual as a bold line over the bars
                fig4.add_trace(go.Scatter(x=rep, y=av, name="Actual",
                    mode="lines+markers",
                    line=dict(color=GREEN, width=3, shape="spline", smoothing=0.6),
                    marker=dict(size=10, color=GREEN, symbol="circle",
                                line=dict(color=T["bg"], width=2)),
                    hovertemplate="<b>%{x}</b><br>Actual: <b>₨%{y:,.0f}</b><extra></extra>"))
                badge_scatter(fig4, rep, av, pkr=True)
            lay4 = base(310, r=8, b=60)
            fig4.update_layout(lay4); ax(fig4, show_x_grid=True)
            leg(fig4, ori="h", y=-0.28, x=0)
            st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar":False})

        with db:
            section_hdr("🎯", "Achievement Gauge")
            gc = GREEN if rep_pct>=100 else (GOLD if rep_pct>=75 else RED)
            fig5g = go.Figure(go.Indicator(
                mode="gauge+number+delta", value=round(rep_pct,1),
                delta=dict(reference=100, valueformat=".1f",
                           increasing=dict(color=GREEN), decreasing=dict(color=RED),
                           suffix=" pp"),
                number=dict(suffix="%", font=dict(size=28, color=_tx, family="DM Mono")),
                gauge=dict(axis=dict(range=[0,150],
                               tickfont=dict(color=_st,size=8),
                               tickvals=[0,50,75,100,125,150],
                               ticktext=["0%","50%","75%","100%","125%","150%"]),
                    bar=dict(color=gc, thickness=0.25),
                    bgcolor="rgba(0,0,0,0)", bordercolor=_b, borderwidth=1,
                    steps=[dict(range=[0,75],color=R_DIM),
                           dict(range=[75,100],color=AU_DIM),
                           dict(range=[100,150],color=G_DIM)],
                    threshold=dict(line=dict(color=GREEN,width=2.5),thickness=0.8,value=100)),
                title=dict(text=f"YTD Achievement", font=dict(size=10,color=_st))))
            fig5g.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                font=dict(family="DM Sans",color=_tx),
                                margin=dict(l=20,r=20,t=55,b=10), height=300)
            st.plotly_chart(fig5g, use_container_width=True, config={"displayModeBar":False})

# ══════════════════════════════════════════════════════════════════════
# TAB 6 — TRENDS & HEATMAP (FC sheet)
# ══════════════════════════════════════════════════════════════════════
with tab_heat:
    if not fc_ok:
        st.warning("FC data unavailable.")
    else:
        section_hdr("🔥", "Forecast Revenue Intensity Heatmap")
        heat_z = [[float(df_fc.loc[df_fc["Initiative"]==init, m].values[0])
                   for m in MONTHS] for init in df_fc["Initiative"]]
        fig8 = go.Figure(go.Heatmap(
            z=heat_z, x=MONTHS, y=df_fc["Initiative"].tolist(),
            colorscale=[[0,T["surface2"]],[0.25,G_DIM],[0.6,G_MED],[1,GREEN]],
            showscale=True,
            hovertemplate="<b>%{y}</b><br>%{x}: <b>₨%{z:,.0f}</b><extra></extra>",
            colorbar=dict(tickfont=dict(color=_st,size=9,family="DM Mono"),
                          tickformat=",.0f", outlinecolor=_b, outlinewidth=1,
                          bgcolor="rgba(0,0,0,0)")))
        n_init = len(df_fc)
        max_heat = max(max(row) for row in heat_z) if heat_z else 1
        for ri in range(n_init):
            for ci, m in enumerate(MONTHS):
                val = heat_z[ri][ci]
                if val <= 0: continue
                intensity = val/max_heat
                tc_h = "white" if intensity>0.4 else T["text"]
                fig8.add_annotation(x=m, y=df_fc["Initiative"].iloc[ri],
                    text=f"<b>{fmt_pkr(val,short=True)}</b>", showarrow=False,
                    font=dict(size=10,color=tc_h,family="DM Mono"),
                    bgcolor=rgba(T["surface"],0.5),
                    bordercolor=rgba(T["border"],0.5),borderwidth=1,borderpad=3)
        fig8.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=280, font=dict(family="DM Sans",color=_tx,size=11),
            margin=dict(l=8,r=90,t=16,b=8))
        fig8.update_xaxes(side="top", tickfont=dict(color=_st,size=10,family="DM Mono"),
                          gridcolor=_b, linecolor=_b)
        fig8.update_yaxes(gridcolor="rgba(0,0,0,0)",
                          tickfont=dict(size=9,color=_tx,family="DM Mono"), linecolor=_b)
        st.plotly_chart(fig8, use_container_width=True, config={"displayModeBar":False})

# ══════════════════════════════════════════════════════════════════════
# TAB 7 — DATA
# ══════════════════════════════════════════════════════════════════════
with tab_data:
    section_hdr("🗃", "Source Data")
    view_opts = []
    if fc_ok:  view_opts += ["📅 FC Forecast","✅ FC Actual","📊 FC Variance"]
    if zsm_ok: view_opts += ["🏢 ZSM Performance"]
    view = st.selectbox("Data View", view_opts, label_visibility="visible")

    if "Forecast" in view and fc_ok:
        rows = [[r["Initiative"], fmt_pkr(float(r["FC_Rev"]))] +
                [fmt_pkr(float(r[m])) for m in MONTHS] + [fmt_pkr(float(r["YTD"]))]
                for _,r in df_fc.iterrows()]
        cols_h = ["Initiative","FC Rev"] + MONTHS + ["YTD FC"]
    elif "Actual" in view and fc_ok:
        rows = [[r["Initiative"]] + [fmt_pkr(float(r[m])) for m in MONTHS] +
                [fmt_pkr(float(r.get("YTD", sum(float(r[m]) for m in MONTHS))))]
                for _,r in df_act.iterrows()]
        cols_h = ["Initiative"] + MONTHS + ["YTD Actual"]
    elif "Variance" in view and fc_ok:
        rows = []
        for init in df_fc["Initiative"]:
            fc_r = df_fc[df_fc["Initiative"]==init].iloc[0]
            act_r= df_act[df_act["Initiative"]==init].iloc[0]
            rfc  = sum(float(fc_r[m]) for m in rep) if rep else 0
            ract = sum(float(act_r[m]) for m in rep) if rep else 0
            vv   = ract - rfc
            pp   = f"{ract/rfc*100:.0f}%" if rfc>0 else "N/A"
            rows.append([init, fmt_pkr(float(fc_r["FC_Rev"])), fmt_pkr(rfc),
                         fmt_pkr(ract), fmt_pkr(vv,signed=True), pp,
                         "✅ On Track" if (ract/rfc*100 if rfc>0 else 0)>=90 else "⚠️ At Risk"])
        cols_h = ["Initiative","Full-Year FC","YTD FC","YTD Actual","Variance","% Ach","Status"]
    elif "ZSM" in view and zsm_ok:
        display_df = dff.copy()
        for c in all_vc: display_df[c] = display_df[c].apply(fmt)
        st.dataframe(display_df, use_container_width=True, height=520, hide_index=True)
        st.download_button("⬇ Download ZSM Data", dff.to_csv(index=False).encode(),
                           "zameen_zsm.csv","text/csv")
        rows = None; cols_h = []

    if 'rows' in dir() and rows is not None:
        th = (f'padding:0.6rem 0.9rem;text-align:left;color:{_st};font-size:0.58rem;'
              f'letter-spacing:0.12em;text-transform:uppercase;font-weight:700;'
              f'border-bottom:1px solid {_b};white-space:nowrap;')
        td_s = (f'padding:0.6rem 0.9rem;border-bottom:1px solid {_b};'
                f'font-family:DM Mono,monospace;font-size:0.72rem;color:{_tx};white-space:nowrap;')
        hdrs_html = "".join(f'<th style="{th}">{c}</th>' for c in cols_h)
        body_html = "".join(f'<tr>{"".join(f"<td style={chr(39)}{td_s}{chr(39)}>{v}</td>" for v in row)}</tr>'
                            for row in rows)
        st.markdown(f"""
        <div style="background:{_sf};border:1px solid {_b};border-radius:12px;overflow:hidden;">
          <div style="overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;">
            <thead><tr style="background:{_s2};">{hdrs_html}</tr></thead>
            <tbody>{body_html}</tbody>
          </table></div>
          <div style="padding:0.6rem 0.9rem;border-top:1px solid {_b};font-size:0.6rem;
               color:{_st};display:flex;justify-content:space-between;">
            <span>{len(rows)} rows</span>
            <span style="font-family:'DM Mono',monospace;">🔴 Live · Google Sheets · 5 min cache</span>
          </div>
        </div>""", unsafe_allow_html=True)
        if fc_ok:
            var_c = RED if TOTAL_VAR<0 else GREEN
            st.markdown(f"""
            <div style="background:{G_DIM};border:1px solid {rgba(GREEN,0.3)};border-radius:10px;
                 padding:0.9rem 1.4rem;display:flex;gap:2.5rem;align-items:center;
                 flex-wrap:wrap;margin-top:1rem;">
              {pill_stat("Full-Year FC",   fmt_pkr(TOTAL_FC),   GOLD)}
              <div style="width:1px;height:30px;background:{_b};"></div>
              {pill_stat("YTD Actual",     fmt_pkr(TOTAL_ACT),  GREEN)}
              <div style="width:1px;height:30px;background:{_b};"></div>
              {pill_stat("YTD Variance",   fmt_pkr(TOTAL_VAR, signed=True), var_c)}
              <div style="width:1px;height:30px;background:{_b};"></div>
              {pill_stat("Achievement",    f"{YTD_PCT:.0f}%",   _tx)}
              <div style="width:1px;height:30px;background:{_b};"></div>
              {pill_stat("Run Rate (Ann.)",fmt_pkr(run_rate),   BLUE)}
            </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="border-top:1px solid {_b};margin-top:3rem;padding:1.2rem 0 0.5rem;
     display:flex;justify-content:space-between;align-items:center;
     font-size:0.6rem;color:{_st};letter-spacing:0.05em;">
  <span>zameen.com · Unified Strategic Intelligence · FY2026</span>
  <span style="font-family:'DM Mono',monospace;">
    🔴 Live · Two Google Sheets · st.cache_data(ttl=300) · Password protected
  </span>
</div>""", unsafe_allow_html=True)
