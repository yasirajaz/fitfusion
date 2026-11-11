"""Warm Sunset look for FitFusion: one place for colours, custom CSS and card helpers.

Usage (once per page, at the top):
    import style
    style.inject()
    style.sidebar_brand()

Conventions the CSS relies on (needs Streamlit >= 1.39 for widget/container keys):
  * st.container(key="card_...")   -> white rounded card around ordinary widgets
  * st.button(..., key="soft_...") -> quiet tinted pill instead of the coral one
  * Sidebar nav: st.sidebar.radio(..., label_visibility="collapsed")

Every card has two forms: xxx_html(...) returns markup (use it inside grid()),
xxx_card(...) renders it straight away.
"""
import html

import streamlit as st

# ---- palette ---------------------------------------------------------------
ACCENT = "#D9481F"    # coral
HOVER = "#B83A16"     # coral, hover
INK = "#2B1B14"       # dark brown text
MUTED = "#7A5C4D"     # secondary text
CREAM = "#FFF3E7"     # page background, bar tracks, sidebar select
TINT = "#FFEBDD"      # chips, soft buttons
TINT_HOVER = "#FFDFCB"
HERO_SUB = "#FFE9DF"
LINE = "#F1DFCF"      # input borders
HAIR = "#F3E9DF"      # row dividers
GOLD = "#F4B942"      # second series colour
WHITE = "#fff"
SPLIT_COLORS = (ACCENT, GOLD, MUTED)

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Inter:wght@400;500;600;700&display=swap');
html, body, .stApp, button, input, textarea, select {{ font-family: 'Inter', sans-serif; }}
.stApp {{ background: {CREAM}; color: {INK}; }}
h1, h2, h3, .ff-brand {{ font-family: 'Fraunces', serif !important; color: {INK}; font-weight: 600; }}

/* ---- Streamlit chrome we do not want ---- */
[data-testid="stHeader"] {{ background: transparent; pointer-events: none; }}
[data-testid="stHeader"] button {{ pointer-events: auto; }}
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stHeaderActionElements"],
#MainMenu, footer {{ display: none !important; }}

/* ---- page layout ---- */
.block-container, [data-testid="stMainBlockContainer"] {{ padding: 1.1rem 1.6rem 2rem !important; }}
[data-testid="stMain"] [data-testid="stVerticalBlock"] {{ gap: 14px; }}
[data-testid="stHorizontalBlock"] {{ gap: 14px; }}
.stApp h1 {{ font-size: 32px; line-height: 1.2; padding: 0; margin: 0 0 -4px; letter-spacing: -0.01em; }}
.stApp h2 {{ font-size: 24px; padding: 0; }}
.stApp h3 {{ font-size: 20px; padding: 0; margin: 0; }}
[data-testid="stCaptionContainer"] {{ color: {MUTED}; }}

/* ---- floating sidebar ---- */
[data-testid="stSidebar"] {{ background: transparent; border: 0; }}
[data-testid="stSidebar"] > div:first-child {{
    background: {WHITE}; border-radius: 28px; margin: 18px 0 18px 18px;
    width: calc(100% - 26px); height: calc(100vh - 36px); }}
[data-testid="stSidebarHeader"] {{ height: 0; min-height: 0; padding: 0; margin: 0; }}
[data-testid="stSidebarUserContent"] {{ padding: 1.25rem 14px 1rem; }}
.ff-brand {{ font-size: 24px; line-height: 1.1; }}
.ff-tag {{ color: {MUTED}; font-size: 13px; margin: 4px 0 18px; }}

/* user picker: cream pill, no border */
[data-testid="stSidebar"] [data-baseweb="select"] > div {{
    background: {CREAM} !important; border: 0 !important; border-radius: 16px !important; min-height: 42px; }}
[data-testid="stSidebar"] [data-baseweb="select"] div {{ font-size: 17px; }}

/* nav: radio group becomes a list of rounded rows, selected row is coral */
[data-testid="stSidebar"] [role="radiogroup"] {{ gap: 6px; align-items: stretch !important; }}
[data-testid="stSidebar"] [role="radiogroup"] label {{
    width: 100% !important; box-sizing: border-box; margin: 0; padding: 11px 14px;
    border-radius: 12px; cursor: pointer; }}
[data-testid="stSidebar"] [role="radiogroup"] label > *:not(input):not([data-testid="stMarkdownContainer"]):not(:has([data-testid="stMarkdownContainer"])) {{
    display: none !important; }}
[data-testid="stSidebar"] [role="radiogroup"] label p {{ font-size: 15px; color: {INK}; }}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{ background: {CREAM}; }}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{ background: {ACCENT}; }}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{ color: {WHITE}; font-weight: 600; }}
/* nav: same look for st.navigation() links */
[data-testid="stSidebarNavLink"] {{ border-radius: 12px; padding: 11px 14px; }}
[data-testid="stSidebarNavLink"][aria-current="page"] {{ background: {ACCENT}; }}
[data-testid="stSidebarNavLink"][aria-current="page"] span {{ color: {WHITE}; font-weight: 600; }}

/* ---- inputs ---- */
[data-testid="stWidgetLabel"] p {{ color: {MUTED}; font-size: 13px; font-weight: 400; }}
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {{
    background: {WHITE} !important; border: 1px solid {LINE} !important; border-radius: 14px !important;
    min-height: 42px; }}
[data-baseweb="base-input"], [data-baseweb="input"] input {{ background: transparent !important; border-radius: 14px; }}
[data-baseweb="input"] input, [data-baseweb="select"] div {{ color: {INK}; font-size: 14px; }}
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within {{ border-color: {ACCENT} !important; }}
[data-testid="stNumberInput"] button {{ display: none; }}
[data-baseweb="popover"] > div {{ border-radius: 16px; }}

/* ---- white cards ---- */
[data-testid="stForm"] {{ background: {WHITE}; border: 0 !important; border-radius: 24px; padding: 20px 20px 22px; }}
[data-testid="stExpander"] {{ background: {WHITE}; border: 0 !important; border-radius: 24px; }}
[data-testid="stExpander"] details {{ border: 0; border-radius: 24px; }}
[data-testid="stExpander"] summary {{ padding: 14px 20px; }}
[data-testid="stExpander"] summary p {{ font-size: 15px; font-weight: 600; }}
[data-testid="stMetric"] {{ background: {WHITE}; border-radius: 24px; padding: 16px 20px; }}
[data-testid="stMetricLabel"] p {{ color: {MUTED}; font-size: 13px; }}
[data-testid="stMetricValue"] {{ color: {INK}; font-size: 36px; font-weight: 700; line-height: 1.2; }}
[data-testid="stMetricDelta"] {{ color: {MUTED} !important; font-size: 13px; }}
[data-testid="stMetricDelta"] svg {{ display: none; }}
[data-testid="stAlert"] {{ border-radius: 18px; }}
/* st.container(key="card_...") = white card around widgets */
[class*="st-key-card"] {{ background: {WHITE}; border-radius: 24px; padding: 18px 20px; }}
[class*="st-key-card"] .stButton button {{ width: 100%; }}
/* centred "+ Add exercise" tile */
.st-key-tile_add {{ background: {WHITE}; border-radius: 24px; min-height: 122px;
    align-items: center; justify-content: center; }}
/* right-aligned page action */
.st-key-gen_plan {{ display: flex; justify-content: flex-end; }}

/* ---- buttons ---- */
.stButton button, .stFormSubmitButton button {{
    border-radius: 999px; border: 0; background: {ACCENT}; color: {WHITE};
    font-weight: 600; font-size: 16px; min-height: 44px; padding: 0 1.6rem; }}
.stButton button p, .stFormSubmitButton button p {{ color: {WHITE}; font-size: 16px; font-weight: 600; }}
.stButton button:hover, .stFormSubmitButton button:hover {{ background: {HOVER}; color: {WHITE}; }}
.stButton button:focus-visible, .stFormSubmitButton button:focus-visible {{ outline: 3px solid {INK}; outline-offset: 2px; }}
[class*="st-key-soft"] button {{ background: {TINT}; color: {ACCENT}; }}
[class*="st-key-soft"] button p {{ color: {ACCENT}; }}
[class*="st-key-soft"] button:hover {{ background: {TINT_HOVER}; color: {ACCENT}; }}

button[role="tab"][aria-selected="true"] {{ color: {ACCENT}; }}
[data-baseweb="tab-highlight"] {{ background-color: {ACCENT}; }}
.stProgress > div > div {{ background: {CREAM}; height: 10px; border-radius: 999px; }}
.stProgress > div > div > div > div {{ background-color: {ACCENT}; border-radius: 999px; }}

/* ---- hero card ---- */
.ff-hero {{ background: {ACCENT}; color: {WHITE}; border-radius: 28px; padding: 26px 30px; }}
.stApp .ff-hero h1 {{ color: {WHITE} !important; margin: 0; font-size: 38px; padding: 0; letter-spacing: 0; }}
.ff-hero .sub {{ color: {HERO_SUB}; font-size: 13px; margin-top: 6px; }}
.ff-hero .pill {{ display: inline-block; margin-top: 14px; background: {WHITE}; color: {ACCENT};
    padding: 10px 18px; border-radius: 999px; font-weight: 700; font-size: 15px; }}

/* ---- custom cards (see helpers below) ---- */
[data-testid="stMarkdownContainer"]:has(.ff-card, .ff-grid, .ff-hero) {{ margin-bottom: 0 !important; }}
.ff-grid {{ display: grid; grid-template-columns: repeat(var(--cols, 2), minmax(0, 1fr)); gap: 14px; }}
@media (max-width: 700px) {{ .ff-grid {{ grid-template-columns: 1fr; }} }}
.ff-card {{ background: {WHITE}; border-radius: 24px; padding: 18px 20px; color: {INK}; }}
.ff-label {{ color: {MUTED}; font-size: 13px; }}
.ff-cap {{ color: {MUTED}; font-size: 13px; margin-top: 2px; }}
.ff-title {{ font-family: 'Fraunces', serif; font-size: 21px; font-weight: 600; line-height: 1.2; }}
.ff-chiprow {{ margin-top: 6px; }}
.ff-chip {{ display: inline-block; background: {TINT}; color: {ACCENT}; font-size: 12px; font-weight: 600;
    padding: 3px 10px; border-radius: 999px; }}
.ff-rows {{ margin-top: 8px; }}
.ff-row {{ display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; font-size: 14px; }}
.ff-row + .ff-row {{ border-top: 1px solid {HAIR}; }}
.ff-row .r {{ color: {MUTED}; white-space: nowrap; }}
.ff-note {{ color: {MUTED}; font-size: 13px; margin-top: 10px; }}
.ff-num {{ font-size: 36px; font-weight: 700; line-height: 1.2; margin-top: 2px; }}
.ff-big {{ font-family: 'Fraunces', serif; font-size: 42px; font-weight: 600; line-height: 1.1; margin-top: 2px; }}
.ff-big.sans {{ font-family: 'Inter', sans-serif; font-weight: 700; }}
.ff-unit {{ font-family: 'Inter', sans-serif; color: {MUTED}; font-size: 15px; font-weight: 400; }}
.ff-bar {{ height: 10px; background: {CREAM}; border-radius: 999px; overflow: hidden; margin-top: 8px; }}
.ff-bar > span {{ display: block; height: 100%; background: {ACCENT}; border-radius: 999px; }}
.ff-macro {{ display: grid; grid-template-columns: 70px 1fr auto; align-items: center; gap: 14px;
    font-size: 14px; margin-top: 14px; }}
.ff-macro .ff-bar {{ margin: 0; }}
.ff-macro b {{ text-align: right; font-weight: 700; white-space: nowrap; }}
.ff-bars {{ position: relative; display: flex; align-items: flex-end; gap: 8px; height: 112px; margin-top: 10px; }}
.ff-bars > span {{ flex: 1; background: {ACCENT}; border-radius: 10px 10px 0 0; }}
.ff-bars.few > span {{ max-width: 64px; }}
.ff-target {{ position: absolute; left: 0; right: 0; border-top: 2px dashed {INK}; opacity: .55; }}
.ff-line {{ display: block; width: 100%; height: 110px; margin-top: 12px; }}
.ff-line polyline {{ fill: none; stroke: {ACCENT}; stroke-width: 3; stroke-linecap: round;
    stroke-linejoin: round; vector-effect: non-scaling-stroke; }}
.ff-split {{ display: flex; height: 14px; border-radius: 999px; overflow: hidden; background: {CREAM}; margin-top: 12px; }}
.ff-split > span {{ display: block; height: 100%; }}
.ff-legend {{ display: flex; flex-wrap: wrap; gap: 6px 16px; margin-top: 12px; font-size: 13px; }}
.ff-legend i {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }}
"""


# ---- internals -------------------------------------------------------------
def _e(value):
    """HTML-escape any user-supplied value."""
    return html.escape(str(value))


def _frac(value):
    """Clamp to 0..1; bad input becomes 0."""
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _chip(text):
    return f'<span class="ff-chip">{_e(text)}</span>'


def _bar(fraction):
    return f'<div class="ff-bar"><span style="width:{_frac(fraction) * 100:.1f}%"></span></div>'


def _render(markup):
    # One line, no blank lines or indentation: Markdown would turn those into code blocks.
    st.markdown(markup, unsafe_allow_html=True)


def _renderer(builder):
    def card(*args, **kwargs):
        _render(builder(*args, **kwargs))
    card.__doc__ = builder.__doc__
    return card


# ---- page chrome -----------------------------------------------------------
def inject():
    """Inject the Warm Sunset CSS. Call once per page."""
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def sidebar_brand():
    """Brand and tagline at the top of the sidebar."""
    st.sidebar.markdown(
        '<div class="ff-brand">FitFusion</div>'
        '<div class="ff-tag">Analyze. Personalize. Transform.</div>',
        unsafe_allow_html=True,
    )


def hero(name, subtitle, pill):
    """Coral hero card. All user-supplied text is HTML-escaped."""
    st.markdown(
        f'<div class="ff-hero"><h1>Hello, {html.escape(name)}</h1>'
        f'<div class="sub">{html.escape(subtitle)}</div>'
        f'<div class="pill">{html.escape(pill)}</div></div>',
        unsafe_allow_html=True,
    )


def grid(*cards, cols=2):
    """Lay out xxx_html() cards in an equal-height grid (stacks to one column on phones)."""
    _render(f'<div class="ff-grid" style="--cols:{int(cols)}">{"".join(cards)}</div>')


# ---- cards -----------------------------------------------------------------
def metric_html(label, value, caption=""):
    """Small stat: label, bold number, muted caption (BMI 24.2 / Normal)."""
    cap = f'<div class="ff-cap">{_e(caption)}</div>' if caption else ""
    return (f'<div class="ff-card"><div class="ff-label">{_e(label)}</div>'
            f'<div class="ff-num">{_e(value)}</div>{cap}</div>')


def rows_html(title, rows=(), chip=None, note=None):
    """White card with a serif title and label/value rows.

    Food Log "Today":  rows_html("Today", [("Oats · 60 g", "233 kcal"), ...])
    Workout day:       rows_html("Monday", [("Lat Pulldown", "3 × 10-12"), ...], chip="Back + Biceps")
    Rest day:          rows_html("Sunday", chip="Rest", note="Rest day: stretch or take a short walk.")
    """
    parts = ['<div class="ff-card">', f'<div class="ff-title">{_e(title)}</div>']
    if chip:
        parts.append(f'<div class="ff-chiprow">{_chip(chip)}</div>')
    rows = list(rows)
    if rows:
        parts.append('<div class="ff-rows">')
        parts += [f'<div class="ff-row"><span>{_e(l)}</span><span class="r">{_e(r)}</span></div>' for l, r in rows]
        parts.append("</div>")
    if note:
        parts.append(f'<div class="ff-note">{_e(note)}</div>')
    parts.append("</div>")
    return "".join(parts)


def stat_html(label, value, unit="", progress=None, chip=None, note=None, serif=True):
    """Big-number card.

    Calories:  stat_html("Calories", 976, "/ 2085 kcal", progress=976 / 2085)
    Adaptive:  stat_html("Adaptive calorie check", "-0.35", "kg/week", chip="On track",
                         note="Keep your current target of 2085 kcal.")
    progress is a 0-1 fraction. serif=False gives the bold sans number.
    """
    big_cls = "ff-big" if serif else "ff-big sans"
    parts = [
        '<div class="ff-card">',
        f'<div class="ff-label">{_e(label)}</div>',
        f'<div class="{big_cls}">{_e(value)} <span class="ff-unit">{_e(unit)}</span></div>',
    ]
    if progress is not None:
        parts.append(_bar(progress))
    if chip:
        parts.append(f'<div class="ff-chiprow">{_chip(chip)}</div>')
    if note:
        parts.append(f'<div class="ff-note">{_e(note)}</div>')
    parts.append("</div>")
    return "".join(parts)


def macro_html(label, value, unit, macros):
    """Card with an optional big number (pass value=None to omit it) and labelled bars.

    macro_html("Daily calories", 2085, "kcal",
               [("Protein", 0.27, "140 g"), ("Carbs", 0.48, "251 g"), ("Fat", 0.25, "58 g")])
    Each macro is (name, 0-1 fraction of the bar, value text).
    """
    parts = ['<div class="ff-card">', f'<div class="ff-label">{_e(label)}</div>']
    if value is not None:
        parts.append(f'<div class="ff-big sans">{_e(value)} <span class="ff-unit">{_e(unit)}</span></div>')
    for name, fraction, text in macros:
        parts.append(f'<div class="ff-macro"><span>{_e(name)}</span>{_bar(fraction)}<b>{_e(text)}</b></div>')
    parts.append("</div>")
    return "".join(parts)


def split_html(label, items):
    """One stacked bar with a legend. items = [(name, text, weight), ...] (3 colours)."""
    items = [(n, t, max(0.0, float(w))) for n, t, w in items]
    total = sum(w for _, _, w in items) or 1.0
    segs, legend = [], []
    for (name, text, weight), color in zip(items, SPLIT_COLORS):
        pct = weight / total * 100
        segs.append(f'<span style="width:{pct:.1f}%;background:{color}"></span>')
        legend.append(f'<span><i style="background:{color}"></i>{_e(name)} {_e(text)} · {pct:.0f}%</span>')
    return (f'<div class="ff-card"><div class="ff-label">{_e(label)}</div>'
            f'<div class="ff-split">{"".join(segs)}</div>'
            f'<div class="ff-legend">{"".join(legend)}</div></div>')


def line_html(label, values):
    """Axis-free coral line chart in a white card (e.g. body weight)."""
    try:
        vals = [float(v) for v in values]
    except (TypeError, ValueError):
        vals = []
    parts = ['<div class="ff-card">', f'<div class="ff-label">{_e(label)}</div>']
    if len(vals) >= 2:
        lo, hi = min(vals), max(vals)
        span = (hi - lo) or 1.0
        step = 300 / (len(vals) - 1)
        pts = " ".join(f"{i * step:.1f},{8 + (1 - (v - lo) / span) * 84:.1f}" for i, v in enumerate(vals))
        parts.append(
            '<svg class="ff-line" viewBox="0 0 300 100" preserveAspectRatio="none">'
            f'<polyline points="{pts}"/></svg>'
        )
    else:
        parts.append('<div class="ff-note">Not enough data yet.</div>')
    parts.append("</div>")
    return "".join(parts)


def bar_html(label, values, target=None, labels=None):
    """Rounded coral bars, optional dashed target line, optional hover text per bar."""
    try:
        vals = [max(0.0, float(v)) for v in values]
        tgt = None if target is None else float(target)
    except (TypeError, ValueError):
        vals, tgt = [], None
    parts = ['<div class="ff-card">', f'<div class="ff-label">{_e(label)}</div>']
    if vals:
        tips = list(labels or [])
        top = max(vals + ([tgt] if tgt else [])) or 1.0
        cls = "ff-bars" + (" few" if len(vals) < 7 else "")
        parts.append(f'<div class="{cls}">')
        for i, v in enumerate(vals):
            tip = f' title="{_e(tips[i])}"' if i < len(tips) else ""
            parts.append(f'<span{tip} style="height:{v / top * 100:.1f}%"></span>')
        if tgt:
            parts.append(f'<div class="ff-target" style="bottom:{tgt / top * 100:.1f}%"></div>')
        parts.append("</div>")
    else:
        parts.append('<div class="ff-note">Nothing to show yet.</div>')
    parts.append("</div>")
    return "".join(parts)


metric_card = _renderer(metric_html)
rows_card = _renderer(rows_html)
stat_card = _renderer(stat_html)
macro_card = _renderer(macro_html)
split_card = _renderer(split_html)
line_card = _renderer(line_html)
bar_card = _renderer(bar_html)
