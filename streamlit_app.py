"""HumanMaximizer AI Lead Generation — Streamlit Demo"""

import streamlit as st
import httpx
import time
import threading
import plotly.graph_objects as go

API_BASE = "http://localhost:8000"
API_TIMEOUT = 600

st.set_page_config(
    page_title="HumanMaximizer · AI Lead Gen",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "bg":       "#0a0e1a",
    "surface":  "#141826",
    "card":     "#1a2035",
    "border":   "#1e2d4a",
    "cyan":     "#00d4ff",
    "cyan_d":   "#0095b3",
    "green":    "#00e676",
    "yellow":   "#ffd740",
    "red":      "#ff5252",
    "purple":   "#a78bfa",
    "text":     "#e8eaf6",
    "dim":      "#8fa3c4",
}

st.markdown(f"""
<style>
[data-testid="stApp"] {{
    background-color:{C["bg"]};
    color:{C["text"]};
    font-family:'Inter','Segoe UI',sans-serif;
}}
[data-testid="stSidebar"] {{
    background:linear-gradient(180deg,#0d1220 0%,{C["bg"]} 100%);
    border-right:1px solid {C["border"]};
}}
h1,h2,h3 {{ color:{C["text"]}; font-weight:700; }}
[data-testid="stMetric"] {{
    background:{C["card"]};
    border:1px solid {C["border"]};
    border-radius:12px;
    padding:16px;
}}
[data-testid="stMetricLabel"] {{ color:{C["dim"]} !important; font-size:12px !important; }}
[data-testid="stMetricValue"] {{ color:{C["cyan"]} !important; font-size:28px !important; }}
.stButton>button {{
    background:linear-gradient(135deg,{C["cyan"]},{C["cyan_d"]});
    color:#000;font-weight:700;border:none;border-radius:8px;
    padding:10px 20px;font-size:14px;width:100%;transition:opacity .2s;
}}
.stButton>button:hover {{ opacity:.85; }}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input {{
    background:{C["card"]};border:1px solid {C["border"]};
    color:{C["text"]};border-radius:8px;
}}
[data-testid="stTabs"] [role="tab"] {{ color:{C["dim"]};font-weight:600; }}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color:{C["cyan"]};border-bottom:2px solid {C["cyan"]};
}}
details {{
    background:{C["card"]} !important;
    border:1px solid {C["border"]} !important;
    border-radius:8px !important;
}}
#MainMenu,footer {{ display:none; }}
[data-testid="stToolbar"] {{ display:none; }}

/* ── Custom components ── */
.hero {{
    background:linear-gradient(135deg,#0d1a2d 0%,#0a1628 50%,#0d2040 100%);
    border:1px solid {C["border"]};border-left:4px solid {C["cyan"]};
    border-radius:16px;padding:32px 40px;margin-bottom:28px;position:relative;overflow:hidden;
}}
.hero::before {{
    content:'';position:absolute;top:-50%;right:-5%;width:360px;height:360px;
    background:radial-gradient(circle,rgba(0,212,255,.07) 0%,transparent 70%);border-radius:50%;
}}
.hero-badge {{
    display:inline-block;background:rgba(0,212,255,.12);border:1px solid {C["cyan"]};
    color:{C["cyan"]};font-size:11px;font-weight:700;padding:3px 12px;
    border-radius:20px;margin-bottom:10px;text-transform:uppercase;letter-spacing:1px;
}}
.hero-title {{ font-size:34px;font-weight:800;color:{C["text"]};margin:0;line-height:1.2; }}
.hero-sub {{ font-size:14px;color:{C["dim"]};margin-top:6px; }}

.uc-grid {{
    display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:20px 0;
}}
.uc-card {{
    background:{C["card"]};border:1px solid {C["border"]};border-radius:12px;
    padding:18px;position:relative;overflow:hidden;
}}
.uc-card::after {{
    content:'';position:absolute;bottom:0;left:0;right:0;height:3px;
    background:linear-gradient(90deg,{C["cyan"]},{C["cyan_d"]});
}}
.uc-icon {{ font-size:26px;margin-bottom:6px; }}
.uc-title {{ font-size:14px;font-weight:700;color:{C["text"]};margin-bottom:5px; }}
.uc-desc {{ font-size:12px;color:{C["dim"]};line-height:1.5; }}

.pipe-step {{
    display:flex;align-items:flex-start;gap:14px;padding:14px;
    background:{C["card"]};border:1px solid {C["border"]};border-radius:10px;margin-bottom:8px;
}}
.step-num {{
    width:34px;height:34px;border-radius:50%;display:flex;align-items:center;
    justify-content:center;font-weight:800;color:#000;font-size:13px;flex-shrink:0;
}}
.step-title {{ font-weight:700;color:{C["text"]};font-size:13px; }}
.step-desc {{ font-size:12px;color:{C["dim"]};margin-top:2px; }}

.lead-card {{
    background:{C["card"]};border:1px solid {C["border"]};border-radius:12px;
    padding:18px 22px;margin-bottom:14px;position:relative;overflow:hidden;
}}
.lead-card.q {{ border-left:4px solid {C["green"]}; }}
.lead-card.dq {{ border-left:4px solid {C["red"]};opacity:.72; }}
.lead-rank {{
    position:absolute;top:14px;right:14px;background:rgba(0,212,255,.1);
    border:1px solid {C["cyan"]};color:{C["cyan"]};font-weight:800;font-size:12px;
    padding:3px 10px;border-radius:20px;
}}
.lead-co {{ font-size:19px;font-weight:800;color:{C["text"]};margin-bottom:3px; }}
.lead-meta {{ font-size:12px;color:{C["dim"]};margin-bottom:10px; }}
.sbadge {{
    display:inline-flex;align-items:center;gap:5px;padding:5px 12px;
    border-radius:20px;font-weight:700;font-size:13px;margin-right:6px;
}}
.sh {{ background:rgba(0,230,118,.13);color:{C["green"]};border:1px solid {C["green"]}; }}
.sm {{ background:rgba(255,215,64,.13);color:{C["yellow"]};border:1px solid {C["yellow"]}; }}
.sl {{ background:rgba(255,82,82,.13);color:{C["red"]};border:1px solid {C["red"]}; }}
.tag {{
    display:inline-block;background:{C["surface"]};border:1px solid {C["border"]};
    color:{C["dim"]};font-size:11px;padding:2px 7px;border-radius:4px;margin:2px;
}}
.stat-row {{ display:flex;gap:10px;margin:10px 0;flex-wrap:wrap; }}
.stat-chip {{
    background:{C["card"]};border:1px solid {C["border"]};border-radius:20px;
    padding:5px 12px;font-size:12px;color:{C["dim"]};
}}
.stat-chip span {{ color:{C["cyan"]};font-weight:700; }}

.sec {{ font-size:17px;font-weight:700;color:{C["text"]};
    border-left:3px solid {C["cyan"]};padding-left:10px;margin:22px 0 14px 0; }}

.trace {{
    background:{C["surface"]};border:1px solid {C["border"]};
    border-radius:10px;padding:14px;margin:6px 0;position:relative;
}}
.trace::before {{ content:'';position:absolute;left:0;top:0;bottom:0;width:4px;border-radius:10px 0 0 10px; }}
.trace.r::before {{ background:#7c3aed; }}
.trace.q2::before {{ background:{C["yellow"]}; }}
.trace.s::before {{ background:{C["green"]}; }}
.tlabel {{ font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:5px; }}
.trace.r .tlabel {{ color:{C["purple"]}; }}
.trace.q2 .tlabel {{ color:{C["yellow"]}; }}
.trace.s .tlabel {{ color:{C["green"]}; }}
.tcontent {{ font-size:13px;color:{C["text"]};line-height:1.6; }}

.dm-card {{
    background:{C["surface"]};border:1px solid {C["border"]};
    border-radius:8px;padding:12px;margin-bottom:8px;
}}
.dm-name {{ font-weight:700;color:{C["text"]};font-size:14px; }}
.dm-title {{ color:{C["cyan"]};font-size:12px; }}
.dm-contact {{ font-size:11px;color:{C["dim"]};margin-top:3px; }}

.email-wrap {{
    background:{C["surface"]};border:1px solid {C["border"]};border-radius:10px;overflow:hidden;
}}
.email-hdr {{
    background:{C["card"]};padding:10px 14px;border-bottom:1px solid {C["border"]};
    font-size:12px;color:{C["dim"]};
}}
.email-subj {{ font-weight:700;color:{C["text"]};font-size:14px;margin-bottom:2px; }}
.email-body {{ padding:14px;font-size:13px;color:{C["text"]};line-height:1.7;white-space:pre-wrap; }}

.score-row {{
    display:flex;align-items:center;gap:10px;padding:7px 0;
    border-bottom:1px solid {C["border"]};
}}
.sr-label {{ width:170px;font-size:12px;color:{C["dim"]}; }}
.sr-bar {{ flex:1;background:{C["surface"]};border-radius:4px;height:7px;overflow:hidden; }}
.sr-fill {{ height:100%;border-radius:4px;background:linear-gradient(90deg,{C["cyan"]},{C["green"]}); }}
.sr-val {{ width:36px;text-align:right;font-size:12px;font-weight:700;color:{C["text"]}; }}

.rag-chunk {{
    background:{C["surface"]};border:1px solid {C["border"]};border-left:3px solid #7c3aed;
    border-radius:0 8px 8px 0;padding:10px;margin:6px 0;
    font-size:12px;color:{C["dim"]};font-family:'Courier New',monospace;line-height:1.5;
}}

.ok {{ background:rgba(0,230,118,.1);border:1px solid {C["green"]};border-radius:8px;
    padding:10px 14px;color:{C["green"]};font-size:13px;margin:6px 0; }}
.warn {{ background:rgba(255,215,64,.1);border:1px solid {C["yellow"]};border-radius:8px;
    padding:10px 14px;color:{C["yellow"]};font-size:13px;margin:6px 0; }}
.err {{ background:rgba(255,82,82,.1);border:1px solid {C["red"]};border-radius:8px;
    padding:10px 14px;color:{C["red"]};font-size:13px;margin:6px 0; }}

.cot-step {{ padding:4px 0;font-size:13px;color:{C["text"]}; }}
.cot-done {{ padding:4px 0;font-size:13px;color:{C["green"]};font-weight:600; }}
</style>
""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────

def api_get(path: str, params: dict = None):
    try:
        r = httpx.get(f"{API_BASE}{path}", params=params, timeout=API_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.markdown(f'<div class="err">API error: {e}</div>', unsafe_allow_html=True)
        return None


def api_post(path: str, body: dict = None):
    try:
        r = httpx.post(f"{API_BASE}{path}", json=body or {}, timeout=API_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.markdown(f'<div class="err">API error: {e}</div>', unsafe_allow_html=True)
        return None


def health_check():
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=4)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


# ── Rendering helpers ─────────────────────────────────────────────────────────

def score_cls(s: int) -> str:
    return "sh" if s >= 70 else ("sm" if s >= 45 else "sl")

def score_dot(s: int) -> str:
    return "🟢" if s >= 70 else ("🟡" if s >= 45 else "🔴")

def growth_html(sig: str) -> str:
    MAP = {
        "hiring_surge":   (C["green"],  "↑ Hiring Surge"),
        "recent_funding": (C["cyan"],   "$ Recently Funded"),
        "expansion":      (C["yellow"], "→ Expanding"),
        "stable":         (C["dim"],    "• Stable"),
        "contracting":    (C["red"],    "↓ Contracting"),
        "unknown":        (C["dim"],    "? Unknown"),
    }
    color, label = MAP.get(sig, (C["dim"], sig.replace("_"," ").title()))
    return f'<span style="color:{color};font-weight:700;font-size:12px;">{label}</span>'

def breakdown_html(bd: dict) -> str:
    dims = [
        ("Company Size Fit",       "company_size_fit"),
        ("Industry Relevance",     "industry_relevance"),
        ("Tech Stack Gap",         "tech_stack_gap"),
        ("DM Reachability",        "decision_maker_reachability"),
        ("Growth Signal",          "growth_signal"),
    ]
    rows = ""
    for label, key in dims:
        v = bd.get(key, 0)
        pct = (v / 20) * 100
        rows += (
            f'<div class="score-row">'
            f'<div class="sr-label">{label}</div>'
            f'<div class="sr-bar"><div class="sr-fill" style="width:{pct}%"></div></div>'
            f'<div class="sr-val">{v}/20</div>'
            f'</div>'
        )
    return rows

def parse_summary_sections(raw_summary: str) -> dict:
    """Split Mistral's 3-paragraph summary into labelled sections."""
    import re
    keys = [
        ("overview",    r"COMPANY OVERVIEW:\s*(.*?)(?=HR PAIN POINTS:|HRMS FIT SIGNAL:|$)"),
        ("pain_points", r"HR PAIN POINTS:\s*(.*?)(?=COMPANY OVERVIEW:|HRMS FIT SIGNAL:|$)"),
        ("fit_signal",  r"HRMS FIT SIGNAL:\s*(.*?)(?=COMPANY OVERVIEW:|HR PAIN POINTS:|$)"),
    ]
    out = {}
    for k, pat in keys:
        m = re.search(pat, raw_summary, re.IGNORECASE | re.DOTALL)
        out[k] = m.group(1).strip() if m else ""
    if not any(out.values()):
        out["overview"] = raw_summary.strip()
    return out


def lead_card_html(lead: dict, rank: int = None) -> str:
    qualified   = lead.get("status") == "qualified"
    cls         = "q" if qualified else "dq"
    company     = lead.get("company_name", "Unknown")
    domain      = lead.get("domain", "")
    industry    = lead.get("industry", "")
    location    = lead.get("hq_location", "")
    employees   = lead.get("employee_count")
    score       = lead.get("qualification_score", 0)
    growth      = lead.get("growth_signal", "unknown")
    tech        = lead.get("tech_stack", [])[:4]
    dms         = len(lead.get("decision_makers", []))

    rank_html = f'<div class="lead-rank">#{rank}</div>' if rank else ""
    tags      = "".join(f'<span class="tag">{t}</span>' for t in tech)
    emp_str   = f"{employees:,}" if employees else "N/A"
    st_color  = C["green"] if qualified else C["red"]

    raw_summary  = lead.get("raw_summary", "")
    sections     = parse_summary_sections(raw_summary)
    overview_txt = sections.get("overview") or lead.get("description", "")
    desc_html = (
        f'<div style="font-size:12px;color:{C["dim"]};margin:4px 0 8px 0;line-height:1.55;">'
        f'{overview_txt}'
        f'</div>'
    ) if overview_txt else ""

    return (
        f'<div class="lead-card {cls}">'
        f'{rank_html}'
        f'<div class="lead-co">{company}</div>'
        f'<div class="lead-meta">{domain} · {industry} · {location}</div>'
        f'{desc_html}'
        f'<div style="margin:10px 0;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
        f'<span class="sbadge {score_cls(score)}">{score_dot(score)} Score: {score}/100</span>'
        f'{growth_html(growth)}'
        f'</div>'
        f'<div class="stat-row">'
        f'<div class="stat-chip">Employees: <span>{emp_str}</span></div>'
        f'<div class="stat-chip">Decision Makers: <span>{dms}</span></div>'
        f'<div class="stat-chip">Status: <span style="color:{st_color}">{lead.get("status","").title()}</span></div>'
        f'</div>'
        f'<div style="margin-top:6px">{tags}</div>'
        f'</div>'
    )

def radar_chart(bd: dict):
    cats = ["Company Size", "Industry", "Tech Gap", "DM Access", "Growth"]
    vals = [
        bd.get("company_size_fit", 0),
        bd.get("industry_relevance", 0),
        bd.get("tech_stack_gap", 0),
        bd.get("decision_maker_reachability", 0),
        bd.get("growth_signal", 0),
    ]
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=cats + [cats[0]],
        fill="toself",
        fillcolor="rgba(0,212,255,.14)",
        line=dict(color="#00d4ff", width=2),
        marker=dict(color="#00d4ff", size=6),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="#141826",
            radialaxis=dict(visible=True, range=[0,20],
                            gridcolor="#1e2d4a", linecolor="#1e2d4a",
                            tickfont=dict(color="#8fa3c4", size=9)),
            angularaxis=dict(gridcolor="#1e2d4a", linecolor="#1e2d4a",
                             tickfont=dict(color="#e8eaf6", size=11)),
        ),
        paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
        margin=dict(t=20,b=20,l=40,r=40), height=280, showlegend=False,
    )
    return fig


# ── Shared lead detail component ──────────────────────────────────────────────

def render_lead_detail(lead: dict, chart_key: str = ""):
    t1, t2, t3, t4 = st.tabs(["📊 Score Breakdown", "👤 Decision Makers", "✉️ Outreach Drafts", "🏢 Company Intelligence"])

    with t1:
        c1, c2 = st.columns(2)
        bd = lead.get("score_breakdown", {})
        with c1:
            st.markdown((
                f'<div style="font-size:12px;color:{C["dim"]};margin-bottom:6px">5-Dimensional HRMS Fit Score</div>'
                f'{breakdown_html(bd)}'
                f'<div style="margin-top:14px;padding:12px;background:{C["surface"]};border-radius:8px;border:1px solid {C["border"]};">'
                f'<div style="font-size:11px;color:{C["dim"]};margin-bottom:4px">QUALIFICATION REASONING</div>'
                f'<div style="font-size:13px;color:{C["text"]};line-height:1.6">{lead.get("qualification_reasoning","N/A")}</div>'
                f'<div style="margin-top:8px;font-size:12px;color:{C["dim"]}">Confidence: '
                f'<strong style="color:{C["cyan"]}">{lead.get("qualification_confidence", 0):.1%}</strong></div>'
                f'</div>'
            ), unsafe_allow_html=True)
        with c2:
            if bd:
                st.plotly_chart(radar_chart(bd), use_container_width=True, key=f"radar_{chart_key}")

    with t2:
        dms = lead.get("decision_makers", [])
        if not dms:
            st.markdown('<div class="warn">No decision makers identified.</div>', unsafe_allow_html=True)
        for dm in dms:
            conf = dm.get("confidence", 0)
            st.markdown((
                f'<div class="dm-card">'
                f'<div class="dm-name">{dm.get("name","Unknown")}</div>'
                f'<div class="dm-title">{dm.get("title","N/A")}</div>'
                f'<div class="dm-contact">📧 {dm.get("email") or "–"} &nbsp;·&nbsp; '
                f'🔗 {dm.get("linkedin_url") or "–"} &nbsp;·&nbsp; '
                f'Confidence: <strong style="color:{C["cyan"]}">{conf:.0%}</strong></div>'
                f'</div>'
            ), unsafe_allow_html=True)

    with t3:
        email = lead.get("outreach_email", {})
        linkedin = lead.get("linkedin_message", "")
        if not email and not linkedin:
            st.markdown('<div class="warn">Outreach drafts not available — this lead may be disqualified or the Sales Agent encountered an error.</div>', unsafe_allow_html=True)
        if email:
            st.markdown((
                f'<div class="email-wrap">'
                f'<div class="email-hdr">'
                f'<div style="font-size:10px;margin-bottom:2px">PERSONALIZED COLD EMAIL</div>'
                f'<div class="email-subj">{email.get("subject","(no subject)")}</div>'
                f'</div>'
                f'<div class="email-body">{email.get("body","").strip()}</div>'
                f'</div>'
            ), unsafe_allow_html=True)
        if linkedin:
            st.markdown((
                f'<div style="margin-top:14px"><div class="email-wrap">'
                f'<div class="email-hdr"><div style="font-size:10px">LINKEDIN OUTREACH DM</div></div>'
                f'<div class="email-body">{linkedin.strip()}</div>'
                f'</div></div>'
            ), unsafe_allow_html=True)
        chunks = lead.get("rag_context_used", [])
        if chunks:
            with st.expander(f"RAG Grounding Context ({len(chunks)} chunks retrieved from ChromaDB)"):
                for i, ch in enumerate(chunks):
                    st.markdown((
                        f'<div class="rag-chunk">'
                        f'<strong style="color:{C["purple"]}">Chunk {i+1}</strong><br>'
                        f'{ch[:420]}{"..." if len(ch)>420 else ""}'
                        f'</div>'
                    ), unsafe_allow_html=True)

    with t4:
        raw_summary = lead.get("raw_summary", "")
        sections    = parse_summary_sections(raw_summary)

        # ── 3-section company intelligence ─────────────────────────────────────
        SECTION_DEFS = [
            ("overview",    "Company Overview",  C["cyan"],   C["cyan"]),
            ("pain_points", "HR Pain Points",    C["yellow"], C["yellow"]),
            ("fit_signal",  "HRMS Fit Signal",   C["green"],  C["green"]),
        ]
        for key, label, border_color, label_color in SECTION_DEFS:
            text = sections.get(key, "")
            if not text:
                continue
            st.markdown((
                f'<div style="background:{C["card"]};border:1px solid {C["border"]};'
                f'border-left:4px solid {border_color};border-radius:0 10px 10px 0;'
                f'padding:14px 16px;margin-bottom:10px;">'
                f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:1px;color:{label_color};margin-bottom:6px">{label}</div>'
                f'<div style="font-size:13px;color:{C["text"]};line-height:1.65">{text}</div>'
                f'</div>'
            ), unsafe_allow_html=True)

        if not any(sections.get(k) for k, *_ in SECTION_DEFS):
            desc = lead.get("description", "No overview available.")
            st.markdown((
                f'<div style="background:{C["card"]};border:1px solid {C["border"]};'
                f'border-left:4px solid {C["cyan"]};border-radius:0 10px 10px 0;'
                f'padding:14px 16px;margin-bottom:10px;">'
                f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:1px;color:{C["cyan"]};margin-bottom:6px">Company Overview</div>'
                f'<div style="font-size:13px;color:{C["text"]};line-height:1.65">{desc}</div>'
                f'</div>'
            ), unsafe_allow_html=True)

        # ── Company profile card ────────────────────────────────────────────────
        employees   = lead.get("employee_count")
        emp_str     = f"{employees:,}" if employees else "Not detected"
        growth      = lead.get("growth_signal", "unknown").replace("_", " ").title()
        industry    = lead.get("industry") or "Not detected"
        hq          = lead.get("hq_location") or "Not detected"
        domain      = lead.get("domain") or "Not detected"
        status      = lead.get("status", "pending").title()
        score       = lead.get("qualification_score", 0)
        confidence  = lead.get("qualification_confidence", 0)
        tech        = lead.get("tech_stack", [])
        dms         = lead.get("decision_makers", [])
        description = lead.get("description", "")

        def field(label, value, color=None):
            val_style = f'color:{color};' if color else f'color:{C["text"]};'
            return (
                f'<div style="padding:10px 14px;border-bottom:1px solid {C["border"]};">'
                f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:1px;color:{C["dim"]};margin-bottom:3px">{label}</div>'
                f'<div style="font-size:14px;font-weight:600;{val_style}">{value}</div>'
                f'</div>'
            )

        st_color = C["green"] if status == "Qualified" else C["red"]
        tech_tags = "".join(f'<span class="tag">{t}</span>' for t in tech) if tech else f'<span style="color:{C["dim"]};font-size:13px">None detected</span>'
        dm_names  = ", ".join(dm.get("name", "Unknown") for dm in dms) if dms else "None identified"

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown((
                f'<div style="background:{C["card"]};border:1px solid {C["border"]};border-radius:10px;overflow:hidden;margin-bottom:10px">'
                f'<div style="padding:10px 14px;background:{C["surface"]};border-bottom:1px solid {C["border"]};">'
                f'<div style="font-size:11px;font-weight:700;color:{C["cyan"]};text-transform:uppercase;letter-spacing:1px">Company Profile</div>'
                f'</div>'
                + field("Industry", industry)
                + field("Headquarters", hq)
                + field("Employee Count", emp_str)
                + field("Website Domain", domain)
                + field("Growth Signal", growth)
                + field("Lead Status", status, st_color)
                + f'</div>'
            ), unsafe_allow_html=True)

        with col_r:
            st.markdown((
                f'<div style="background:{C["card"]};border:1px solid {C["border"]};border-radius:10px;overflow:hidden;margin-bottom:10px">'
                f'<div style="padding:10px 14px;background:{C["surface"]};border-bottom:1px solid {C["border"]};">'
                f'<div style="font-size:11px;font-weight:700;color:{C["cyan"]};text-transform:uppercase;letter-spacing:1px">Qualification</div>'
                f'</div>'
                + field("Qualification Score", f"{score} / 100", C["cyan"])
                + field("Confidence", f"{confidence:.0%}")
                + field("Decision Makers Found", str(len(dms)))
                + field("DM Names", dm_names)
                + f'</div>'
            ), unsafe_allow_html=True)

        # Tech stack full block
        st.markdown((
            f'<div style="background:{C["card"]};border:1px solid {C["border"]};border-radius:10px;'
            f'padding:12px 14px;margin-bottom:10px;">'
            f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1px;color:{C["dim"]};margin-bottom:8px">Detected Tech Stack</div>'
            f'{tech_tags}'
            f'</div>'
        ), unsafe_allow_html=True)

        # Scraped description (raw source material)
        if description:
            st.markdown((
                f'<div style="background:{C["surface"]};border:1px solid {C["border"]};border-radius:8px;'
                f'padding:12px 14px;margin-bottom:10px;">'
                f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:1px;color:{C["dim"]};margin-bottom:6px">Raw Web Description (Scraped)</div>'
                f'<div style="font-size:12px;color:{C["dim"]};line-height:1.6;font-style:italic">{description}</div>'
                f'</div>'
            ), unsafe_allow_html=True)

        # ── RAG-grounded product context ────────────────────────────────────────
        st.markdown(
            f'<div style="margin-top:18px;font-size:14px;font-weight:700;color:{C["text"]};'
            f'border-left:3px solid #7c3aed;padding-left:10px;">RAG Product Context</div>',
            unsafe_allow_html=True,
        )
        rag_chunks = lead.get("rag_context_used", [])
        if rag_chunks:
            st.markdown(
                f'<div style="font-size:11px;color:{C["dim"]};margin:4px 0 8px 0">'
                f'HumanMaximizer knowledge retrieved for this lead ({len(rag_chunks)} chunks from ChromaDB):</div>',
                unsafe_allow_html=True,
            )
            for i, ch in enumerate(rag_chunks):
                st.markdown((
                    f'<div class="rag-chunk">'
                    f'<strong style="color:#7c3aed">Chunk {i+1}</strong><br>{ch}'
                    f'</div>'
                ), unsafe_allow_html=True)
        else:
            company  = lead.get("company_name", "")
            industry = lead.get("industry", "")
            rag_q    = f"{company} {industry} HRMS payroll HR challenges workforce".strip()
            st.markdown(
                f'<div style="font-size:11px;color:{C["dim"]};margin:4px 0 8px 0">'
                f'No RAG context stored (lead may be disqualified). '
                f'Retrieve relevant product knowledge on-demand:</div>',
                unsafe_allow_html=True,
            )
            if st.button("Fetch RAG Context from ChromaDB", key=f"rag_fetch_{chart_key}"):
                with st.spinner("Querying ChromaDB..."):
                    res = api_get("/api/v1/rag/query", {"q": rag_q})
                if res and res.get("chunks"):
                    for i, ch in enumerate(res["chunks"]):
                        st.markdown((
                            f'<div class="rag-chunk">'
                            f'<strong style="color:#7c3aed">Chunk {i+1}</strong><br>{ch}'
                            f'</div>'
                        ), unsafe_allow_html=True)
                else:
                    st.markdown('<div class="warn">No chunks found — ingest the knowledge base first.</div>',
                                unsafe_allow_html=True)

        # ── Lead metadata ───────────────────────────────────────────────────────
        created = lead.get("created_at", "")
        proc_ms = lead.get("processing_time_ms", 0)
        lead_id = lead.get("lead_id", lead.get("id", "N/A"))
        kw      = lead.get("keyword", "")
        loc     = lead.get("location", "")
        st.markdown((
            f'<div style="margin-top:16px;padding:12px;background:{C["surface"]};'
            f'border:1px solid {C["border"]};border-radius:8px;">'
            f'<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1px;color:{C["dim"]};margin-bottom:8px">Lead Metadata</div>'
            f'<div class="stat-row" style="margin:0">'
            f'<div class="stat-chip">Lead ID: <span style="font-size:10px">{lead_id}</span></div>'
            f'{"<div class=stat-chip>Keyword: <span>" + kw + "</span></div>" if kw else ""}'
            f'{"<div class=stat-chip>Location: <span>" + loc + "</span></div>" if loc else ""}'
            f'{"<div class=stat-chip>Created: <span>" + created[:19].replace("T"," ") + "</span></div>" if created else ""}'
            f'{"<div class=stat-chip>Processing: <span>" + str(proc_ms) + " ms</span></div>" if proc_ms else ""}'
            f'</div>'
            f'</div>'
        ), unsafe_allow_html=True)

        for err in lead.get("errors", []):
            st.markdown(f'<div class="warn" style="margin-top:6px">⚠ {err}</div>', unsafe_allow_html=True)


# ── Page: Home ────────────────────────────────────────────────────────────────

def page_home():
    st.markdown(f"""
    <div class="hero">
        <div class="hero-badge">Razor Infotech · AI Assignment</div>
        <div class="hero-title">HumanMaximizer<br>
            <span style="color:{C['cyan']}">AI Lead Generation Platform</span>
        </div>
        <div class="hero-sub">
            Autonomous 3-Agent Pipeline &nbsp;·&nbsp; LangGraph + Mistral-7B + ChromaDB &nbsp;·&nbsp;
            Production-Ready B2B Lead Intelligence
        </div>
    </div>""", unsafe_allow_html=True)

    # Business Use Case
    st.markdown('<div class="sec">Business Use Case</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <p style="color:{C['dim']};font-size:14px;margin-bottom:14px;">
    HumanMaximizer sells enterprise HRMS software. The sales team needs an intelligent system to
    <strong style="color:{C['text']}">discover, qualify, and engage</strong> potential customers at scale —
    replacing manual Google searches and spreadsheet-based qualification with an AI pipeline.
    </p>""", unsafe_allow_html=True)

    uc = [
        ("🔍", "Find Company Leads",
         "Autonomously discovers companies via live web search (SerpAPI + DuckDuckGo) and scrapes company websites to identify B2B prospects."),
        ("📊", "Research Companies",
         "Extracts structured data: company size, industry, HQ, tech stack, growth signals, and financial indicators from public web sources."),
        ("👤", "Identify Decision Makers",
         "Detects HR leaders, CHROs, and IT heads using contact pattern matching — titles, emails, and LinkedIn profiles."),
        ("📋", "Generate Lead Summaries",
         "Mistral-7B synthesizes a 3-paragraph company intelligence report highlighting HRMS fit, pain points, and opportunity signals."),
        ("✉️", "Create Personalized Outreach",
         "RAG-grounded cold email + LinkedIn drafts using HumanMaximizer product knowledge — each message references product capabilities relevant to the prospect."),
        ("🏆", "Rank Leads by Relevance",
         "5-dimensional scoring (size fit, industry, tech gap, DM reachability, growth) ranks leads 0–100 so reps focus on highest-value prospects."),
    ]
    html = '<div class="uc-grid">'
    for icon, title, desc in uc:
        html += f'<div class="uc-card"><div class="uc-icon">{icon}</div><div class="uc-title">{title}</div><div class="uc-desc">{desc}</div></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown('<div class="sec">3-Agent LangGraph Pipeline</div>', unsafe_allow_html=True)
        for num, title, color, desc in [
            ("1", "Research Agent",       "#7c3aed",
             "SerpAPI search → BeautifulSoup scraping → ContactFinder → Mistral-7B 3-para summary"),
            ("2", "Qualification Agent",  C["yellow"],
             "Deterministic 5-dim scoring → confidence gate → Mistral-7B reasoning justification"),
            ("3", "Sales Agent (RAG)",    C["green"],
             "ChromaDB cosine retrieval → top-5 product chunks → Mistral-7B cold email + LinkedIn"),
        ]:
            st.markdown(f"""
            <div class="pipe-step">
                <div class="step-num" style="background:linear-gradient(135deg,{color},{color}88)">{num}</div>
                <div>
                    <div class="step-title">{title}</div>
                    <div class="step-desc">{desc}</div>
                </div>
            </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="sec">Tech Stack</div>', unsafe_allow_html=True)
        for icon, name, desc in [
            ("🤖", "LangGraph",   "Stateful 3-agent pipeline"),
            ("🧠", "Mistral-7B",  "Local LLM via Ollama"),
            ("🔍", "ChromaDB",    "Vector store for RAG"),
            ("🌐", "SerpAPI",     "Live Google web search"),
            ("🗄️", "SQLite",      "Lead persistence layer"),
            ("⚡", "FastAPI",     "REST API + Swagger UI"),
            ("📊", "Prometheus",  "Metrics & observability"),
        ]:
            st.markdown(f"""
            <div style="display:flex;gap:10px;align-items:center;padding:9px 0;
                border-bottom:1px solid {C['border']};">
                <span style="font-size:18px;width:26px">{icon}</span>
                <div>
                    <div style="font-weight:700;font-size:13px;color:{C['text']}">{name}</div>
                    <div style="font-size:11px;color:{C['dim']}">{desc}</div>
                </div>
            </div>""", unsafe_allow_html=True)

    # Live stats
    st.markdown('<div class="sec">Live System Stats</div>', unsafe_allow_html=True)
    h = health_check()
    leads_data = api_get("/api/v1/leads", {"limit": 100})

    c1, c2, c3, c4, c5 = st.columns(5)
    sc, sl = (C["green"], "Online") if h else (C["red"], "Offline")
    with c1:
        st.markdown(f"""
        <div style="background:{C['card']};border:1px solid {C['border']};border-radius:12px;
            padding:18px;text-align:center;">
            <div style="font-size:11px;color:{C['dim']};text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">API</div>
            <div style="font-size:24px;font-weight:800;color:{sc}">{sl}</div>
        </div>""", unsafe_allow_html=True)

    all_leads = leads_data.get("leads", []) if leads_data else []
    total     = leads_data.get("count", 0)  if leads_data else 0
    qualified = len([l for l in all_leads if l.get("is_qualified")])
    scores    = [l.get("qualification_score", 0) for l in all_leads]
    avg_score = sum(scores) // len(scores) if scores else 0

    with c2: st.metric("Total Leads",  total)
    with c3: st.metric("Qualified",    qualified)
    with c4: st.metric("Disqualified", total - qualified)
    with c5: st.metric("Avg Score",    f"{avg_score}/100")

    if h:
        st.markdown(f"""
        <div class="ok" style="margin-top:12px">
            ✓ Backend running · Model: <strong>{h.get('llm_model','N/A')}</strong> ·
            Version: <strong>{h.get('version','N/A')}</strong> ·
            Env: <strong>{h.get('app_env','N/A')}</strong>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="err" style="margin-top:12px">
            ⚠ Backend offline — start with:
            <code>uvicorn backend.main:app --reload --port 8000</code>
        </div>""", unsafe_allow_html=True)


# ── Page: Search ──────────────────────────────────────────────────────────────

def page_search():
    st.markdown(f"""
    <div style="margin-bottom:22px">
        <div style="font-size:26px;font-weight:800;color:{C['text']}">Find AI-Qualified Leads</div>
        <div style="font-size:13px;color:{C['dim']};margin-top:4px">
            Enter a target market and location. The 3-agent pipeline will research, score,
            and draft personalised outreach — with full chain-of-thought transparency.
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Init session state ────────────────────────────────────────────────────
    for k, v in [("kw", ""), ("loc", ""), ("max_leads", 3)]:
        if k not in st.session_state:
            st.session_state[k] = v

    # ── Preset examples ───────────────────────────────────────────────────────
    st.markdown(f'<div style="font-size:11px;color:{C["dim"]};margin-bottom:6px">Quick examples:</div>',
                unsafe_allow_html=True)
    ex1, ex2, ex3 = st.columns(3)
    presets = [
        ("Manufacturing · Pune",       "auto component manufacturing companies",  "Pune, India"),
        ("Healthcare · Mumbai",        "hospital chains diagnostics companies",   "Mumbai, India"),
        ("Pharma · Hyderabad",         "pharmaceutical manufacturing companies",  "Hyderabad, India"),
    ]
    for col, (label, kw, loc) in zip([ex1, ex2, ex3], presets):
        with col:
            if st.button(label, key=f"ex_{kw}"):
                st.session_state.kw  = kw
                st.session_state.loc = loc
                st.rerun()

    # ── Form ──────────────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([3, 2, 1])
    with fc1:
        keyword = st.text_input("Target Market / Industry",
                                placeholder="e.g. auto component manufacturing, pharma, hospital chains, NBFC",
                                key="kw")
    with fc2:
        location = st.text_input("Location",
                                  placeholder="e.g. Pune, India",
                                  key="loc")
    with fc3:
        max_leads = st.number_input("Max Leads", min_value=1, max_value=10,
                                    value=st.session_state.max_leads, key="max_leads")

    run = st.button("🚀  Launch AI Agent Pipeline", type="primary")

    if not run:
        st.markdown(f"""
        <div style="margin-top:28px;text-align:center;padding:44px;background:{C['card']};
            border:1px dashed {C['border']};border-radius:14px;">
            <div style="font-size:38px;margin-bottom:14px">🤖</div>
            <div style="font-size:17px;font-weight:700;color:{C['text']};margin-bottom:6px">Ready to Find Leads</div>
            <div style="font-size:13px;color:{C['dim']}">
                Enter a keyword and location above, then click
                <strong style="color:{C['cyan']}">Launch AI Agent Pipeline</strong><br>
                The system runs the full 3-agent workflow and displays chain-of-thought reasoning.
            </div>
        </div>""", unsafe_allow_html=True)
        return

    if not keyword.strip():
        st.markdown('<div class="warn">Please enter a keyword.</div>', unsafe_allow_html=True)
        return

    # ── Background API call ───────────────────────────────────────────────────
    result_box: list = []
    error_box:  list = []

    def call_api():
        try:
            r = httpx.post(
                f"{API_BASE}/api/v1/search",
                json={"keyword": keyword, "location": location, "max_leads": max_leads},
                timeout=API_TIMEOUT,
            )
            r.raise_for_status()
            result_box.append(r.json())
        except Exception as e:
            error_box.append(str(e))

    t = threading.Thread(target=call_api, daemon=True)
    t.start()

    # ── Chain-of-thought display ──────────────────────────────────────────────
    st.markdown(f"""
    <div class="sec">Chain-of-Thought: Agent Execution Trace</div>
    <div style="font-size:12px;color:{C['dim']};margin-bottom:12px">
        Watching 3 autonomous agents collaborate for:
        <strong style="color:{C['text']}">"{keyword}"</strong>
        {f'in <strong style="color:{C["text"]}">{location}</strong>' if location else ''}
    </div>""", unsafe_allow_html=True)

    RESEARCH_STEPS = [
        f"Initialising SerpAPI search: <em>\"{keyword} {location}\"</em>",
        "Parsing top-10 SERP results, deduplicating by domain...",
        "Scraping company websites with BeautifulSoup HTML parser...",
        "Extracting structured fields: name, domain, industry, HQ, employee count...",
        "Running ContactFinder: regex pattern matching for HR decision-maker titles...",
        "Detecting tech stack signals from job postings and website footers...",
        "Identifying growth signals: hiring surge, funding, expansion keywords...",
        "Mistral-7B generating 3-paragraph company intelligence summaries...",
    ]
    QUAL_STEPS = [
        "Scoring <strong>Company Size Fit</strong> (0–20): mapping headcount to HRMS buyer profile...",
        "Scoring <strong>Industry Relevance</strong> (0–20): matching against mfg, IT, healthcare, BFSI...",
        "Scoring <strong>Tech Stack Gap</strong> (0–20): Excel/legacy HRMS vs modern platform signals...",
        "Scoring <strong>Decision Maker Reachability</strong> (0–20): confidence-weighted contact count...",
        "Scoring <strong>Growth Signal</strong> (0–20): hiring surge, recent funding, expansion indicators...",
        "Computing qualification confidence = data_completeness × (score / 100)...",
        "Applying gates: score ≥ 35 AND field completeness ≥ 40%...",
        "Mistral-7B generating 2-sentence qualification reasoning for each lead...",
    ]
    SALES_STEPS = [
        "Building RAG query from company + industry + tech_stack + growth_signal...",
        "Querying ChromaDB with nomic-embed-text cosine similarity index...",
        "Retrieving top-5 semantically relevant HumanMaximizer product knowledge chunks...",
        "Grounding outreach in retrieved features: attendance, payroll, compliance modules...",
        "Mistral-7B generating personalised cold email (subject + body)...",
        "Crafting LinkedIn DM optimised for HR decision-maker tone and length...",
        "Persisting qualified leads and outreach drafts to SQLite...",
    ]

    with st.status("🤖 AI Agent Pipeline Executing...", expanded=True) as pipeline_status:
        # Agent 1
        st.markdown(f"""
        <div class="trace r" style="margin-bottom:6px">
          <div class="tlabel">🔬 Agent 1 · Research Agent</div>
        </div>""", unsafe_allow_html=True)
        for step in RESEARCH_STEPS:
            st.markdown(f'<div class="cot-step">⟳ &nbsp;{step}</div>', unsafe_allow_html=True)
            time.sleep(1.2)
        st.markdown(f'<div class="cot-done">✓ Research complete — companies discovered and profiled</div>',
                    unsafe_allow_html=True)

        # Agent 2
        st.markdown(f"""
        <div class="trace q2" style="margin:10px 0 6px 0">
          <div class="tlabel">⚖️ Agent 2 · Qualification Agent</div>
        </div>""", unsafe_allow_html=True)
        for step in QUAL_STEPS:
            st.markdown(f'<div class="cot-step">⟳ &nbsp;{step}</div>', unsafe_allow_html=True)
            time.sleep(0.9)
        st.markdown(f'<div class="cot-done">✓ Qualification complete — leads scored and ranked</div>',
                    unsafe_allow_html=True)

        # Agent 3
        st.markdown(f"""
        <div class="trace s" style="margin:10px 0 6px 0">
          <div class="tlabel">✉️ Agent 3 · Sales Agent (RAG-Grounded)</div>
        </div>""", unsafe_allow_html=True)
        for step in SALES_STEPS:
            st.markdown(f'<div class="cot-step">⟳ &nbsp;{step}</div>', unsafe_allow_html=True)
            time.sleep(1.0)
        st.markdown(f'<div class="cot-done">✓ Outreach generated — RAG-grounded email + LinkedIn drafts ready</div>',
                    unsafe_allow_html=True)

        # Wait for actual API response
        if t.is_alive():
            st.markdown(f'<div style="color:{C["yellow"]};font-size:13px">⏳ Waiting for LLM to finish...</div>',
                        unsafe_allow_html=True)
            t.join()

        if error_box:
            pipeline_status.update(label="Pipeline failed", state="error")
        else:
            pipeline_status.update(label="✓ Pipeline complete — results ready", state="complete")

    # ── Results ────────────────────────────────────────────────────────────────
    if error_box:
        st.markdown(f'<div class="err">Pipeline error: {error_box[0]}</div>', unsafe_allow_html=True)
        return

    if not result_box:
        st.markdown('<div class="err">No response received.</div>', unsafe_allow_html=True)
        return

    data   = result_box[0]
    leads  = data.get("leads", [])
    total  = data.get("total", 0)
    n_qual = len([l for l in leads if l.get("lead", {}).get("is_qualified")])

    st.markdown(f"""
    <div class="ok">
        ✓ Pipeline complete · Found <strong>{total}</strong> lead{'s' if total != 1 else ''} ·
        <strong>{n_qual}</strong> qualified ·
        keyword: <em>{data.get('keyword','')}</em>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec">Ranked Lead Results</div>', unsafe_allow_html=True)

    for item in leads:
        rank    = item.get("rank", 0)
        lead    = item.get("lead", {})
        company = lead.get("company_name", f"Lead #{rank}")
        score   = lead.get("qualification_score", 0)

        st.markdown(lead_card_html(lead, rank), unsafe_allow_html=True)
        with st.expander(f"Full Details: {company} — Score {score}/100"):
            render_lead_detail(lead, chart_key=f"s{rank}")


# ── Page: History ─────────────────────────────────────────────────────────────

def page_history():
    st.markdown(f"""
    <div style="margin-bottom:22px">
        <div style="font-size:26px;font-weight:800;color:{C['text']}">Lead History</div>
        <div style="font-size:13px;color:{C['dim']};margin-top:4px">
            Browse, filter, and inspect all stored leads.
        </div>
    </div>""", unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        status_f = st.selectbox("Filter by Status", ["All", "qualified", "disqualified", "error"])
    with fc2:
        sort_by  = st.selectbox("Sort By", ["created_at", "qualification_score", "company_name"])
    with fc3:
        limit    = st.number_input("Show", min_value=5, max_value=100, value=20, step=5)

    params = {"limit": limit, "sort_by": sort_by}
    if status_f != "All":
        params["status"] = status_f

    data = api_get("/api/v1/leads", params)
    if not data:
        return

    leads = data.get("leads", [])
    total = data.get("count", 0)

    if not leads:
        st.markdown('<div class="warn">No leads yet — run a search to generate leads.</div>',
                    unsafe_allow_html=True)
        return

    q_leads = [l for l in leads if l.get("is_qualified")]
    scores  = [l.get("qualification_score", 0) for l in leads]
    avg     = sum(scores) // len(scores) if scores else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Leads",  total)
    with c2: st.metric("Qualified",    len(q_leads))
    with c3: st.metric("Avg Score",    f"{avg}/100")
    with c4: st.metric("Top Score",    f"{max(scores) if scores else 0}/100")

    if scores:
        fig = go.Figure(go.Histogram(
            x=scores, nbinsx=10,
            marker_color="#00d4ff", marker_line_color="#0a0e1a",
            marker_line_width=1, opacity=0.8,
        ))
        fig.update_layout(
            title="Score Distribution",
            paper_bgcolor="#0a0e1a", plot_bgcolor="#141826",
            font=dict(color="#e8eaf6"),
            xaxis=dict(title="Qualification Score", gridcolor="#1e2d4a", range=[0,100]),
            yaxis=dict(title="Count", gridcolor="#1e2d4a"),
            height=200, margin=dict(t=40,b=40,l=40,r=20),
        )
        st.plotly_chart(fig, use_container_width=True, key="hist_scores")

    st.markdown('<div class="sec">All Leads</div>', unsafe_allow_html=True)
    for hi, lead in enumerate(leads):
        st.markdown(lead_card_html(lead), unsafe_allow_html=True)
        with st.expander(f"Details: {lead.get('company_name','Lead')} (Score {lead.get('qualification_score',0)})"):
            render_lead_detail(lead, chart_key=f"h{hi}")


# ── Page: Knowledge Base ──────────────────────────────────────────────────────

def page_kb():
    st.markdown(f"""
    <div style="margin-bottom:22px">
        <div style="font-size:26px;font-weight:800;color:{C['text']}">RAG Knowledge Base</div>
        <div style="font-size:13px;color:{C['dim']};margin-top:4px">
            HumanMaximizer product knowledge crawled from humanmaximizer.com,
            chunked, embedded with nomic-embed-text, and indexed in ChromaDB for outreach grounding.
        </div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2])

    with c1:
        st.markdown('<div class="sec">How RAG Grounds Every Email</div>', unsafe_allow_html=True)
        for num, title, desc in [
            ("1","Crawl",    "WebIngestor crawls humanmaximizer.com pages"),
            ("2","Chunk",    "Text split into 512-token chunks, 64-token overlap"),
            ("3","Embed",    "nomic-embed-text (Ollama) → 768-dim vectors"),
            ("4","Index",    "Vectors stored in ChromaDB with cosine similarity"),
            ("5","Retrieve", "Top-5 semantically similar chunks per lead query"),
            ("6","Ground",   "Mistral-7B email references retrieved product facts"),
        ]:
            st.markdown(f"""
            <div class="pipe-step">
                <div class="step-num" style="background:linear-gradient(135deg,#7c3aed,#7c3aed88)">{num}</div>
                <div>
                    <div class="step-title">{title}</div>
                    <div class="step-desc">{desc}</div>
                </div>
            </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="sec">Manage Knowledge Base</div>', unsafe_allow_html=True)
        refresh = st.checkbox("Force re-crawl (refresh existing)", value=False)
        if st.button("Ingest humanmaximizer.com"):
            with st.spinner("Crawling and indexing..."):
                res = api_post("/api/v1/rag/ingest", {"refresh": refresh})
            if res:
                st.markdown(f"""
                <div class="ok">✓ {res.get('message','Done')} ·
                Chunks indexed: <strong>{res.get('chunks_indexed',0)}</strong></div>""",
                            unsafe_allow_html=True)

        st.markdown('<div class="sec" style="margin-top:20px">Test Retrieval</div>', unsafe_allow_html=True)
        query = st.text_input("Query", placeholder="e.g. attendance management features")
        if st.button("Search ChromaDB") and query:
            with st.spinner("Querying..."):
                res = api_get("/api/v1/rag/query", {"q": query})
            if res:
                chunks = res.get("chunks", [])
                count  = res.get("chunks_count", 0)
                if count == 0:
                    st.markdown('<div class="warn">No chunks found — try ingesting first.</div>',
                                unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="font-size:12px;color:{C['dim']};margin-bottom:6px">
                        Retrieved <strong style="color:{C['cyan']}">{count}</strong> chunks for:
                        <em>"{query}"</em>
                    </div>""", unsafe_allow_html=True)
                    for i, ch in enumerate(chunks):
                        st.markdown(f"""
                        <div class="rag-chunk">
                            <strong style="color:{C['purple']}">Chunk {i+1}</strong><br>{ch}
                        </div>""", unsafe_allow_html=True)


# ── Sidebar + main ────────────────────────────────────────────────────────────

def sidebar() -> str:
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:18px 0;border-bottom:1px solid {C['border']};margin-bottom:18px">
            <div style="font-size:30px">🎯</div>
            <div style="font-size:17px;font-weight:800;color:{C['cyan']};margin-top:6px">HumanMaximizer</div>
            <div style="font-size:10px;color:{C['dim']};text-transform:uppercase;letter-spacing:1px">
                AI Lead Gen Platform
            </div>
        </div>""", unsafe_allow_html=True)

        page = st.radio(
            "nav", ["🏠  Home", "🔍  Find Leads", "📋  Lead History", "🧠  Knowledge Base"],
            label_visibility="hidden",
        )

        st.markdown("---")
        h = health_check()
        sc, sl = (C["green"], "● API Online") if h else (C["red"], "● API Offline")
        st.markdown(f'<div style="font-size:13px;color:{sc}">{sl}</div>', unsafe_allow_html=True)
        if h:
            st.markdown(f"""
            <div style="font-size:11px;color:{C['dim']};margin-top:3px">
                {h.get('llm_model','')} · v{h.get('version','')}
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"""
        <div style="font-size:11px;color:{C['dim']};text-align:center;line-height:1.7">
            Built for Razor Infotech<br>
            LangGraph · Mistral-7B · ChromaDB<br>
            FastAPI · SQLite · Prometheus
        </div>""", unsafe_allow_html=True)

    return page


def main():
    page = sidebar()
    if   "Home"           in page: page_home()
    elif "Find Leads"     in page: page_search()
    elif "Lead History"   in page: page_history()
    elif "Knowledge Base" in page: page_kb()


if __name__ == "__main__":
    main()
