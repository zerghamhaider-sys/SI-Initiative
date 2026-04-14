import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io, requests

st.set_page_config(page_title="Zameen · SI Intelligence", page_icon="🏢",
                   layout="wide", initial_sidebar_state="collapsed")

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True
DM = st.session_state.dark_mode

# ── Premium dark: deep navy-charcoal, not pure black ──────────────────
D = dict(
    bg          = "#080C14",       # near-black with blue cast
    surface     = "#0D1525",       # card background
    surface2    = "#111D30",       # input / hover
    surface3    = "#172033",       # subtle lift
    border      = "#1E2D47",       # subtle borders
    border2     = "#243452",       # slightly brighter borders
    text        = "#F0F4FF",       # crisp white-blue
    subtext     = "#5E7499",       # muted blue-grey
    subtext2    = "#8BA3C7",       # lighter subtext for labels
    green       = "#10D97A",       # vivid emerald
    green2      = "#0BAF62",       # darker emerald for gradients
    gold        = "#F0B429",       # warm amber
    gold2       = "#C4901A",       # deeper gold
    red         = "#F04060",       # coral red
    blue        = "#4D9FFF",       # accent blue
    purple      = "#9B7FFF",       # accent purple
    grid        = "#0F1A2C",       # very subtle grid
    tag_bg      = "#0D2238",
    tag_border  = "#10D97A",
    tag_text    = "#10D97A",
)
# ── Premium light: warm ivory, not flat white ─────────────────────────
L = dict(
    bg          = "#F5F7FC",
    surface     = "#FFFFFF",
    surface2    = "#EDF1FA",
    surface3    = "#E3E9F5",
    border      = "#D0DAF0",
    border2     = "#BFC9E8",
    text        = "#0A1628",
    subtext     = "#4E6080",
    subtext2    = "#6B7FA0",
    green       = "#008A48",
    green2      = "#006A36",
    gold        = "#C47B00",
    gold2       = "#9A5F00",
    red         = "#D42050",
    blue        = "#2563EB",
    purple      = "#7C3AED",
    grid        = "#E8EEF8",
    tag_bg      = "#E0F5EC",
    tag_border  = "#008A48",
    tag_text    = "#006A36",
)
T = D if DM else L
GREEN  = T["green"]
GOLD   = T["gold"]
RED    = T["red"]
BLUE   = T["blue"]
PURPLE = T["purple"]

# Premium curated palette — distinct, rich, harmonious
PAL = [
    T["green"], T["gold"], T["blue"], T["purple"],
    T["red"],   "#20C4D8", "#FF8C42", "#E040FB",
    "#00BFA5",  "#FFB300",
]

def rgba(h, a=0.15):
    h = h.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{a})"

def fmt(n):
    try:
        n = float(n)
        if n >= 1_000_000: return f"{n/1_000_000:.2f}M"
        if n >= 1_000:     return f"{n/1_000:.1f}K"
        return f"{n:,.0f}"
    except: return "0"

# ── Chart base — clean, no conflicts ─────────────────────────────────
def base(h=380, l=8, r=80, t=16, b=8):
    return dict(
        paper_bgcolor = T["surface"],
        plot_bgcolor  = T["surface"],
        font = dict(family="'DM Sans', Inter, sans-serif", color=T["subtext2"], size=11),
        margin = dict(l=l, r=r, t=t, b=b),
        height = h,
    )

def ax(fig, angle=0, show_x_grid=False):
    fig.update_xaxes(
        gridcolor   = T["grid"] if show_x_grid else "rgba(0,0,0,0)",
        tickcolor   = "rgba(0,0,0,0)",
        linecolor   = T["border"],
        tickfont    = dict(color=T["subtext2"], size=11),
        zeroline    = False,
        tickangle   = angle,
        showgrid    = show_x_grid,
    )
    fig.update_yaxes(
        gridcolor   = T["grid"],
        tickcolor   = "rgba(0,0,0,0)",
        linecolor   = "rgba(0,0,0,0)",
        tickfont    = dict(color=T["subtext2"], size=11),
        zeroline    = False,
        showgrid    = True,
    )
    return fig

def leg(fig, ori="v", y=0.5, x=1.02):
    fig.update_layout(legend=dict(
        bgcolor      = T["surface2"],
        bordercolor  = T["border"],
        borderwidth  = 1,
        font         = dict(size=10, color=T["text"]),
        orientation  = ori, y=y, x=x,
        itemsizing   = "constant",
    ))
    return fig

def badge_labels_hbar(fig, values, labels, xref="x", yref="y"):
    """Add pill-badge annotations for horizontal bar outside labels."""
    for val, lbl in zip(values, labels):
        fig.add_annotation(
            x=val, y=lbl,
            text=f"<b>{fmt(val)}</b>",
            showarrow=False,
            xanchor="left",
            xshift=8,
            font=dict(size=13, color=T["text"], family="DM Mono"),
            bgcolor=T["surface2"],
            bordercolor=T["border"],
            borderwidth=1,
            borderpad=5,
            opacity=1.0,
        )
    return fig

def badge_labels_vbar(fig, x_vals, y_vals, shift=10):
    """Add pill-badge annotations for vertical bar outside labels."""
    for x, y in zip(x_vals, y_vals):
        if y <= 0: continue
        fig.add_annotation(
            x=x, y=y,
            text=f"<b>{fmt(y)}</b>",
            showarrow=False,
            yanchor="bottom",
            yshift=shift,
            font=dict(size=12, color=T["text"], family="DM Mono"),
            bgcolor=T["surface2"],
            bordercolor=T["border"],
            borderwidth=1,
            borderpad=4,
            opacity=1.0,
        )
    return fig

def badge_labels_scatter(fig, x_vals, y_vals):
    """Add pill-badge annotations above scatter/line points."""
    for x, y in zip(x_vals, y_vals):
        fig.add_annotation(
            x=x, y=y,
            text=f"<b>{fmt(y)}</b>",
            showarrow=False,
            yanchor="bottom",
            yshift=14,
            font=dict(size=13, color=T["text"], family="DM Mono"),
            bgcolor=T["surface2"],
            bordercolor=GREEN,
            borderwidth=1,
            borderpad=5,
            opacity=1.0,
        )
    return fig

# ─────────────────────────────────────────────────────────────────────
# PREMIUM CSS
# ─────────────────────────────────────────────────────────────────────
_g  = T["grid"];    _b  = T["border"];   _b2 = T["border2"]
_bg = T["bg"];      _sf = T["surface"];  _s2 = T["surface2"]
_tx = T["text"];    _st = T["subtext"];  _s3 = T["surface3"]
_s2t= T["subtext2"]
_gr = GREEN; _go = GOLD; _re = RED

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}

html, body, [class*="css"], .stApp {{
  font-family: 'DM Sans', sans-serif !important;
  background: {_bg} !important;
  color: {_tx} !important;
  -webkit-font-smoothing: antialiased;
}}

.block-container {{ padding: 0 2.6rem 4rem !important; max-width: 1520px !important; }}
section[data-testid="stSidebar"] {{ display: none !important; }}
#MainMenu, footer, header, div[data-testid="stToolbar"], .stDeployButton {{
  display: none !important; visibility: hidden !important;
}}

/* ════════════════════════════════════
   LOGIN — full-page immersive
   ════════════════════════════════════ */
.login-page {{
  display: flex; align-items: center; justify-content: center;
  min-height: 88vh;
}}
.login-card {{
  width: 420px;
  background: {_sf};
  border: 1px solid {_b2};
  border-radius: 24px;
  padding: 3.2rem 2.8rem 2.4rem;
  text-align: center;
  box-shadow: 0 32px 80px {rgba(_bg, 0.9)}, 0 0 0 1px {rgba(GREEN, 0.08)};
}}
.login-mark {{
  width: 60px; height: 60px;
  background: linear-gradient(135deg, {GREEN} 0%, {T["green2"]} 100%);
  border-radius: 16px;
  margin: 0 auto 1.6rem;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.6rem; font-weight: 900; color: #fff; letter-spacing: -1px;
  box-shadow: 0 8px 24px {rgba(GREEN, 0.35)};
}}
.login-eyebrow {{
  font-size: 0.62rem; font-weight: 600; letter-spacing: 2.5px;
  text-transform: uppercase; color: {GREEN}; margin-bottom: 10px;
}}
.login-h {{
  font-size: 1.65rem; font-weight: 700; color: {_tx};
  letter-spacing: -0.6px; line-height: 1.25; margin-bottom: 8px;
}}
.login-sub {{
  font-size: 0.82rem; color: {_st}; line-height: 1.65; margin-bottom: 2rem;
}}
.login-divider {{
  height: 1px; background: {_b}; margin: 1.4rem 0;
}}
.login-foot {{
  font-size: 0.67rem; color: {_st}; letter-spacing: 0.5px;
}}

/* ════════════════════════════════════
   TOPBAR
   ════════════════════════════════════ */
.topbar {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 1.1rem 0 1rem;
  border-bottom: 1px solid {_b};
  margin-bottom: 1.4rem;
}}
.topbar-brand {{ display: flex; align-items: center; gap: 14px; }}
.topbar-mark {{
  width: 38px; height: 38px;
  background: linear-gradient(135deg, {GREEN} 0%, {T["green2"]} 100%);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 800; color: #fff; letter-spacing: -1px;
  flex-shrink: 0;
  box-shadow: 0 4px 14px {rgba(GREEN, 0.3)};
}}
.topbar-title {{
  font-size: 1rem; font-weight: 700; color: {_tx}; letter-spacing: -0.3px;
}}
.topbar-sub {{
  font-size: 0.68rem; color: {_st}; margin-top: 2px; font-weight: 400;
}}
.topbar-right {{ display: flex; align-items: center; gap: 10px; }}
.live-badge {{
  display: inline-flex; align-items: center; gap: 6px;
  background: {rgba(GREEN, 0.09)};
  border: 1px solid {rgba(GREEN, 0.22)};
  color: {GREEN}; font-size: 0.65rem; font-weight: 600;
  letter-spacing: 1.2px; padding: 5px 12px;
  border-radius: 20px; text-transform: uppercase;
}}
.live-dot {{
  width: 6px; height: 6px; background: {GREEN};
  border-radius: 50%; animation: pulse 2s ease-in-out infinite;
}}
@keyframes pulse {{
  0%, 100% {{ opacity: 1; transform: scale(1); }}
  50%       {{ opacity: 0.3; transform: scale(0.8); }}
}}

/* ════════════════════════════════════
   FILTER BAR
   ════════════════════════════════════ */
.filter-wrap {{
  background: {_sf};
  border: 1px solid {_b};
  border-radius: 12px;
  padding: 14px 18px 10px;
  margin-bottom: 1.4rem;
}}

/* ════════════════════════════════════
   KPI CARDS
   ════════════════════════════════════ */
.kpi-row {{
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 1.4rem;
}}
.kpi {{
  background: {_sf};
  border: 1px solid {_b};
  border-radius: 12px;
  padding: 1.1rem 1.2rem 1rem;
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s;
}}
.kpi:hover {{ border-color: {_b2}; }}
.kpi-stripe {{
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, {GREEN}, {T["green2"]});
  border-radius: 12px 12px 0 0;
}}
.kpi-stripe.gold {{
  background: linear-gradient(90deg, {GOLD}, {T["gold2"]});
}}
.kpi-stripe.blue {{
  background: linear-gradient(90deg, {BLUE}, {PURPLE});
}}
.kpi-stripe.dim {{
  background: {_b2};
}}
.kpi-lbl {{
  font-size: 0.62rem; font-weight: 600; letter-spacing: 1.4px;
  text-transform: uppercase; color: {_st}; margin-bottom: 7px;
}}
.kpi-val {{
  font-size: 1.55rem; font-weight: 700; color: {_tx};
  letter-spacing: -0.8px; line-height: 1.1;
  font-variant-numeric: tabular-nums;
  font-family: 'DM Mono', monospace;
}}
.kpi-note {{
  font-size: 0.69rem; color: {_st}; margin-top: 5px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}

/* ════════════════════════════════════
   SECTION LABEL
   ════════════════════════════════════ */
.slbl {{
  font-size: 0.65rem; font-weight: 600; letter-spacing: 1.8px;
  text-transform: uppercase; color: {_s2t}; margin-bottom: 0.75rem;
  display: flex; align-items: center; gap: 8px;
}}
.slbl::before {{
  content: ''; display: block; width: 3px; height: 12px;
  background: linear-gradient(180deg, {GREEN}, {T["green2"]});
  border-radius: 2px;
}}

/* ════════════════════════════════════
   TABS
   ════════════════════════════════════ */
div[data-baseweb="tab-list"] {{
  background: {_s2} !important;
  border-radius: 10px !important;
  border: 1px solid {_b} !important;
  padding: 4px !important;
  gap: 2px !important;
}}
button[data-baseweb="tab"] {{
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.8rem !important;
  font-weight: 500 !important;
  color: {_st} !important;
  border-radius: 7px !important;
  padding: 7px 20px !important;
  transition: all 0.15s !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
  background: linear-gradient(135deg, {rgba(GREEN,0.18)}, {rgba(GREEN,0.08)}) !important;
  color: {GREEN} !important;
  font-weight: 600 !important;
}}
div[data-baseweb="tab-highlight"],
div[data-baseweb="tab-border"] {{ display: none !important; }}

/* ════════════════════════════════════
   MULTISELECT / DROPDOWNS
   ════════════════════════════════════ */
div[data-baseweb="select"] > div {{
  background: {_s2} !important;
  border: 1px solid {_b} !important;
  border-radius: 9px !important;
  min-height: 40px !important;
  transition: border-color 0.15s !important;
}}
div[data-baseweb="select"] > div:focus-within {{
  border-color: {GREEN} !important;
  box-shadow: 0 0 0 3px {rgba(GREEN, 0.12)} !important;
}}
div[data-baseweb="popover"] ul {{
  background: {_sf} !important;
  border: 1px solid {_b2} !important;
  border-radius: 10px !important;
  box-shadow: 0 16px 48px rgba(0,0,0,0.4) !important;
}}
div[data-baseweb="popover"] li {{
  color: {_tx} !important;
  font-size: 0.82rem !important;
  background: {_sf} !important;
}}
div[data-baseweb="popover"] li:hover {{
  background: {_s2} !important;
  color: {_tx} !important;
}}
div[data-baseweb="popover"] {{
  background: {_sf} !important;
}}
div[data-testid="stMultiSelect"] [data-baseweb="tag"] {{
  background: {T["tag_bg"]} !important;
  border: 1px solid {T["tag_border"]} !important;
  color: {T["tag_text"]} !important;
  border-radius: 6px !important;
  font-size: 0.73rem !important;
  font-weight: 600 !important;
}}
div[data-testid="stMultiSelect"] [data-baseweb="tag"] span {{
  color: {T["tag_text"]} !important;
}}
div[data-testid="stMultiSelect"] [data-baseweb="tag"] [role="presentation"] {{
  color: {T["tag_text"]} !important;
  opacity: 0.7;
}}
/* Input text inside multiselect */
div[data-testid="stMultiSelect"] input {{
  color: {_tx} !important;
  background: transparent !important;
}}
/* Dropdown option check color */
div[data-baseweb="popover"] [aria-selected="true"] {{
  background: {T["tag_bg"]} !important;
  color: {T["tag_text"]} !important;
}}
div[data-testid="stMultiSelect"] label,
div[data-testid="stSelectbox"] label {{
  font-size: 0.62rem !important;
  font-weight: 600 !important;
  letter-spacing: 1.3px !important;
  text-transform: uppercase !important;
  color: {_st} !important;
}}

/* ════════════════════════════════════
   BUTTONS
   ════════════════════════════════════ */
.stButton > button {{
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.76rem !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  background: {_s2} !important;
  color: {_tx} !important;
  border: 1px solid {_b} !important;
  padding: 6px 14px !important;
  transition: all 0.15s !important;
}}
.stButton > button:hover {{
  border-color: {GREEN} !important;
  color: {GREEN} !important;
  background: {rgba(GREEN, 0.06)} !important;
}}
.btn-primary > button {{
  background: linear-gradient(135deg, {GREEN} 0%, {T["green2"]} 100%) !important;
  color: #fff !important;
  border: none !important;
  font-size: 0.92rem !important;
  font-weight: 700 !important;
  padding: 12px 14px !important;
  border-radius: 10px !important;
  box-shadow: 0 6px 20px {rgba(GREEN, 0.35)} !important;
  letter-spacing: 0.2px !important;
}}
.btn-primary > button:hover {{
  box-shadow: 0 8px 28px {rgba(GREEN, 0.45)} !important;
  transform: translateY(-1px) !important;
}}

/* ════════════════════════════════════
   INPUT
   ════════════════════════════════════ */
div[data-testid="stTextInput"] > div > div > input {{
  background: {_s2} !important;
  border: 1px solid {_b} !important;
  border-radius: 10px !important;
  color: {_tx} !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.92rem !important;
  padding: 12px 16px !important;
  transition: all 0.15s !important;
}}
div[data-testid="stTextInput"] > div > div > input:focus {{
  border-color: {GREEN} !important;
  box-shadow: 0 0 0 3px {rgba(GREEN, 0.14)} !important;
  outline: none !important;
}}
div[data-testid="stTextInput"] label {{ display: none !important; }}

/* ════════════════════════════════════
   TABLE & SCROLLBAR
   ════════════════════════════════════ */
div[data-testid="stDataFrame"] {{ border-radius: 10px; overflow: hidden; }}
div[data-testid="stDataFrame"] iframe {{ background: {_sf} !important; }}
div[data-testid="stDataFrame"] * {{ color: {_tx} !important; }}
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: {_s2}; }}
::-webkit-scrollbar-thumb {{
  background: {_b2}; border-radius: 10px;
}}

/* ════════════════════════════════════
   PLOTLY CHART CONTAINERS
   ════════════════════════════════════ */
div[data-testid="stPlotlyChart"] {{
  background: transparent !important;
  border-radius: 12px !important;
  padding: 0 !important;
}}
div[data-testid="stPlotlyChart"] > div {{
  background: transparent !important;
}}
/* Force plotly SVG text to use theme color */
.js-plotly-plot .plotly text {{
  fill: {_s2t} !important;
}}
.js-plotly-plot .plotly .gtitle {{
  fill: {_tx} !important;
}}

/* ════════════════════════════════════
   DOWNLOAD BUTTON
   ════════════════════════════════════ */
div[data-testid="stDownloadButton"] > button {{
  background: {_s2} !important;
  border: 1px solid {_b2} !important;
  color: {_tx} !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: 0.8rem !important;
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# AUTH — PREMIUM LOGIN
# ─────────────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, mc, _ = st.columns([1, 1, 1])
    with mc:
        st.markdown(f"""
        <div style="padding-top:12vh;">
          <div class="login-card">
            <div class="login-mark">Z</div>
            <div class="login-eyebrow">Restricted Access</div>
            <div class="login-h">Sign in to your<br>Intelligence Portal</div>
            <div class="login-sub">Enter your access password to view<br>the ZSM Strategic Initiatives data.</div>
          </div>
        </div>""", unsafe_allow_html=True)
        pw = st.text_input("pw", type="password", placeholder="Enter access password",
                           label_visibility="collapsed")
        st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
        if st.button("Sign In →", use_container_width=True):
            if pw == "7862":
                st.session_state.authenticated = True; st.rerun()
            else:
                st.markdown(
                    f'<p style="color:{RED};font-size:0.8rem;text-align:center;'
                    f'margin-top:10px;font-weight:500;">⚠ Incorrect password — please try again</p>',
                    unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f'<p style="text-align:center;font-size:0.65rem;color:{T["subtext"]};'
                    f'margin-top:1.4rem;letter-spacing:0.5px;">'
                    f'Zameen.com · Strategic Intelligence · Confidential</p>',
                    unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────────────
# DATA LOAD
# ─────────────────────────────────────────────────────────────────────
SHEET_ID = "14UEnSMs1GAuvUVxp7aq_q71YYc_d0VaEVrygarXzaxs"
CSV_URL  = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

@st.cache_data(ttl=300)
def load_data():
    resp = requests.get(CSV_URL, timeout=15); resp.raise_for_status()
    raw = pd.read_csv(io.StringIO(resp.text), header=None, dtype=str).fillna('')
    hr = 0; best = -1
    for i in range(min(10, len(raw))):
        row = raw.iloc[i]
        score = (row.str.strip() != '').sum()
        score += sum(k in ' '.join(row.str.lower())
                     for k in ['jan','feb','mar','regional','initiative','zsm','ytd']) * 3
        if score > best: best = score; hr = i
    df = pd.read_csv(io.StringIO(resp.text), skiprows=hr, dtype=str).fillna('')
    df.columns = [str(c).strip() for c in df.columns]
    df = df[[c for c in df.columns
             if not c.lower().startswith('unnamed') and c.strip() != '']]
    df = df[df.apply(lambda r: r.str.strip().ne('').any(), axis=1)].reset_index(drop=True)
    tc_list, nc = [], []
    for col in df.columns:
        ne = df[col][df[col].str.strip() != '']
        if ne.empty: continue
        ratio = pd.to_numeric(ne.str.replace(',', '', regex=False).str.strip(),
                              errors='coerce').notna().mean()
        (nc if ratio >= 0.5 else tc_list).append(col)
    if len(tc_list) < 2: tc_list = list(df.columns[:2]); nc = list(df.columns[2:])
    tc, sc = tc_list[0], tc_list[1]
    for col in nc:
        df[col] = pd.to_numeric(df[col].str.replace(',', '', regex=False).str.strip(),
                                errors='coerce').fillna(0)
    df[tc] = df[tc].replace('', np.nan).ffill().fillna('')
    df = df[df[sc].str.strip() != ''].reset_index(drop=True)
    df = df[df[tc].str.strip() != ''].reset_index(drop=True)
    return df, tc, sc, nc

try:
    df, team_col, si_col, num_cols = load_data()
except Exception as e:
    st.error(f"**Cannot load data:** `{e}`\n\nSet Google Sheet → **Anyone with link → Viewer**")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Retry"): st.cache_data.clear(); st.rerun()
    with c2:
        if st.button("🔒 Logout"): st.session_state.authenticated = False; st.rerun()
    st.stop()

ytd_cols   = [c for c in num_cols if 'ytd' in c.lower()]
month_cols = [c for c in num_cols if 'ytd' not in c.lower()]
all_vc     = num_cols
teams = sorted(df[team_col].dropna().unique().tolist())
sis   = sorted(df[si_col].dropna().unique().tolist())

# ─────────────────────────────────────────────────────────────────────
# TOPBAR + FILTER — unified single row
# ─────────────────────────────────────────────────────────────────────
# Brand block
st.markdown(f"""
<div class="topbar">
  <div class="topbar-brand">
    <div class="topbar-mark">Z</div>
    <div>
      <div class="topbar-title">Strategic Initiatives Dashboard</div>
      <div class="topbar-sub">Zameen.com &nbsp;·&nbsp; ZSM Level Revenue Intelligence</div>
    </div>
  </div>
  <div class="live-badge" style="margin-left:auto;"><div class="live-dot"></div>Live Sync</div>
</div>""", unsafe_allow_html=True)

# Filters + action buttons in one tight row
fc1, fc2, fc3, fc4 = st.columns([3, 3, 2, 1], gap="small")
with fc1:
    sel_teams = st.multiselect("ZSM / Region", options=teams, default=teams,
                               placeholder="All ZSMs", label_visibility="visible")
with fc2:
    sel_si = st.multiselect("Strategic Initiative", options=sis, default=sis,
                            placeholder="All Initiatives", label_visibility="visible")
with fc3:
    sel_months = st.multiselect("Month", options=month_cols, default=month_cols,
                                placeholder="All Months", label_visibility="visible") if month_cols else []
with fc4:
    st.markdown("<div style='padding-top:1.45rem;display:flex;flex-direction:column;gap:4px;'>", unsafe_allow_html=True)
    if st.button("☀ / 🌙", use_container_width=True):
        st.session_state.dark_mode = not DM; st.rerun()
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    if st.button("⏻ Logout", use_container_width=True):
        st.session_state.authenticated = False; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    f"<div style='height:1px;background:{T['border']};margin:0.3rem 0 1rem;'></div>",
    unsafe_allow_html=True)

sel_teams  = sel_teams  or teams
sel_si     = sel_si     or sis
sel_months = sel_months or month_cols

dff    = df[df[team_col].isin(sel_teams) & df[si_col].isin(sel_si)].copy()
use_mc = [m for m in sel_months if m in dff.columns]

# ─────────────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────────────
tot  = float(dff[all_vc].sum().sum()) if all_vc else 0
ytd  = float(dff[ytd_cols].sum().sum()) if ytd_cols else tot
nzsm = int(dff[team_col].nunique())
ts   = dff.groupby(team_col)[all_vc].sum().sum(axis=1) if all_vc else pd.Series(dtype=float)
ss2  = dff.groupby(si_col)[all_vc].sum().sum(axis=1)   if all_vc else pd.Series(dtype=float)
tp   = str(ts.idxmax())  if (not ts.empty  and ts.sum()  > 0) else "N/A"
tsi  = str(ss2.idxmax()) if (not ss2.empty and ss2.sum() > 0) else "N/A"
tpv  = float(ts.max()) if not ts.empty else 0

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi">
    <div class="kpi-stripe"></div>
    <div class="kpi-lbl">Total Revenue</div>
    <div class="kpi-val">{fmt(tot)}</div>
    <div class="kpi-note">{nzsm} ZSMs · {len(sel_si)} initiatives</div>
  </div>
  <div class="kpi">
    <div class="kpi-stripe gold"></div>
    <div class="kpi-lbl">YTD Revenue</div>
    <div class="kpi-val">{fmt(ytd)}</div>
    <div class="kpi-note">Year-to-date cumulative</div>
  </div>
  <div class="kpi">
    <div class="kpi-stripe blue"></div>
    <div class="kpi-lbl">Active ZSMs</div>
    <div class="kpi-val">{nzsm}</div>
    <div class="kpi-note">{len(sel_months)} months in view</div>
  </div>
  <div class="kpi">
    <div class="kpi-stripe gold"></div>
    <div class="kpi-lbl">Top ZSM</div>
    <div class="kpi-val" style="font-size:1.1rem;letter-spacing:-0.3px;">{tp[:22]}</div>
    <div class="kpi-note">{fmt(tpv)} total revenue</div>
  </div>
  <div class="kpi">
    <div class="kpi-stripe"></div>
    <div class="kpi-lbl">Top Initiative</div>
    <div class="kpi-val" style="font-size:1.1rem;letter-spacing:-0.3px;">{tsi[:22]}</div>
    <div class="kpi-note">Highest revenue driver</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊  Overview", "📈  Monthly Trends", "🏆  ZSM Performance",
    "🎯  Initiatives", "🗃  Data"
])

# ══════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════
with tab1:
    ca, cb = st.columns([3, 2], gap="medium")

    with ca:
        st.markdown('<div class="slbl">Revenue by ZSM Region</div>', unsafe_allow_html=True)
        tr2 = dff.groupby(team_col)[all_vc].sum().sum(axis=1).sort_values(ascending=True)
        # Gradient bars: lightest at bottom (lowest), richest at top (highest)
        n = len(tr2)
        bar_colors = [PAL[i % len(PAL)] for i in range(n)]
        fig = go.Figure(go.Bar(
            x=tr2.values,
            y=tr2.index,
            orientation='h',
            marker=dict(
                color=bar_colors,
                line=dict(width=0),
                opacity=0.92,
            ),
            hovertemplate="<b>%{y}</b><br>Revenue: <b>%{x:,.0f}</b><extra></extra>",
        ))
        badge_labels_hbar(fig, tr2.values, tr2.index.tolist())
        fig.update_layout(**base(380, r=140))
        ax(fig)
        leg(fig)
        st.plotly_chart(fig, use_container_width=True)

    with cb:
        st.markdown('<div class="slbl">Revenue Mix by Initiative</div>', unsafe_allow_html=True)
        sr = dff.groupby(si_col)[all_vc].sum().sum(axis=1).sort_values(ascending=False)
        sr = sr[sr > 0]
        if not sr.empty:
            fig2 = go.Figure(go.Pie(
                labels=sr.index,
                values=sr.values,
                hole=0.62,
                marker=dict(
                    colors=PAL[:len(sr)],
                    line=dict(color=T["bg"], width=3)
                ),
                textinfo='percent',
                textfont=dict(color='white', size=13, family="DM Sans"),
                insidetextorientation='radial',
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Revenue: <b>%{value:,.0f}</b><br>"
                    "Share: <b>%{percent}</b><extra></extra>"
                ),
                pull=[0.03] + [0] * (len(sr) - 1),  # slight pull on top segment
            ))
            fig2.update_layout(
                **base(380, r=120),
                annotations=[dict(
                    text=f"<b>{fmt(sr.sum())}</b><br>"
                         f"<span style='font-size:10px'>Total</span>",
                    x=0.38, y=0.5,
                    font=dict(size=16, color=T["text"], family="DM Mono"),
                    showarrow=False
                )]
            )
            leg(fig2, ori="v", y=0.5, x=0.82)
            st.plotly_chart(fig2, use_container_width=True)

    # Stacked bar
    st.markdown('<div class="slbl" style="margin-top:0.6rem;">Stacked Revenue — ZSM × Initiative</div>',
                unsafe_allow_html=True)
    p2 = dff.groupby([team_col, si_col])[all_vc].sum().sum(axis=1).reset_index()
    p2.columns = [team_col, si_col, 'Rev']
    p2 = p2[p2['Rev'] > 0]
    if not p2.empty:
        fig5 = go.Figure()
        sis_in_p2 = p2[si_col].unique()
        for i, si in enumerate(sis_in_p2):
            sub = p2[p2[si_col] == si]
            # Only show labels on segments large enough
            labels = [fmt(v) if v >= (p2['Rev'].max() * 0.05) else '' for v in sub['Rev']]
            fig5.add_trace(go.Bar(
                x=sub[team_col], y=sub['Rev'], name=si,
                marker=dict(color=PAL[i % len(PAL)], line=dict(width=0), opacity=0.92),
                text=labels,
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(color='white', size=11, family="DM Mono"),
                hovertemplate=f"<b>{si}</b><br>%{{x}}: <b>%{{y:,.0f}}</b><extra></extra>",
            ))
        fig5.update_layout(**base(340, r=8, b=60), barmode='stack')
        ax(fig5, -15)
        leg(fig5, ori="h", y=-0.35, x=0)
        st.plotly_chart(fig5, use_container_width=True)

# ══════════════════════════════════════════════════════
# TAB 2 — MONTHLY TRENDS
# ══════════════════════════════════════════════════════
with tab2:
    if not use_mc:
        st.info("No monthly columns in current selection.")
    else:
        mt = dff[use_mc].sum()

        st.markdown('<div class="slbl">Total Monthly Revenue</div>', unsafe_allow_html=True)
        fig3 = go.Figure()
        # Area fill
        fig3.add_trace(go.Scatter(
            x=use_mc, y=mt.values,
            mode='lines+markers',
            name='Total Revenue',
            line=dict(color=GREEN, width=3, shape='spline', smoothing=0.8),
            marker=dict(size=11, color=GREEN,
                        line=dict(color=T["bg"], width=2.5),
                        symbol='circle'),
            fill='tozeroy',
            fillcolor=rgba(GREEN, 0.07),
            hovertemplate="<b>%{x}</b><br>Revenue: <b>%{y:,.0f}</b><extra></extra>",
        ))
        badge_labels_scatter(fig3, use_mc, mt.values)
        for i, si in enumerate(dff[si_col].unique()):
            vals2 = dff[dff[si_col] == si][use_mc].sum()
            if vals2.sum() == 0: continue
            fig3.add_trace(go.Scatter(
                x=use_mc, y=vals2.values,
                mode='lines+markers', name=si,
                line=dict(color=PAL[(i+1) % len(PAL)], width=2, shape='spline'),
                marker=dict(size=6),
                visible='legendonly',
                hovertemplate=f"<b>{si}</b> · %{{x}}: <b>%{{y:,.0f}}</b><extra></extra>",
            ))
        fig3.update_layout(**base(400, r=8, b=60))
        ax(fig3, show_x_grid=True)
        leg(fig3, ori="h", y=-0.25, x=0)
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown('<div class="slbl" style="margin-top:0.6rem;">Month-over-Month by ZSM</div>',
                    unsafe_allow_html=True)
        mom = dff.groupby(team_col)[use_mc].sum()
        fig_m = go.Figure()
        for i, m in enumerate(use_mc):
            fig_m.add_trace(go.Bar(
                name=m, x=mom.index, y=mom[m],
                marker=dict(color=PAL[i % len(PAL)], line=dict(width=0), opacity=0.9),
                hovertemplate=f"<b>{m}</b> · %{{x}}: <b>%{{y:,.0f}}</b><extra></extra>",
            ))
        fig_m.update_layout(**base(430, r=8, b=70), barmode='group')
        ax(fig_m, -20)
        leg(fig_m, ori="h", y=-0.3, x=0)
        # Add badge labels for each month group
        for i, m in enumerate(use_mc):
            badge_labels_vbar(fig_m, mom.index.tolist(), mom[m].tolist(), shift=6)
        st.plotly_chart(fig_m, use_container_width=True)

# ══════════════════════════════════════════════════════
# TAB 3 — ZSM PERFORMANCE
# ══════════════════════════════════════════════════════
with tab3:
    ch, ct = st.columns([3, 2], gap="medium")
    with ch:
        st.markdown('<div class="slbl">ZSM × Month Revenue Heatmap</div>', unsafe_allow_html=True)
        if use_mc:
            ph = dff.groupby(team_col)[use_mc].sum()
            ph = ph[ph.sum(axis=1) > 0]
            if not ph.empty:
                fig4 = go.Figure(go.Heatmap(
                    z=ph.values,
                    x=ph.columns.tolist(),
                    y=[str(t)[:30] for t in ph.index],
                    colorscale=[
                        [0.00, T["bg"]],
                        [0.01, rgba(GREEN, 0.12)],
                        [0.40, rgba(GREEN, 0.55)],
                        [0.75, GREEN],
                        [1.00, "#80FFB8"],
                    ],
                    text=[[fmt(v) for v in row] for row in ph.values],
                    texttemplate="%{text}",
                    textfont=dict(size=13, color="white", family="DM Mono"),
                    hovertemplate=(
                        "<b>%{y}</b> · <b>%{x}</b><br>"
                        "Revenue: <b>%{z:,.0f}</b><extra></extra>"
                    ),
                    showscale=True,
                    colorbar=dict(
                        tickfont=dict(color=T["subtext2"], size=9, family="DM Mono"),
                        bgcolor=T["surface"],
                        bordercolor=T["border"],
                        borderwidth=1,
                        len=0.85,
                        thickness=12,
                    ),
                ))
                fig4.update_layout(**base(480))
                ax(fig4)
                st.plotly_chart(fig4, use_container_width=True)

    with ct:
        st.markdown('<div class="slbl">Revenue Leaderboard</div>', unsafe_allow_html=True)
        lb = (dff.groupby(team_col)[all_vc].sum().sum(axis=1)
                .sort_values(ascending=False).reset_index())
        lb.columns = ['ZSM', 'Revenue']
        lb.insert(0, 'Rank', [f"#{i+1}" for i in range(len(lb))])
        ts_ = lb['Revenue'].sum()
        lb['Share'] = ((lb['Revenue'] / ts_ * 100).round(1).astype(str) + '%') if ts_ > 0 else "—"
        lb['Revenue'] = lb['Revenue'].apply(fmt)
        st.dataframe(lb, use_container_width=True, height=480, hide_index=True)

# ══════════════════════════════════════════════════════
# TAB 4 — INITIATIVES
# ══════════════════════════════════════════════════════
with tab4:
    ci1, ci2 = st.columns(2, gap="medium")

    with ci1:
        st.markdown('<div class="slbl">Initiative Revenue Ranking</div>', unsafe_allow_html=True)
        sir = dff.groupby(si_col)[all_vc].sum().sum(axis=1).sort_values(ascending=True)
        fig_si = go.Figure(go.Bar(
            x=sir.values,
            y=sir.index,
            orientation='h',
            marker=dict(color=PAL[:len(sir)], line=dict(width=0), opacity=0.92),
            hovertemplate="<b>%{y}</b>: <b>%{x:,.0f}</b><extra></extra>",
        ))
        badge_labels_hbar(fig_si, sir.values, sir.index.tolist())
        fig_si.update_layout(**base(400, r=140))
        ax(fig_si)
        leg(fig_si)
        st.plotly_chart(fig_si, use_container_width=True)

    with ci2:
        st.markdown('<div class="slbl">Initiative × ZSM Contribution</div>', unsafe_allow_html=True)
        sz = dff.groupby([si_col, team_col])[all_vc].sum().sum(axis=1).reset_index()
        sz.columns = [si_col, team_col, 'Rev']
        sz = sz[sz['Rev'] > 0]
        fig_sz = go.Figure()
        for i, zsm in enumerate(sz[team_col].unique()):
            sub = sz[sz[team_col] == zsm]
            fig_sz.add_trace(go.Bar(
                x=sub[si_col], y=sub['Rev'], name=str(zsm)[:18],
                marker=dict(color=PAL[i % len(PAL)], line=dict(width=0), opacity=0.9),
                hovertemplate=f"<b>{zsm}</b><br>%{{x}}: <b>%{{y:,.0f}}</b><extra></extra>",
            ))
        fig_sz.update_layout(**base(430, r=8, b=70), barmode='group')
        ax(fig_sz, -20)
        leg(fig_sz, ori="h", y=-0.3, x=0)
        for zsm2 in sz[team_col].unique():
            sub2 = sz[sz[team_col] == zsm2]
            badge_labels_vbar(fig_sz, sub2[si_col].tolist(), sub2['Rev'].tolist(), shift=6)
        st.plotly_chart(fig_sz, use_container_width=True)

    st.markdown('<div class="slbl" style="margin-top:0.5rem;">Initiative Summary</div>',
                unsafe_allow_html=True)
    sum_df = dff.groupby(si_col)[all_vc].sum()
    sum_df['Total'] = sum_df.sum(axis=1)
    sum_df = sum_df.sort_values('Total', ascending=False)
    sum_fmt = sum_df.copy()
    for c in sum_fmt.columns:
        sum_fmt[c] = sum_fmt[c].apply(fmt)
    st.dataframe(sum_fmt, use_container_width=True, height=280)

# ══════════════════════════════════════════════════════
# TAB 5 — DATA
# ══════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="slbl">Full Dataset</div>', unsafe_allow_html=True)
    fd = {c: "{:,.0f}" for c in all_vc if c in dff.columns}
    st.dataframe(dff.style.format(fd), use_container_width=True, height=520)
    st.download_button("⬇  Download CSV", dff.to_csv(index=False).encode(),
                       "zameen_si.csv", "text/csv")

# FOOTER
_fb = T["border"]; _fs = T["subtext"]
st.markdown(f"""
<div style="text-align:center;padding:2.5rem 0 0.8rem;color:{_fs};
    font-size:0.62rem;font-weight:500;letter-spacing:2.5px;
    border-top:1px solid {_fb};margin-top:2rem;text-transform:uppercase;">
  Zameen.com &nbsp;·&nbsp; Strategic Intelligence Portal &nbsp;·&nbsp; Live · Cached 5 min
</div>""", unsafe_allow_html=True)
