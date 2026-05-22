import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import json
import os
import uuid
from datetime import datetime, date

st.set_page_config(
    page_title="Carteira Tiago",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Paleta de cores ────────────────────────────────────────────────────────────
C_BG       = "#0D1117"
C_CARD     = "#161B27"
C_CARD2    = "#1C2333"
C_BLUE     = "#4B9FFF"
C_GREEN    = "#00D48A"
C_RED      = "#FF5252"
C_GOLD     = "#FFB347"
C_PURPLE   = "#A78BFA"
C_TEXT     = "#E8EDF5"
C_MUTED    = "#7A8BA8"

CHART_COLORS = [C_BLUE, C_GREEN, C_GOLD, C_RED, C_PURPLE,
                "#38BDF8", "#FB923C", "#34D399", "#F472B6", "#818CF8"]

# ── CSS global ─────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
<style>
/* ── Reset e base ── */
#MainMenu, footer, header {{visibility: hidden;}}
.stDeployButton {{display:none;}}

body, .stApp {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
}}

/* ── Container central ── */
.main .block-container {{
    padding: 1rem 1rem 3rem 1rem;
    max-width: 860px;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: {C_CARD};
    border-right: 1px solid #1E2A3A;
}}
[data-testid="stSidebar"] .stRadio label {{
    font-size: 15px !important;
    padding: 8px 4px;
}}

/* ── Mobile: colunas empilham ── */
@media (max-width: 600px) {{
    div[data-testid="column"] {{
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }}
    .main .block-container {{ padding: 0.5rem 0.5rem 3rem 0.5rem; }}
}}

/* ── KPI cards ── */
.kpi-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin: 8px 0 20px 0;
}}
.kpi-card {{
    background: {C_CARD};
    border-radius: 14px;
    padding: 14px 16px;
    border-top: 3px solid;
    text-align: left;
    box-shadow: 0 2px 12px rgba(0,0,0,0.3);
}}
.kpi-label {{
    font-size: 10px;
    color: {C_MUTED};
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 5px;
}}
.kpi-value {{
    font-size: 1.35rem;
    font-weight: 700;
    color: {C_TEXT};
    line-height: 1.2;
    word-break: break-all;
}}
.kpi-delta {{
    font-size: 12px;
    font-weight: 600;
    margin-top: 4px;
}}
.pos {{ color: {C_GREEN}; }}
.neg {{ color: {C_RED}; }}
.neu {{ color: {C_MUTED}; }}

/* ── Títulos de seção ── */
.section-title {{
    font-size: 13px;
    font-weight: 700;
    color: {C_MUTED};
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 20px 0 8px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #1E2A3A;
}}

/* ── Tabelas ── */
[data-testid="stDataFrame"] {{
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #1E2A3A;
}}

/* ── Tabs ── */
button[data-baseweb="tab"] {{
    font-size: 13px !important;
    padding: 8px 12px !important;
}}

/* ── Métricas nativas ── */
[data-testid="stMetric"] {{
    background: {C_CARD};
    border-radius: 10px;
    padding: 10px 14px;
    border: 1px solid #1E2A3A;
}}
[data-testid="stMetricLabel"] {{ font-size: 11px !important; color: {C_MUTED} !important; }}
[data-testid="stMetricValue"] {{ font-size: 1.1rem !important; font-weight: 700 !important; }}

/* ── Botões ── */
.stButton > button {{
    border-radius: 10px;
    font-weight: 600;
    border: 1px solid #2A3A55;
    background: {C_CARD2};
    color: {C_TEXT};
    transition: all 0.2s;
}}
.stButton > button:hover {{
    background: #1E2D4A;
    border-color: {C_BLUE};
    color: {C_BLUE};
}}

/* ── Selectbox / Input ── */
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {{
    background-color: {C_CARD2} !important;
    border-color: #2A3A55 !important;
    border-radius: 8px !important;
}}
</style>
""", unsafe_allow_html=True)


# ── Helpers de dados ───────────────────────────────────────────────────────────

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "portfolio.json")


def load_portfolio() -> dict:
    if "portfolio" not in st.session_state:
        with open(DATA_PATH, encoding="utf-8") as f:
            st.session_state["portfolio"] = json.load(f)
    return st.session_state["portfolio"]


def save_portfolio(portfolio: dict):
    st.session_state["portfolio"] = portfolio
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_df(portfolio: dict) -> pd.DataFrame:
    rows = []
    usd_rate = portfolio["metadata"].get("usd_brl_rate", 5.87)
    for p in portfolio["positions"]:
        row = dict(p)
        if row.get("moeda") == "USD" and row.get("atual_usd"):
            row["atual_brl"] = row["atual_usd"] * usd_rate
        row["variacao_brl"] = (row.get("atual_brl") or 0) - (row.get("custo_brl") or 0)
        custo = row.get("custo_brl") or 0
        row["variacao_pct"] = (row["variacao_brl"] / custo * 100) if custo else 0
        rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for col in ["custo_brl", "atual_brl", "variacao_brl"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


# ── Cotações ───────────────────────────────────────────────────────────────────

def fetch_prices(tickers: list[str]) -> dict[str, float]:
    results = {}
    if not tickers:
        return results
    try:
        data = yf.download(tickers, period="1d", progress=False, auto_adjust=True)
        close = data["Close"] if "Close" in data else data.get("close", pd.DataFrame())
        if isinstance(close, pd.Series):
            close = close.to_frame(tickers[0])
        for t in tickers:
            if t in close.columns and not close[t].dropna().empty:
                results[t] = float(close[t].dropna().iloc[-1])
    except Exception:
        pass
    return results


def fetch_usd_brl() -> float:
    try:
        tick = yf.Ticker("BRL=X")
        hist = tick.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return 5.87


# ── Formatação ─────────────────────────────────────────────────────────────────

def fmt_brl(v: float, sign: bool = False) -> str:
    if v is None:
        return "—"
    prefix = "+" if (sign and v > 0) else ""
    return f"R$ {prefix}{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v: float, sign: bool = True) -> str:
    if v is None:
        return "—"
    prefix = "+" if (sign and v > 0) else ""
    return f"{prefix}{v:.2f}%"


def delta_cls(v: float) -> str:
    return "pos" if v > 0 else ("neg" if v < 0 else "neu")


def chart_layout(height=360):
    return dict(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=C_TEXT, family="-apple-system, BlinkMacSystemFont, sans-serif", size=12),
        margin=dict(t=24, b=24, l=8, r=8),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        hoverlabel=dict(bgcolor=C_CARD2, bordercolor=C_BLUE, font_color=C_TEXT),
    )


# ── KPI Card (HTML) ────────────────────────────────────────────────────────────

def kpi_card(label: str, value: str, delta: str = "", border_color: str = C_BLUE) -> str:
    d_cls = "pos" if delta.startswith("+") else ("neg" if delta.startswith("-") else "neu")
    delta_html = f'<div class="kpi-delta {d_cls}">{delta}</div>' if delta else ""
    return f"""
<div class="kpi-card" style="border-top-color:{border_color}">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value">{value}</div>
  {delta_html}
</div>"""


# ── Sidebar ────────────────────────────────────────────────────────────────────

def render_sidebar(portfolio: dict):
    with st.sidebar:
        st.markdown("### 📊 Carteira Tiago")
        st.markdown("---")
        page = st.radio(
            "Menu",
            ["🏠 Dashboard", "💼 Posições", "📈 Análises",
             "➕ Gerenciar", "🔄 Atualizar", "⚙️ Config"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        usd = portfolio["metadata"].get("usd_brl_rate", 5.87)
        updated = portfolio["metadata"].get("last_updated", "—")
        st.metric("USD/BRL", f"R$ {usd:.4f}")
        st.caption(f"Atualizado: {updated}")
        st.markdown("---")
        st.download_button(
            "💾 Exportar JSON",
            data=json.dumps(portfolio, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"carteira_{date.today().isoformat()}.json",
            mime="application/json",
            use_container_width=True,
        )
    return page


# ── Dashboard ──────────────────────────────────────────────────────────────────

def render_dashboard(portfolio: dict, df: pd.DataFrame):
    usd = portfolio["metadata"].get("usd_brl_rate", 5.87)
    total_custo = df["custo_brl"].sum()
    total_atual = df["atual_brl"].sum()
    total_var   = total_atual - total_custo
    total_pct   = (total_var / total_custo * 100) if total_custo else 0

    st.markdown("## 📊 Carteira Tiago")

    # ── KPI cards 2x2 ──
    cards_html = f"""
<div class="kpi-grid">
  {kpi_card("Patrimônio Atual", fmt_brl(total_atual), border_color=C_BLUE)}
  {kpi_card("Custo Total", fmt_brl(total_custo), border_color=C_MUTED)}
  {kpi_card("Variação R$", fmt_brl(total_var, sign=True),
            delta="▲" if total_var >= 0 else "▼",
            border_color=C_GREEN if total_var >= 0 else C_RED)}
  {kpi_card("Variação %", fmt_pct(total_pct),
            border_color=C_GREEN if total_pct >= 0 else C_RED)}
</div>"""
    st.markdown(cards_html, unsafe_allow_html=True)

    # ── Alocação por Tipo (donut) ──
    st.markdown('<div class="section-title">Alocação por Tipo</div>', unsafe_allow_html=True)
    df_tipo = df.groupby("tipo")["atual_brl"].sum().reset_index()
    df_tipo = df_tipo[df_tipo["atual_brl"] > 0].sort_values("atual_brl", ascending=False)
    total_t = df_tipo["atual_brl"].sum()
    df_tipo["pct"] = df_tipo["atual_brl"] / total_t * 100
    df_tipo["label"] = df_tipo.apply(
        lambda r: f"{r['tipo']} ({r['pct']:.1f}%)", axis=1)
    fig_tipo = px.pie(
        df_tipo, values="atual_brl", names="label",
        hole=0.55, color_discrete_sequence=CHART_COLORS,
    )
    fig_tipo.update_traces(
        textposition="outside",
        textinfo="label",
        textfont_size=11,
        pull=[0.03] * len(df_tipo),
    )
    fig_tipo.update_layout(
        **chart_layout(380),
        showlegend=False,
        annotations=[dict(
            text=f"<b>{fmt_brl(total_atual)}</b>",
            x=0.5, y=0.5, font_size=14, showarrow=False,
            font_color=C_TEXT,
        )],
    )
    st.plotly_chart(fig_tipo, use_container_width=True)

    # ── Treemap Classe › Tipo ──
    st.markdown('<div class="section-title">Distribuição por Classe</div>', unsafe_allow_html=True)
    df_tree = df.groupby(["classe", "tipo"])["atual_brl"].sum().reset_index()
    df_tree = df_tree[df_tree["atual_brl"] > 0]
    total_tree = df_tree["atual_brl"].sum()
    df_tree["pct"] = df_tree["atual_brl"] / total_tree * 100
    fig_tree = px.treemap(
        df_tree, path=["classe", "tipo"], values="atual_brl",
        color="pct", color_continuous_scale=[[0, "#1A2744"], [0.5, "#2563EB"], [1, C_BLUE]],
        custom_data=["pct"],
    )
    fig_tree.update_traces(
        texttemplate="<b>%{label}</b><br>%{customdata[0]:.1f}%",
        textinfo="label+text",
        textfont_size=13,
    )
    fig_tree.update_layout(**chart_layout(360))
    fig_tree.update_coloraxes(showscale=False)
    st.plotly_chart(fig_tree, use_container_width=True)

    # ── Barras horizontais por Tipo ──
    st.markdown('<div class="section-title">Valor por Tipo</div>', unsafe_allow_html=True)
    df_bar = df_tipo.sort_values("atual_brl")
    colors_bar = CHART_COLORS[:len(df_bar)]
    fig_bar = go.Figure(go.Bar(
        x=df_bar["atual_brl"],
        y=df_bar["tipo"],
        orientation="h",
        text=[fmt_brl(v) for v in df_bar["atual_brl"]],
        textposition="outside",
        marker_color=colors_bar,
        textfont=dict(size=11, color=C_TEXT),
    ))
    fig_bar.update_layout(
        **chart_layout(380),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False),
        showlegend=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Performance por Classe ──
    st.markdown('<div class="section-title">Performance por Classe</div>', unsafe_allow_html=True)
    df_perf = df.groupby("classe").agg(
        custo=("custo_brl", "sum"), atual=("atual_brl", "sum"),
    ).reset_index()
    df_perf["variacao"] = df_perf["atual"] - df_perf["custo"]
    df_perf["pct"]      = df_perf["variacao"] / df_perf["custo"] * 100
    df_perf = df_perf[df_perf["custo"] > 0].sort_values("pct")
    c_perf = [C_GREEN if v >= 0 else C_RED for v in df_perf["pct"]]
    fig_perf = go.Figure(go.Bar(
        x=df_perf["pct"],
        y=df_perf["classe"],
        orientation="h",
        text=[fmt_pct(p) for p in df_perf["pct"]],
        textposition="outside",
        marker_color=c_perf,
        textfont=dict(size=11, color=C_TEXT),
    ))
    fig_perf.update_layout(
        **chart_layout(300),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=True,
                   zerolinecolor="#2A3A55"),
        yaxis=dict(showgrid=False),
        showlegend=False,
    )
    st.plotly_chart(fig_perf, use_container_width=True)

    # ── Corretoras ──
    st.markdown('<div class="section-title">Por Corretora</div>', unsafe_allow_html=True)
    df_corr = df.groupby("corretora")["atual_brl"].sum().reset_index().sort_values("atual_brl", ascending=False)
    df_corr = df_corr[df_corr["atual_brl"] > 0]
    df_corr["pct"] = df_corr["atual_brl"] / df_corr["atual_brl"].sum() * 100
    cols = st.columns(min(len(df_corr), 3))
    for i, (_, row) in enumerate(df_corr.iterrows()):
        cols[i % len(cols)].metric(
            row["corretora"],
            fmt_brl(row["atual_brl"]),
            f"{row['pct']:.1f}%",
        )


# ── Posições ───────────────────────────────────────────────────────────────────

def render_posicoes(portfolio: dict, df: pd.DataFrame):
    st.markdown("## 💼 Posições")

    col_f1, col_f2 = st.columns(2)
    classe_sel = col_f1.selectbox("Classe", ["Todas"] + sorted(df["classe"].unique().tolist()))
    tipo_sel   = col_f2.selectbox("Tipo",   ["Todos"] + sorted(df["tipo"].unique().tolist()))
    corr_sel   = st.selectbox("Corretora",  ["Todas"] + sorted(df["corretora"].unique().tolist()))

    filt = df.copy()
    if classe_sel != "Todas":  filt = filt[filt["classe"] == classe_sel]
    if tipo_sel   != "Todos":  filt = filt[filt["tipo"]   == tipo_sel]
    if corr_sel   != "Todas":  filt = filt[filt["corretora"] == corr_sel]

    total_custo = filt["custo_brl"].sum()
    total_atual = filt["atual_brl"].sum()
    total_var   = total_atual - total_custo

    cards_html = f"""
<div class="kpi-grid">
  {kpi_card("Atual Filtrado", fmt_brl(total_atual), border_color=C_BLUE)}
  {kpi_card("Custo Filtrado", fmt_brl(total_custo), border_color=C_MUTED)}
  {kpi_card("Variação R$", fmt_brl(total_var, sign=True),
            border_color=C_GREEN if total_var >= 0 else C_RED)}
  {kpi_card("Posições", str(len(filt)), border_color=C_GOLD)}
</div>"""
    st.markdown(cards_html, unsafe_allow_html=True)

    show_cols = ["corretora", "titulo", "tipo", "custo_brl", "atual_brl", "variacao_brl", "variacao_pct"]
    show_cols = [c for c in show_cols if c in filt.columns]
    disp = filt[show_cols].copy()
    disp["custo_brl"]    = filt["custo_brl"].apply(fmt_brl)
    disp["atual_brl"]    = filt["atual_brl"].apply(fmt_brl)
    disp["variacao_brl"] = filt["variacao_brl"].apply(lambda v: fmt_brl(v, sign=True))
    disp["variacao_pct"] = filt["variacao_pct"].apply(fmt_pct)
    disp.columns = ["Corretora", "Título", "Tipo", "Custo", "Atual", "Var R$", "Var %"]

    st.dataframe(disp, use_container_width=True, height=480)


# ── Análises ───────────────────────────────────────────────────────────────────

def render_analises(portfolio: dict, df: pd.DataFrame):
    st.markdown("## 📈 Análises")
    tabs = st.tabs(["RF por Indexador", "Emissores", "Renda Variável", "Internacional"])

    # ── Tab 0: RF por Indexador ──
    with tabs[0]:
        df_fi = df[df["classe"] == "RENDA FIXA"]
        if df_fi.empty:
            st.info("Sem posições de renda fixa.")
        else:
            df_idx = df_fi.groupby("tipo")["atual_brl"].sum().reset_index().sort_values("atual_brl", ascending=False)
            total_fi = df_idx["atual_brl"].sum()
            df_idx["pct"] = df_idx["atual_brl"] / total_fi * 100
            df_idx["label"] = df_idx.apply(lambda r: f"{r['tipo']} ({r['pct']:.1f}%)", axis=1)

            fig = px.pie(df_idx, values="atual_brl", names="label", hole=0.52,
                         color_discrete_sequence=CHART_COLORS)
            fig.update_traces(textposition="outside", textinfo="label", textfont_size=11)
            fig.update_layout(**chart_layout(360), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            # Tabela resumo
            df_sum = df_fi.groupby("tipo").agg(n=("id","count"), custo=("custo_brl","sum"), atual=("atual_brl","sum")).reset_index()
            df_sum["variacao"] = df_sum["atual"] - df_sum["custo"]
            df_sum["pct"]      = df_sum["variacao"] / df_sum["custo"] * 100
            disp = df_sum.copy()
            disp["custo"]    = df_sum["custo"].apply(fmt_brl)
            disp["atual"]    = df_sum["atual"].apply(fmt_brl)
            disp["variacao"] = df_sum["variacao"].apply(lambda v: fmt_brl(v, sign=True))
            disp["pct"]      = df_sum["pct"].apply(fmt_pct)
            st.dataframe(
                disp.rename(columns={"tipo":"Tipo","n":"Qtd","custo":"Custo","atual":"Atual","variacao":"Variação","pct":"Var%"}),
                use_container_width=True,
            )

    # ── Tab 1: Emissores ──
    with tabs[1]:
        df_fi = df[df["classe"] == "RENDA FIXA"]
        df_em = df_fi.groupby("emissor")["atual_brl"].sum().reset_index().sort_values("atual_brl", ascending=False)
        df_em = df_em[df_em["atual_brl"] > 0].head(25)
        if df_em.empty:
            st.info("Sem emissores.")
        else:
            total_fi = df_fi["atual_brl"].sum()
            df_em["pct"] = df_em["atual_brl"] / total_fi * 100
            fig = go.Figure(go.Bar(
                x=df_em["atual_brl"], y=df_em["emissor"],
                orientation="h",
                text=[f"{r['pct']:.1f}%" for _, r in df_em.iterrows()],
                textposition="outside",
                marker_color=C_BLUE,
                textfont=dict(size=10, color=C_TEXT),
            ))
            fig.update_layout(
                **chart_layout(550),
                xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                yaxis=dict(showgrid=False, tickfont=dict(size=10)),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

            df_em_risk = df_em[df_em["pct"] > 2]
            if not df_em_risk.empty:
                st.warning(f"⚠️ {len(df_em_risk)} emissores acima de 2% da carteira RF")
                disp = df_em_risk[["emissor","atual_brl","pct"]].copy()
                disp["atual_brl"] = df_em_risk["atual_brl"].apply(fmt_brl)
                disp["pct"]       = df_em_risk["pct"].apply(lambda v: fmt_pct(v, sign=False))
                st.dataframe(disp.rename(columns={"emissor":"Emissor","atual_brl":"Atual","pct":"% RF"}),
                             use_container_width=True)

    # ── Tab 2: Renda Variável ──
    with tabs[2]:
        df_rv = df[df["tipo"].isin(["RV LOCAL","FII"])]
        if df_rv.empty:
            st.info("Sem posições de renda variável local.")
        else:
            df_rv_g = df_rv.groupby("tipo")["atual_brl"].sum().reset_index()
            fig = px.pie(df_rv_g, values="atual_brl", names="tipo", hole=0.45,
                         color_discrete_sequence=[C_BLUE, C_GOLD])
            fig.update_traces(textposition="outside", textinfo="label+percent", textfont_size=12)
            fig.update_layout(**chart_layout(300), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            df_tick = df_rv[df_rv["ticker"].notna() & (df_rv["ticker"] != "")].copy()
            if not df_tick.empty:
                df_tick = df_tick.sort_values("variacao_pct")
                c_rv = [C_GREEN if v >= 0 else C_RED for v in df_tick["variacao_pct"]]
                fig2 = go.Figure(go.Bar(
                    x=df_tick["variacao_pct"], y=df_tick["ticker"],
                    orientation="h",
                    text=[fmt_pct(v) for v in df_tick["variacao_pct"]],
                    textposition="outside",
                    marker_color=c_rv,
                    textfont=dict(size=11),
                ))
                fig2.update_layout(
                    **chart_layout(300),
                    xaxis=dict(showticklabels=False, showgrid=False,
                               zeroline=True, zerolinecolor="#2A3A55"),
                    yaxis=dict(showgrid=False),
                    showlegend=False,
                )
                st.plotly_chart(fig2, use_container_width=True)

    # ── Tab 3: Internacional ──
    with tabs[3]:
        df_intl = df[df["moeda"] == "USD"]
        if df_intl.empty:
            st.info("Sem posições internacionais.")
        else:
            df_i_g = df_intl.groupby("tipo")["atual_brl"].sum().reset_index()
            total_i = df_i_g["atual_brl"].sum()
            df_i_g["pct"]   = df_i_g["atual_brl"] / total_i * 100
            df_i_g["label"] = df_i_g.apply(lambda r: f"{r['tipo']} ({r['pct']:.1f}%)", axis=1)
            fig = px.pie(df_i_g, values="atual_brl", names="label", hole=0.52,
                         color_discrete_sequence=CHART_COLORS)
            fig.update_traces(textposition="outside", textinfo="label", textfont_size=11)
            fig.update_layout(**chart_layout(340), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            df_i_perf = df_intl.groupby("tipo").agg(custo=("custo_brl","sum"), atual=("atual_brl","sum")).reset_index()
            df_i_perf["var"] = df_i_perf["atual"] - df_i_perf["custo"]
            df_i_perf["pct"] = df_i_perf["var"] / df_i_perf["custo"] * 100
            df_i_perf = df_i_perf.sort_values("pct")
            c_i = [C_GREEN if v >= 0 else C_RED for v in df_i_perf["pct"]]
            fig2 = go.Figure(go.Bar(
                x=df_i_perf["pct"], y=df_i_perf["tipo"],
                orientation="h",
                text=[fmt_pct(p) for p in df_i_perf["pct"]],
                textposition="outside",
                marker_color=c_i,
            ))
            fig2.update_layout(
                **chart_layout(280),
                xaxis=dict(showticklabels=False, showgrid=False,
                           zeroline=True, zerolinecolor="#2A3A55"),
                yaxis=dict(showgrid=False),
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)


# ── Gerenciar ──────────────────────────────────────────────────────────────────

def render_gerenciar(portfolio: dict, df: pd.DataFrame):
    st.markdown("## ➕ Gerenciar Posições")
    tab_add, tab_edit, tab_close, tab_import = st.tabs(
        ["Adicionar", "Editar", "Encerrar", "Importar JSON"])

    with tab_add:
        with st.form("form_add"):
            classe = st.selectbox("Classe", ["RENDA FIXA", "AÇÕES", "FII", "ETF GLOBAL", "CRIPTOATIVOS", "OUTROS"])
            tipo_opts = {
                "RENDA FIXA": ["CDI", "IPCA+", "PRÉ", "BONDS", "CREDITO PRIVADO", "MM"],
                "AÇÕES": ["RV LOCAL"], "FII": ["FII"],
                "ETF GLOBAL": ["INTERNACIONAL", "ALTERNATIVO"],
                "CRIPTOATIVOS": ["ALTERNATIVO"], "OUTROS": ["CDI"],
            }
            tipo = st.selectbox("Tipo", tipo_opts.get(classe, ["Outro"]))

            c1, c2 = st.columns(2)
            corretora = c1.text_input("Corretora")
            titulo    = c2.text_input("Título / Nome")

            c3, c4 = st.columns(2)
            emissor    = c3.text_input("Emissor")
            taxa       = c4.text_input("Taxa (ex: IPCA +8,5%)")

            c5, c6 = st.columns(2)
            ticker = c5.text_input("Ticker (ex: WEGE3)")
            moeda  = c6.selectbox("Moeda", ["BRL", "USD"])

            c7, c8 = st.columns(2)
            data_ap    = c7.text_input("Data (DD/MM/AAAA)")
            vencimento = c8.text_input("Vencimento (DD/MM/AAAA)")

            c9, c10 = st.columns(2)
            custo = c9.number_input("Custo (R$)", min_value=0.0, step=100.0)
            atual = c10.number_input("Valor Atual (R$)", min_value=0.0, step=100.0)

            if st.form_submit_button("✅ Adicionar", use_container_width=True, type="primary"):
                if not titulo or not corretora:
                    st.error("Preencha Corretora e Título.")
                else:
                    portfolio["positions"].append({
                        "id": str(uuid.uuid4())[:8],
                        "data_aplicacao": data_ap, "corretora": corretora,
                        "titulo": titulo, "emissor": emissor or titulo,
                        "taxa": taxa, "vencimento": vencimento,
                        "classe": classe, "tipo": tipo,
                        "ticker": ticker or None, "moeda": moeda,
                        "custo_brl": float(custo),
                        "atual_brl": float(atual) if atual else float(custo),
                        "status": "ativo",
                    })
                    portfolio["metadata"]["last_updated"] = date.today().isoformat()
                    save_portfolio(portfolio)
                    st.success(f"✅ '{titulo}' adicionado!")
                    st.rerun()

    with tab_edit:
        ativos = [p for p in portfolio["positions"] if p.get("status") == "ativo"]
        if not ativos:
            st.info("Nenhuma posição ativa.")
        else:
            opcoes = {f"{p['titulo']} | {p['corretora']}": p["id"] for p in ativos}
            sel    = st.selectbox("Posição", list(opcoes.keys()))
            pos    = next(p for p in portfolio["positions"] if p["id"] == opcoes[sel])

            c1, c2, c3 = st.columns(3)
            novo_atual = c1.number_input("Valor Atual (R$)", value=float(pos.get("atual_brl") or 0), step=100.0)
            nova_taxa  = c2.text_input("Taxa", value=pos.get("taxa") or "")
            novo_venc  = c3.text_input("Vencimento", value=pos.get("vencimento") or "")

            if st.button("💾 Salvar", use_container_width=True, type="primary"):
                for p in portfolio["positions"]:
                    if p["id"] == opcoes[sel]:
                        p["atual_brl"] = float(novo_atual)
                        if nova_taxa:  p["taxa"]      = nova_taxa
                        if novo_venc:  p["vencimento"] = novo_venc
                portfolio["metadata"]["last_updated"] = date.today().isoformat()
                save_portfolio(portfolio)
                st.success("✅ Salvo!")
                st.rerun()

    with tab_close:
        ativos = [p for p in portfolio["positions"] if p.get("status") == "ativo"]
        if not ativos:
            st.info("Nenhuma posição ativa.")
        else:
            opcoes = {f"{p['titulo']} | {p['corretora']}": p["id"] for p in ativos}
            sel    = st.selectbox("Posição a encerrar", list(opcoes.keys()), key="close_sel")
            pos    = next(p for p in portfolio["positions"] if p["id"] == opcoes[sel])

            st.info(f"**{pos['titulo']}** — Custo: {fmt_brl(pos.get('custo_brl'))} | Atual: {fmt_brl(pos.get('atual_brl'))}")
            resgate = st.number_input("Valor de resgate (R$)", value=float(pos.get("atual_brl") or 0), step=100.0)

            if st.button("🔴 Encerrar", type="primary", use_container_width=True):
                for p in portfolio["positions"]:
                    if p["id"] == opcoes[sel]:
                        p["status"]   = "encerrada"
                        p["atual_brl"] = float(resgate)
                portfolio["metadata"]["last_updated"] = date.today().isoformat()
                save_portfolio(portfolio)
                st.success("✅ Posição encerrada.")
                st.rerun()

    with tab_import:
        st.info("Faça upload de um JSON exportado para restaurar sua carteira.")
        uploaded = st.file_uploader("Arquivo JSON", type=["json"])
        if uploaded:
            try:
                data_imp = json.load(uploaded)
                if "positions" in data_imp and "metadata" in data_imp:
                    if st.button("✅ Confirmar importação", type="primary"):
                        save_portfolio(data_imp)
                        st.session_state["portfolio"] = data_imp
                        st.success("Carteira importada!")
                        st.rerun()
                else:
                    st.error("Arquivo inválido.")
            except Exception as e:
                st.error(f"Erro: {e}")


# ── Atualizar ──────────────────────────────────────────────────────────────────

def render_atualizar(portfolio: dict, df: pd.DataFrame):
    st.markdown("## 🔄 Atualizar Preços")
    usd = portfolio["metadata"].get("usd_brl_rate", 5.87)
    st.metric("Câmbio USD/BRL", f"R$ {usd:.4f}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🌎 Atualizar USD/BRL", use_container_width=True):
            with st.spinner("Buscando..."):
                novo = fetch_usd_brl()
            portfolio["metadata"]["usd_brl_rate"] = novo
            portfolio["metadata"]["last_updated"] = date.today().isoformat()
            save_portfolio(portfolio)
            st.success(f"USD/BRL: R$ {novo:.4f}")
            st.rerun()
    with c2:
        tickers_list = [(p["id"], p["ticker"], p["titulo"])
                        for p in portfolio["positions"]
                        if p.get("ticker") and p.get("status") == "ativo"]
        if st.button(f"📈 Atualizar {len(tickers_list)} tickers", use_container_width=True):
            if not tickers_list:
                st.warning("Nenhum ativo com ticker.")
            else:
                with st.spinner("Buscando preços..."):
                    prices = fetch_prices([t for _, t, _ in tickers_list])
                updated = 0
                for pos_id, ticker, titulo in tickers_list:
                    if ticker in prices and prices[ticker] > 0:
                        for p in portfolio["positions"]:
                            if p["id"] == pos_id:
                                p["preco_unit"] = prices[ticker]
                                if p.get("qtd"):
                                    p["atual_brl"] = prices[ticker] * p["qtd"]
                                updated += 1
                if updated:
                    portfolio["metadata"]["last_updated"] = date.today().isoformat()
                    save_portfolio(portfolio)
                    st.success(f"{updated} ativos atualizados.")
                else:
                    st.warning("Nenhum preço encontrado. Verifique os tickers.")

    st.markdown("---")
    df_tick = df[df["ticker"].notna() & (df["ticker"] != "") & (df["atual_brl"] > 0)][
        ["titulo", "ticker", "corretora", "tipo", "atual_brl"]].copy()
    df_tick["atual_brl"] = df_tick["atual_brl"].apply(fmt_brl)
    if not df_tick.empty:
        st.dataframe(df_tick.rename(columns={
            "titulo":"Título","ticker":"Ticker","corretora":"Corretora",
            "tipo":"Tipo","atual_brl":"Atual"}), use_container_width=True)


# ── Config ─────────────────────────────────────────────────────────────────────

def render_config(portfolio: dict):
    st.markdown("## ⚙️ Configurações")
    usd = portfolio["metadata"].get("usd_brl_rate", 5.87)
    novo_usd = st.number_input("USD/BRL", value=usd, min_value=0.01, step=0.01, format="%.4f")
    if st.button("Salvar câmbio", type="primary"):
        portfolio["metadata"]["usd_brl_rate"] = novo_usd
        save_portfolio(portfolio)
        st.success(f"Câmbio salvo: R$ {novo_usd:.4f}")

    st.markdown("---")
    total    = len(portfolio["positions"])
    ativos   = sum(1 for p in portfolio["positions"] if p.get("status") == "ativo")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total posições", total)
    c2.metric("Ativas", ativos)
    c3.metric("Encerradas", total - ativos)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    inject_css()
    portfolio = load_portfolio()
    df        = get_df(portfolio)
    page      = render_sidebar(portfolio)

    if   page == "🏠 Dashboard":  render_dashboard(portfolio, df)
    elif page == "💼 Posições":   render_posicoes(portfolio, df)
    elif page == "📈 Análises":   render_analises(portfolio, df)
    elif page == "➕ Gerenciar":  render_gerenciar(portfolio, df)
    elif page == "🔄 Atualizar":  render_atualizar(portfolio, df)
    elif page == "⚙️ Config":     render_config(portfolio)


if __name__ == "__main__":
    main()
