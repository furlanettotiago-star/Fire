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
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "portfolio.json")

# ── Data helpers ──────────────────────────────────────────────────────────────

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
        pass  # Streamlit Cloud may be read-only; user can export via button


def get_df(portfolio: dict) -> pd.DataFrame:
    rows = []
    usd_rate = portfolio["metadata"].get("usd_brl_rate", 5.87)
    for p in portfolio["positions"]:
        row = dict(p)
        # Normalise atual_brl for USD positions
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


# ── Price fetching ─────────────────────────────────────────────────────────────

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


# ── Formatting helpers ─────────────────────────────────────────────────────────

def fmt_brl(v: float) -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"R$ {sign}{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v: float) -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2f}%"


def color_delta(v: float) -> str:
    return "normal" if v >= 0 else "inverse"


# ── Sidebar ────────────────────────────────────────────────────────────────────

def render_sidebar(portfolio: dict):
    st.sidebar.title("📊 Carteira Tiago")
    st.sidebar.markdown("---")
    page = st.sidebar.radio(
        "Navegação",
        ["🏠 Dashboard", "💼 Posições", "📈 Análises", "➕ Gerenciar", "🔄 Atualizar Preços", "⚙️ Configurações"],
        label_visibility="collapsed",
    )
    st.sidebar.markdown("---")
    usd = portfolio["metadata"].get("usd_brl_rate", 5.87)
    st.sidebar.metric("USD/BRL", f"R$ {usd:.4f}")
    updated = portfolio["metadata"].get("last_updated", "—")
    st.sidebar.caption(f"Última atualização: {updated}")

    # Export button
    st.sidebar.markdown("---")
    st.sidebar.download_button(
        "💾 Exportar JSON",
        data=json.dumps(portfolio, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"carteira_{date.today().isoformat()}.json",
        mime="application/json",
        use_container_width=True,
    )
    return page


# ── Dashboard ──────────────────────────────────────────────────────────────────

def render_dashboard(portfolio: dict, df: pd.DataFrame):
    st.title("🏠 Dashboard")

    usd = portfolio["metadata"].get("usd_brl_rate", 5.87)
    total_custo = df["custo_brl"].sum()
    total_atual = df["atual_brl"].sum()
    total_var = total_atual - total_custo
    total_pct = (total_var / total_custo * 100) if total_custo else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Patrimônio Atual", fmt_brl(total_atual))
    c2.metric("📥 Custo Total", fmt_brl(total_custo))
    c3.metric("📈 Variação R$", fmt_brl(total_var), delta_color=color_delta(total_var))
    c4.metric("📊 Variação %", fmt_pct(total_pct), delta_color=color_delta(total_pct))

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Alocação por Classe")
        df_classe = df.groupby("classe")["atual_brl"].sum().reset_index()
        df_classe = df_classe[df_classe["atual_brl"] > 0].sort_values("atual_brl", ascending=False)
        fig = px.pie(
            df_classe,
            values="atual_brl",
            names="classe",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(showlegend=False, height=380, margin=dict(t=20, b=20, l=20, r=20),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font_color="#FAFAFA")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Alocação por Tipo")
        df_tipo = df.groupby("tipo")["atual_brl"].sum().reset_index()
        df_tipo = df_tipo[df_tipo["atual_brl"] > 0].sort_values("atual_brl", ascending=False)
        fig2 = px.bar(
            df_tipo,
            x="atual_brl",
            y="tipo",
            orientation="h",
            text_auto=".2s",
            color="atual_brl",
            color_continuous_scale="Blues",
        )
        fig2.update_layout(
            height=380,
            showlegend=False,
            coloraxis_showscale=False,
            yaxis_title="",
            xaxis_title="Valor Atual (R$)",
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#FAFAFA",
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Treemap por Classe › Tipo")
        df_tree = df.groupby(["classe", "tipo"])["atual_brl"].sum().reset_index()
        df_tree = df_tree[df_tree["atual_brl"] > 0]
        fig3 = px.treemap(
            df_tree,
            path=["classe", "tipo"],
            values="atual_brl",
            color="atual_brl",
            color_continuous_scale="Blues",
        )
        fig3.update_layout(height=380, margin=dict(t=20, b=0, l=0, r=0),
                           paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA")
        fig3.update_coloraxes(showscale=False)
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader("Performance por Classe")
        df_perf = df.groupby("classe").agg(
            custo=("custo_brl", "sum"),
            atual=("atual_brl", "sum"),
        ).reset_index()
        df_perf["variacao"] = df_perf["atual"] - df_perf["custo"]
        df_perf["pct"] = df_perf["variacao"] / df_perf["custo"] * 100
        df_perf = df_perf[df_perf["custo"] > 0]
        colors = ["#2ECC71" if v >= 0 else "#E74C3C" for v in df_perf["variacao"]]
        fig4 = go.Figure(go.Bar(
            x=df_perf["classe"],
            y=df_perf["variacao"],
            text=[fmt_pct(p) for p in df_perf["pct"]],
            textposition="outside",
            marker_color=colors,
        ))
        fig4.update_layout(
            height=380,
            yaxis_title="Variação (R$)",
            xaxis_title="",
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#FAFAFA",
        )
        st.plotly_chart(fig4, use_container_width=True)

    # Concentração por corretora
    st.markdown("---")
    st.subheader("Concentração por Corretora")
    df_corr = df.groupby("corretora")["atual_brl"].sum().reset_index().sort_values("atual_brl", ascending=False)
    df_corr = df_corr[df_corr["atual_brl"] > 0]
    df_corr["pct"] = df_corr["atual_brl"] / df_corr["atual_brl"].sum() * 100
    cols_corr = st.columns(len(df_corr))
    for i, row in df_corr.iterrows():
        idx = df_corr.index.get_loc(i)
        if idx < len(cols_corr):
            cols_corr[idx].metric(
                row["corretora"],
                fmt_brl(row["atual_brl"]),
                f"{row['pct']:.1f}%",
            )


# ── Posições ───────────────────────────────────────────────────────────────────

def render_posicoes(portfolio: dict, df: pd.DataFrame):
    st.title("💼 Posições")

    classes = ["Todas"] + sorted(df["classe"].unique().tolist())
    col_f1, col_f2, col_f3 = st.columns(3)
    classe_sel = col_f1.selectbox("Classe", classes)
    tipo_opts = ["Todos"] + sorted(df["tipo"].unique().tolist())
    tipo_sel = col_f2.selectbox("Tipo", tipo_opts)
    corr_opts = ["Todas"] + sorted(df["corretora"].unique().tolist())
    corr_sel = col_f3.selectbox("Corretora", corr_opts)

    filt = df.copy()
    if classe_sel != "Todas":
        filt = filt[filt["classe"] == classe_sel]
    if tipo_sel != "Todos":
        filt = filt[filt["tipo"] == tipo_sel]
    if corr_sel != "Todas":
        filt = filt[filt["corretora"] == corr_sel]

    show_cols = ["corretora", "titulo", "emissor", "taxa", "vencimento", "classe", "tipo",
                 "custo_brl", "atual_brl", "variacao_brl", "variacao_pct", "status"]
    show_cols = [c for c in show_cols if c in filt.columns]
    disp = filt[show_cols].copy()
    disp.columns = ["Corretora", "Título", "Emissor", "Taxa", "Vencimento", "Classe", "Tipo",
                    "Custo (R$)", "Atual (R$)", "Variação (R$)", "Variação (%)", "Status"][:len(show_cols)]

    def style_var(val):
        try:
            v = float(str(val).replace("R$ ", "").replace(",", ".").replace(".", "", val.count(".")-1))
            return "color: #2ECC71" if v >= 0 else "color: #E74C3C"
        except Exception:
            return ""

    st.dataframe(
        disp,
        use_container_width=True,
        height=500,
        column_config={
            "Custo (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Atual (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Variação (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Variação (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

    total_custo = filt["custo_brl"].sum()
    total_atual = filt["atual_brl"].sum()
    total_var = total_atual - total_custo
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Custo filtrado", fmt_brl(total_custo))
    c2.metric("Atual filtrado", fmt_brl(total_atual))
    c3.metric("Variação R$", fmt_brl(total_var), delta_color=color_delta(total_var))
    c4.metric("Qtd posições", len(filt))


# ── Análises ───────────────────────────────────────────────────────────────────

def render_analises(portfolio: dict, df: pd.DataFrame):
    st.title("📈 Análises")
    tabs = st.tabs(["Renda Fixa por Indexador", "Concentração Emissores", "Renda Variável", "Internacional"])

    with tabs[0]:
        df_fi = df[df["classe"] == "RENDA FIXA"]
        if df_fi.empty:
            st.info("Sem posições de renda fixa.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Por Indexador (Atual R$)")
                df_idx = df_fi.groupby("tipo")["atual_brl"].sum().reset_index().sort_values("atual_brl", ascending=False)
                fig = px.pie(df_idx, values="atual_brl", names="tipo", hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
                                  margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.subheader("Resumo por Indexador")
                df_sum = df_fi.groupby("tipo").agg(
                    n=("id", "count"),
                    custo=("custo_brl", "sum"),
                    atual=("atual_brl", "sum"),
                ).reset_index()
                df_sum["variacao"] = df_sum["atual"] - df_sum["custo"]
                df_sum["pct"] = df_sum["variacao"] / df_sum["custo"] * 100
                st.dataframe(
                    df_sum.rename(columns={"tipo": "Indexador", "n": "Qtd", "custo": "Custo",
                                           "atual": "Atual", "variacao": "Variação", "pct": "Variação %"}),
                    use_container_width=True,
                    column_config={
                        "Custo": st.column_config.NumberColumn(format="R$ %.0f"),
                        "Atual": st.column_config.NumberColumn(format="R$ %.0f"),
                        "Variação": st.column_config.NumberColumn(format="R$ %.0f"),
                        "Variação %": st.column_config.NumberColumn(format="%.2f%%"),
                    },
                )

    with tabs[1]:
        df_fi = df[df["classe"] == "RENDA FIXA"]
        df_em = df_fi.groupby("emissor")["atual_brl"].sum().reset_index().sort_values("atual_brl", ascending=False)
        df_em = df_em[df_em["atual_brl"] > 0].head(30)
        if df_em.empty:
            st.info("Sem emissores.")
        else:
            st.subheader("Top 30 Emissores (Renda Fixa)")
            usd = portfolio["metadata"].get("usd_brl_rate", 5.87)
            total_fi = df_fi["atual_brl"].sum()
            df_em["% Carteira"] = df_em["atual_brl"] / total_fi * 100
            fig = px.bar(df_em, x="emissor", y="atual_brl", text_auto=".2s",
                         color="atual_brl", color_continuous_scale="Blues")
            fig.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
                              xaxis_tickangle=-45, coloraxis_showscale=False,
                              xaxis_title="", yaxis_title="Atual (R$)",
                              margin=dict(t=10, b=80, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

            # Heatmap risk: posições com > 2% da carteira
            df_em_risk = df_em[df_em["% Carteira"] > 2]
            if not df_em_risk.empty:
                st.warning(f"⚠️ {len(df_em_risk)} emissores representam mais de 2% da carteira de renda fixa.")
                st.dataframe(df_em_risk[["emissor", "atual_brl", "% Carteira"]].rename(
                    columns={"emissor": "Emissor", "atual_brl": "Atual (R$)", "% Carteira": "% Carteira RF"}),
                    use_container_width=True,
                    column_config={
                        "Atual (R$)": st.column_config.NumberColumn(format="R$ %.0f"),
                        "% Carteira RF": st.column_config.NumberColumn(format="%.2f%%"),
                    })

    with tabs[2]:
        df_rv = df[df["classe"].isin(["AÇÕES", "FII"])]
        if df_rv.empty:
            st.info("Sem posições de renda variável local.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Ações x FII (Atual R$)")
                df_rv_g = df_rv.groupby("classe")["atual_brl"].sum().reset_index()
                fig = px.pie(df_rv_g, values="atual_brl", names="classe", hole=0.4,
                             color_discrete_sequence=["#3498DB", "#E67E22"])
                fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
                                  margin=dict(t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.subheader("Performance por Ativo")
                df_rv_s = df_rv.copy()
                df_rv_s["cor"] = df_rv_s["variacao_brl"].apply(lambda v: "#2ECC71" if v >= 0 else "#E74C3C")
                fig2 = go.Figure(go.Bar(
                    x=df_rv_s["titulo"],
                    y=df_rv_s["variacao_pct"],
                    marker_color=df_rv_s["cor"],
                    text=[fmt_pct(v) for v in df_rv_s["variacao_pct"]],
                    textposition="outside",
                ))
                fig2.update_layout(height=300, xaxis_tickangle=-30,
                                   paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
                                   margin=dict(t=20, b=40), yaxis_title="Variação %")
                st.plotly_chart(fig2, use_container_width=True)

    with tabs[3]:
        df_intl = df[df["moeda"] == "USD"]
        usd = portfolio["metadata"].get("usd_brl_rate", 5.87)
        if df_intl.empty:
            st.info("Sem posições internacionais.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Internacional por Tipo")
                df_i_g = df_intl.groupby("tipo")["atual_brl"].sum().reset_index()
                fig = px.pie(df_i_g, values="atual_brl", names="tipo", hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
                                  margin=dict(t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.subheader("Performance Internacional")
                df_i_perf = df_intl.groupby("tipo").agg(
                    custo=("custo_brl", "sum"), atual=("atual_brl", "sum")).reset_index()
                df_i_perf["var"] = df_i_perf["atual"] - df_i_perf["custo"]
                df_i_perf["pct"] = df_i_perf["var"] / df_i_perf["custo"] * 100
                colors = ["#2ECC71" if v >= 0 else "#E74C3C" for v in df_i_perf["var"]]
                fig2 = go.Figure(go.Bar(
                    x=df_i_perf["tipo"],
                    y=df_i_perf["pct"],
                    marker_color=colors,
                    text=[fmt_pct(p) for p in df_i_perf["pct"]],
                    textposition="outside",
                ))
                fig2.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", font_color="#FAFAFA",
                                   margin=dict(t=20, b=20), yaxis_title="Variação %")
                st.plotly_chart(fig2, use_container_width=True)


# ── Gerenciar ──────────────────────────────────────────────────────────────────

def render_gerenciar(portfolio: dict, df: pd.DataFrame):
    st.title("➕ Gerenciar Posições")
    tab_add, tab_edit, tab_close, tab_import = st.tabs(
        ["Adicionar", "Editar Posição", "Encerrar Posição", "Importar JSON"])

    with tab_add:
        st.subheader("Nova Posição")
        with st.form("form_add"):
            c1, c2 = st.columns(2)
            classe = c1.selectbox("Classe", ["RENDA FIXA", "AÇÕES", "FII", "ETF GLOBAL", "CRIPTOATIVOS"])
            tipo_opts = {
                "RENDA FIXA": ["CDI", "IPCA+", "PRÉ", "BONDS", "CREDITO PRIVADO"],
                "AÇÕES": ["RV LOCAL"],
                "FII": ["FII"],
                "ETF GLOBAL": ["INTERNACIONAL", "ALTERNATIVO"],
                "CRIPTOATIVOS": ["ALTERNATIVO"],
            }
            tipo = c2.selectbox("Tipo", tipo_opts.get(classe, ["Outro"]))

            c3, c4 = st.columns(2)
            corretora = c3.text_input("Corretora")
            titulo = c4.text_input("Título / Nome")

            c5, c6 = st.columns(2)
            emissor = c5.text_input("Emissor")
            taxa = c6.text_input("Taxa (ex: IPCA + 8,5%)")

            c7, c8 = st.columns(2)
            ticker = c7.text_input("Ticker (ex: WEGE3.SA) — deixe vazio se n/a")
            moeda = c8.selectbox("Moeda", ["BRL", "USD"])

            c9, c10, c11 = st.columns(3)
            data_ap = c9.text_input("Data Aplicação (DD/MM/AAAA)")
            vencimento = c10.text_input("Vencimento (DD/MM/AAAA ou n/a)")
            custo = c11.number_input("Custo (R$)", min_value=0.0, step=100.0)

            atual = st.number_input("Valor Atual (R$)", min_value=0.0, step=100.0)

            submitted = st.form_submit_button("✅ Adicionar", use_container_width=True)
            if submitted:
                if not titulo or not corretora:
                    st.error("Preencha pelo menos Corretora e Título.")
                else:
                    new = {
                        "id": str(uuid.uuid4())[:8],
                        "data_aplicacao": data_ap,
                        "corretora": corretora,
                        "titulo": titulo,
                        "emissor": emissor or titulo,
                        "taxa": taxa,
                        "vencimento": vencimento,
                        "classe": classe,
                        "tipo": tipo,
                        "ticker": ticker or None,
                        "moeda": moeda,
                        "custo_brl": float(custo),
                        "atual_brl": float(atual) if atual else float(custo),
                        "status": "ativo",
                    }
                    portfolio["positions"].append(new)
                    portfolio["metadata"]["last_updated"] = date.today().isoformat()
                    save_portfolio(portfolio)
                    st.success(f"✅ Posição '{titulo}' adicionada!")
                    st.rerun()

    with tab_edit:
        st.subheader("Editar Valor Atual")
        ativos = [p for p in portfolio["positions"] if p.get("status") == "ativo"]
        if not ativos:
            st.info("Nenhuma posição ativa.")
        else:
            opcoes = {f"{p['titulo']} | {p['corretora']} | {p.get('tipo','')}": p["id"] for p in ativos}
            sel = st.selectbox("Selecione a posição", list(opcoes.keys()))
            pos_id = opcoes[sel]
            pos = next(p for p in portfolio["positions"] if p["id"] == pos_id)

            c1, c2, c3 = st.columns(3)
            novo_atual = c1.number_input("Novo Valor Atual (R$)", value=float(pos.get("atual_brl") or 0), step=100.0)
            nova_taxa = c2.text_input("Atualizar Taxa", value=pos.get("taxa") or "")
            novo_venc = c3.text_input("Atualizar Vencimento", value=pos.get("vencimento") or "")

            if st.button("💾 Salvar alterações", use_container_width=True):
                for p in portfolio["positions"]:
                    if p["id"] == pos_id:
                        p["atual_brl"] = float(novo_atual)
                        if nova_taxa:
                            p["taxa"] = nova_taxa
                        if novo_venc:
                            p["vencimento"] = novo_venc
                portfolio["metadata"]["last_updated"] = date.today().isoformat()
                save_portfolio(portfolio)
                st.success("✅ Posição atualizada!")
                st.rerun()

    with tab_close:
        st.subheader("Encerrar Posição")
        ativos = [p for p in portfolio["positions"] if p.get("status") == "ativo"]
        if not ativos:
            st.info("Nenhuma posição ativa.")
        else:
            opcoes = {f"{p['titulo']} | {p['corretora']} | {p.get('tipo','')}": p["id"] for p in ativos}
            sel = st.selectbox("Selecione a posição a encerrar", list(opcoes.keys()), key="close_sel")
            pos_id = opcoes[sel]
            pos = next(p for p in portfolio["positions"] if p["id"] == pos_id)

            st.info(
                f"**{pos['titulo']}** | Corretora: {pos['corretora']} | "
                f"Custo: {fmt_brl(pos.get('custo_brl'))} | "
                f"Atual: {fmt_brl(pos.get('atual_brl'))}"
            )

            valor_resgate = st.number_input("Valor de resgate/liquidação (R$)",
                                            value=float(pos.get("atual_brl") or 0), step=100.0, key="resgate")
            if st.button("🔴 Encerrar posição", type="primary", use_container_width=True):
                for p in portfolio["positions"]:
                    if p["id"] == pos_id:
                        p["status"] = "encerrada"
                        p["atual_brl"] = float(valor_resgate)
                portfolio["metadata"]["last_updated"] = date.today().isoformat()
                save_portfolio(portfolio)
                st.success(f"✅ Posição '{pos['titulo']}' encerrada.")
                st.rerun()

    with tab_import:
        st.subheader("Importar JSON")
        st.info("Faça upload de um arquivo JSON exportado anteriormente para restaurar/atualizar sua carteira.")
        uploaded = st.file_uploader("Selecione o arquivo JSON", type=["json"])
        if uploaded:
            try:
                data_imported = json.load(uploaded)
                if "positions" in data_imported and "metadata" in data_imported:
                    if st.button("✅ Confirmar importação", type="primary"):
                        save_portfolio(data_imported)
                        st.session_state["portfolio"] = data_imported
                        st.success("Carteira importada com sucesso!")
                        st.rerun()
                else:
                    st.error("Arquivo inválido. Certifique-se de usar um JSON exportado deste app.")
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")


# ── Atualizar Preços ───────────────────────────────────────────────────────────

def render_atualizar(portfolio: dict, df: pd.DataFrame):
    st.title("🔄 Atualizar Preços")
    st.markdown(
        "Busca cotações automáticas via **Yahoo Finance** para ativos com ticker configurado, "
        "e a taxa de câmbio USD/BRL em tempo real."
    )

    usd = portfolio["metadata"].get("usd_brl_rate", 5.87)
    st.metric("Câmbio USD/BRL atual", f"R$ {usd:.4f}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🌎 Atualizar USD/BRL agora", use_container_width=True):
            with st.spinner("Buscando câmbio..."):
                novo_usd = fetch_usd_brl()
            portfolio["metadata"]["usd_brl_rate"] = novo_usd
            portfolio["metadata"]["last_updated"] = date.today().isoformat()
            save_portfolio(portfolio)
            st.success(f"USD/BRL atualizado: R$ {novo_usd:.4f}")
            st.rerun()

    with col2:
        tickers_with_id = [
            (p["id"], p["ticker"], p["titulo"])
            for p in portfolio["positions"]
            if p.get("ticker") and p.get("status") == "ativo"
        ]
        if st.button(f"📈 Atualizar {len(tickers_with_id)} ativos com ticker", use_container_width=True):
            if not tickers_with_id:
                st.warning("Nenhum ativo com ticker configurado.")
            else:
                tickers = [t for _, t, _ in tickers_with_id]
                with st.spinner(f"Buscando preços de {len(tickers)} ativos..."):
                    prices = fetch_prices(tickers)

                updated = 0
                log = []
                for pos_id, ticker, titulo in tickers_with_id:
                    if ticker in prices and prices[ticker] > 0:
                        for p in portfolio["positions"]:
                            if p["id"] == pos_id:
                                # For BR tickers, multiply price * quantity if qty not stored, else just store price
                                # Since we store total values, we approximate by scaling
                                old_atual = p.get("atual_brl") or p.get("custo_brl") or 0
                                # yfinance returns price per unit; we need total
                                # We'll store the new unit price and flag for manual review
                                # For simplicity, update atual_brl proportionally if we can
                                p["preco_unit"] = prices[ticker]
                                if p.get("qtd"):
                                    p["atual_brl"] = prices[ticker] * p["qtd"]
                                log.append(f"✅ {titulo}: R$ {prices[ticker]:.2f}")
                                updated += 1

                if updated:
                    portfolio["metadata"]["last_updated"] = date.today().isoformat()
                    save_portfolio(portfolio)
                    st.success(f"{updated} ativos atualizados.")
                    st.write("\n".join(log))
                else:
                    st.warning("Nenhum preço encontrado. Verifique os tickers.")

    st.markdown("---")
    st.subheader("Ativos com ticker configurado")
    df_tick = df[df["ticker"].notna() & (df["atual_brl"] > 0)][["titulo", "ticker", "corretora", "classe", "atual_brl"]]
    if df_tick.empty:
        st.info("Nenhum ativo com ticker.")
    else:
        st.dataframe(df_tick.rename(columns={
            "titulo": "Título", "ticker": "Ticker", "corretora": "Corretora",
            "classe": "Classe", "atual_brl": "Atual (R$)"}),
            use_container_width=True,
            column_config={"Atual (R$)": st.column_config.NumberColumn(format="R$ %.2f")})

    st.markdown("---")
    st.subheader("Atualização manual em lote (Renda Fixa)")
    st.info(
        "Para posições de renda fixa sem ticker, use a aba **Gerenciar → Editar Posição** "
        "para atualizar o valor atual individualmente, ou exporte o JSON, edite e reimporte."
    )


# ── Configurações ──────────────────────────────────────────────────────────────

def render_config(portfolio: dict):
    st.title("⚙️ Configurações")

    st.subheader("Taxa de câmbio USD/BRL")
    usd = portfolio["metadata"].get("usd_brl_rate", 5.87)
    novo_usd = st.number_input("USD/BRL", value=usd, min_value=0.01, step=0.01, format="%.4f")
    if st.button("Salvar câmbio"):
        portfolio["metadata"]["usd_brl_rate"] = novo_usd
        save_portfolio(portfolio)
        st.success(f"Câmbio salvo: R$ {novo_usd:.4f}")

    st.markdown("---")
    st.subheader("Estatísticas da carteira")
    total = len(portfolio["positions"])
    ativos = sum(1 for p in portfolio["positions"] if p.get("status") == "ativo")
    encerradas = total - ativos
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de posições", total)
    c2.metric("Posições ativas", ativos)
    c3.metric("Encerradas", encerradas)

    st.markdown("---")
    st.subheader("Classes e Tipos cadastrados")
    classes = sorted(set(p.get("classe", "") for p in portfolio["positions"]))
    tipos = sorted(set(p.get("tipo", "") for p in portfolio["positions"]))
    c1, c2 = st.columns(2)
    c1.write("**Classes:**")
    for c in classes:
        c1.write(f"- {c}")
    c2.write("**Tipos:**")
    for t in tipos:
        c2.write(f"- {t}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    portfolio = load_portfolio()
    df = get_df(portfolio)

    page = render_sidebar(portfolio)

    if page == "🏠 Dashboard":
        render_dashboard(portfolio, df)
    elif page == "💼 Posições":
        render_posicoes(portfolio, df)
    elif page == "📈 Análises":
        render_analises(portfolio, df)
    elif page == "➕ Gerenciar":
        render_gerenciar(portfolio, df)
    elif page == "🔄 Atualizar Preços":
        render_atualizar(portfolio, df)
    elif page == "⚙️ Configurações":
        render_config(portfolio)


if __name__ == "__main__":
    main()
