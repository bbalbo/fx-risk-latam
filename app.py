import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from scipy.stats import gaussian_kde

from src.returns import load_rates, log_returns, return_summary
from src.volatility import (rolling_volatility, ewma_volatility, volatility_summary,
                            WINDOW_30D, WINDOW_90D, WINDOW_252D, EWMA_LAMBDA)
from src.correlation import full_correlation, rolling_correlation
from src.var import var_summary, historical_var, expected_shortfall
from src.stress import full_stress_table
from src.anomalies import anomaly_report

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
st.set_page_config(page_title="FX Risk LatAm", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #0f1117; border-right: 1px solid #2a2a2a; }
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
[data-testid="stSidebar"] hr { border-color: #2a2a2a; }
.block-container { padding-top: 1.5rem; padding-bottom: 1rem; max-width: 1200px; }
h1 {
    font-size: 1.3rem !important; font-weight: 600 !important;
    letter-spacing: 0.06em; text-transform: uppercase; color: #0f1117 !important;
    border-bottom: 2px solid #0f1117; padding-bottom: 0.4rem; margin-bottom: 1rem !important;
}
h2, h3 {
    font-size: 0.9rem !important; font-weight: 600 !important;
    letter-spacing: 0.05em; text-transform: uppercase; color: #444 !important; margin-top: 1.2rem !important;
}
[data-testid="metric-container"] {
    background: #f4f4f4; border: 1px solid #e0e0e0; border-radius: 2px; padding: 0.5rem 0.8rem;
}
[data-testid="metric-container"] label { font-size: 0.7rem !important; letter-spacing: 0.06em; text-transform: uppercase; color: #777 !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 700 !important; }
.stCaption { font-size: 0.7rem !important; color: #999 !important; letter-spacing: 0.03em; }
hr { border-color: #e8e8e8; margin: 0.8rem 0; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------
CURRENCY_LABELS = {
    "CLP": "CLP — Peso Chileno", "BRL": "BRL — Real Brasileño",
    "ARS": "ARS — Peso Argentino", "MXN": "MXN — Peso Mexicano",
    "COP": "COP — Peso Colombiano", "PEN": "PEN — Sol Peruano",
    "VES": "VES — Bolívar Venezolano", "EUR": "EUR — Euro",
    "CNY": "CNY — Yuan Chino", "JPY": "JPY — Yen Japonés",
    "ORO_USD": "XAU — Oro (USD/oz)",
}
LATAM = ["CLP", "BRL", "ARS", "MXN", "COP", "PEN", "VES"]
SHORT_LABELS = {
    "CLP": "CLP · Peso Chileno", "BRL": "BRL · Real",
    "ARS": "ARS · Peso Arg.", "MXN": "MXN · Peso Mex.",
    "COP": "COP · Peso Col.", "PEN": "PEN · Sol",
    "VES": "VES · Bolívar", "EUR": "EUR · Euro",
    "CNY": "CNY · Yuan", "JPY": "JPY · Yen",
    "ORO_USD": "XAU · Oro",
}
CHART_COLORS = ["#1f4e79","#c0392b","#27ae60","#d35400","#8e44ad",
                "#2980b9","#16a085","#f39c12","#2c3e50","#7f8c8d","#e74c3c"]
MONTHS_ES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

BASE_LAYOUT = dict(
    plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
    font=dict(family="monospace", size=11),
    margin=dict(l=0, r=0, t=10, b=0),
)

def L(**kwargs):
    """Merge BASE_LAYOUT with extra kwargs."""
    return {**BASE_LAYOUT, **kwargs}

# -------------------------------------------------------------------
# Data
# -------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_data():
    rates = load_rates()
    returns = log_returns(rates)
    return rates, returns

@st.cache_data(ttl=3600)
def monthly_returns_pivot(_returns, currency):
    """Pivot of monthly log returns: rows=year, cols=month."""
    monthly = _returns[[currency]].resample("ME").sum() * 100
    monthly["year"]  = monthly.index.year
    monthly["month"] = monthly.index.month
    return monthly.pivot(index="year", columns="month", values=currency)

# -------------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------------
st.sidebar.markdown("## FX RISK LATAM")
st.sidebar.markdown(
    "<span style='font-size:0.7rem;color:#777;letter-spacing:0.05em'>PANEL DE RIESGO CAMBIARIO</span>",
    unsafe_allow_html=True)
st.sidebar.divider()

page = st.sidebar.radio("Navegación",
    ["Panorama Regional","Volatilidad","Correlaciones",
     "VaR & Riesgo de Cola","Stress Testing","Anomalías"],
    label_visibility="collapsed")

st.sidebar.divider()
st.sidebar.markdown(
    "<span style='font-size:0.68rem;color:#555'>Frankfurter API · Base USD · 2018–hoy</span>",
    unsafe_allow_html=True)
st.sidebar.markdown(
    "<span style='font-size:0.62rem;color:#444'>Brooks, <i>Introductory Econometrics "
    "for Finance</i>, 2ª ed., Cambridge UP, 2008</span>",
    unsafe_allow_html=True)

st.sidebar.divider()
st.sidebar.markdown(
    "<span style='font-size:0.65rem;color:#777;letter-spacing:0.04em'>REFERENCIA</span>",
    unsafe_allow_html=True)
_ref = {
    "CLP":"Peso Chileno","BRL":"Real Brasileño","ARS":"Peso Argentino",
    "MXN":"Peso Mexicano","COP":"Peso Colombiano","PEN":"Sol Peruano",
    "VES":"Bolívar Venezolano","EUR":"Euro","CNY":"Yuan Chino",
    "JPY":"Yen Japonés","XAU":"Oro (USD/oz)",
}
st.sidebar.markdown(
    "".join(
        f"<div style='font-size:0.62rem;color:#aaa;line-height:1.7'>"
        f"<span style='color:#e0e0e0;font-weight:600'>{k}</span> {v}</div>"
        for k, v in _ref.items()
    ),
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# Load
# -------------------------------------------------------------------
try:
    rates, returns = get_data()
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.info("Corre `python -m src.extraction` primero.")
    st.stop()

last_date = returns.index[-1].strftime("%d %b %Y")
n_days    = len(returns)

# ===================================================================
# PAGE 1: Panorama Regional
# ===================================================================
if page == "Panorama Regional":
    st.title("Panorama Regional")
    st.caption(f"Último dato: {last_date}  ·  {n_days} días de trading  ·  11 activos")

    summary  = return_summary(returns)
    vol_snap = volatility_summary(returns)

    overview = pd.DataFrame({
        "Ret. medio diario (%)": (summary["mean"] * 100).round(4),
        "Vol anualizada (%)":    (summary["annualized_vol"] * 100).round(2),
        "Vol 30d (%)":           (vol_snap["vol_30d"] * 100).round(2),
        "Mín diario (%)":        (summary["min"] * 100).round(2),
        "Máx diario (%)":        (summary["max"] * 100).round(2),
        "Curtosis":              summary["kurtosis"].round(2),
    })
    overview.index = [CURRENCY_LABELS.get(c, c) for c in overview.index]
    st.dataframe(
        overview.style
            .background_gradient(subset=["Vol 30d (%)"], cmap="YlOrRd")
            .background_gradient(subset=["Vol anualizada (%)"], cmap="YlOrRd")
            .format("{:.2f}"),
        use_container_width=True, height=430)
    st.caption("r_t = ln(p_t/p_{t-1}) · Curtosis normal=3; exceso indica fat tails")

    st.divider()

    # --- Tipo de cambio normalizado ---
    st.subheader("Tipo de Cambio vs USD")
    col1, col2 = st.columns([3, 1])
    with col1:
        sel_tc = st.multiselect("Monedas", list(rates.columns),
                                default=["CLP","BRL","MXN","COP","PEN"],
                                format_func=lambda c: c, key="tc")
    with col2:
        normalize = st.toggle("Base 100", value=True)
    if sel_tc:
        df_plot = rates[sel_tc] / rates[sel_tc].iloc[0] * 100 if normalize else rates[sel_tc]
        fig = px.line(df_plot, color_discrete_sequence=CHART_COLORS,
                      labels={"value": "Índice (base 100)" if normalize else "Unidades/USD", "date":"","variable":""})
        fig.update_layout(**L(hovermode="x unified"), legend=dict(orientation="h",y=-0.15,x=0),
                          xaxis=dict(showgrid=False,zeroline=False),
                          yaxis=dict(gridcolor="#f0f0f0",zeroline=False))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Positivo = depreciación (más unidades locales por USD).")

    st.divider()

    # --- Violin: distribución de retornos diarios ---
    st.subheader("Distribución de Retornos Diarios por Moneda")
    sel_viol = st.multiselect("Monedas", list(returns.columns), default=LATAM,
                              format_func=lambda c: c, key="viol")
    if sel_viol:
        # Exclude ARS/VES from default view as they distort scale
        fig_v = go.Figure()
        for i, cur in enumerate(sel_viol):
            r = returns[cur] * 100
            # clip at ±5% for readability (ARS/VES are outliers)
            r_clip = r.clip(-5, 5)
            fig_v.add_trace(go.Violin(
                y=r_clip, name=cur,
                box_visible=True, meanline_visible=True,
                fillcolor=CHART_COLORS[i % len(CHART_COLORS)],
                line_color="#333", opacity=0.75,
                points=False,
            ))
        fig_v.update_layout(**L(hovermode="closest"),
                            yaxis_title="Retorno diario (%)",
                            yaxis=dict(gridcolor="#f0f0f0", zeroline=True, zerolinecolor="#ccc"),
                            xaxis=dict(showgrid=False),
                            showlegend=False)
        fig_v.add_hline(y=0, line_color="#bbb", line_dash="dot")
        st.plotly_chart(fig_v, use_container_width=True)
        st.caption("Retornos recortados a ±5% para visibilidad. Caja=IQR, línea=mediana, punto=media. ARS y VES tienen colas mucho más extremas.")

    st.divider()

    # --- Monthly returns heatmap ---
    st.subheader("Retornos Mensuales — Mapa de Calor")
    cur_hm = st.selectbox("Moneda", list(returns.columns),
                          format_func=lambda c: c, key="hmap")
    pivot = monthly_returns_pivot(returns, cur_hm)
    pivot.columns = [MONTHS_ES[m-1] for m in pivot.columns]

    max_abs = float(np.nanpercentile(np.abs(pivot.values), 95))
    fig_hm = go.Figure(go.Heatmap(
        z=pivot.values, x=list(pivot.columns), y=[str(y) for y in pivot.index],
        colorscale="RdYlGn_r", zmid=0, zmin=-max_abs, zmax=max_abs,
        text=np.where(np.isnan(pivot.values), "",
                      np.char.add(np.round(pivot.values, 1).astype(str), "%")),
        texttemplate="%{text}", textfont={"size": 10, "family": "monospace"},
        hovertemplate="<b>%{y} %{x}</b>: %{z:.2f}%<extra></extra>",
        colorbar=dict(title="%", tickfont=dict(family="monospace", size=10)),
    ))
    fig_hm.update_layout(**L(), height=300,
                         xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
    st.plotly_chart(fig_hm, use_container_width=True)
    st.caption("Cambio mensual en la tasa de cambio vs USD (retorno log acumulado). Rojo = tasa subió = moneda local se depreció. Verde = tasa bajó = moneda local se apreció. Para ARS, el predominio rojo refleja la depreciación sostenida del período.")

    st.divider()

    # --- Volatility clustering ---
    st.subheader("Clustering de Volatilidad")
    clust_cur = st.selectbox("Moneda", list(returns.columns),
                             format_func=lambda c: c, key="clust")
    r2 = (returns[clust_cur] ** 2) * 100
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(x=r2.index, y=r2.values, mode="lines",
                               fill="tozeroy", fillcolor="rgba(31,78,121,0.15)",
                               line=dict(color="#1f4e79", width=0.8), name="r²"))
    fig_c.update_layout(**L(hovermode="x unified"),
                        yaxis_title="Retorno² (%²)",
                        xaxis=dict(showgrid=False,zeroline=False),
                        yaxis=dict(gridcolor="#f0f0f0",zeroline=False),
                        showlegend=False)
    st.plotly_chart(fig_c, use_container_width=True)
    st.caption("r²_t como proxy de volatilidad diaria. Bursts = volatility clustering: la varianza no es constante.")

# ===================================================================
# PAGE 2: Volatilidad
# ===================================================================
elif page == "Volatilidad":
    st.title("Volatilidad")
    st.caption("Desviación estándar de retornos log diarios · anualizada ×√252")

    col1, col2, col3 = st.columns([3,1,1])
    with col1:
        selected = st.multiselect("Monedas", list(returns.columns), default=LATAM,
                                  format_func=lambda c: c)
    with col2:
        modelo = st.radio("Modelo", ["Rolling","EWMA"], horizontal=True)
    with col3:
        window = st.radio("Ventana", [WINDOW_30D, WINDOW_90D, WINDOW_252D],
                          format_func=lambda v: {30:"30d",90:"90d",252:"252d"}[v],
                          horizontal=True, disabled=(modelo=="EWMA"))

    if selected:
        if modelo == "Rolling":
            vol  = rolling_volatility(returns[selected], window=window) * 100
            note = (f"Vol histórica: σ_t = std(r_{{t-{window},...,t}}) ×√252 · "
                    "Efecto fantasma: un shock afecta la vol toda la ventana")
        else:
            vol  = ewma_volatility(returns[selected], lam=EWMA_LAMBDA) * 100
            note = (f"EWMA: σ²_t = λ·σ²_{{t-1}} + (1-λ)·r²_{{t-1}} · λ={EWMA_LAMBDA} (RiskMetrics) · "
                    "Sin efecto fantasma, decay exponencial")

        fig = px.line(vol, color_discrete_sequence=CHART_COLORS,
                      labels={"value":"Vol anualizada (%)","date":"","variable":""})
        fig.update_layout(**L(hovermode="x unified"), legend=dict(orientation="h",y=-0.15,x=0),
                          xaxis=dict(showgrid=False,zeroline=False),
                          yaxis=dict(gridcolor="#f0f0f0",zeroline=False))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(note)

        st.divider()

        # --- KDE ridge plot: comparar distribución de vol cross-currency ---
        st.subheader("Densidad de Volatilidad por Moneda (KDE)")
        vol_30 = rolling_volatility(returns[selected], window=WINDOW_30D).dropna() * 100
        x_max  = float(vol_30.quantile(0.99).max())
        x_range = np.linspace(0, x_max, 300)
        fig_kde = go.Figure()
        for i, cur in enumerate(selected):
            series = vol_30[cur].dropna().values
            if len(series) < 10: continue
            kde = gaussian_kde(series, bw_method=0.3)
            color = CHART_COLORS[i % len(CHART_COLORS)]
            h = color.lstrip("#")
            rc2, gc2, bc2 = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
            fig_kde.add_trace(go.Scatter(
                x=x_range, y=kde(x_range), mode="lines", name=cur,
                fill="tozeroy", fillcolor=f"rgba({rc2},{gc2},{bc2},0.12)",
                line=dict(color=color, width=1.5),
            ))
        fig_kde.update_layout(**L(hovermode="x"), legend=dict(orientation="h",y=-0.15,x=0),
                              xaxis=dict(title="Vol anualizada (%)", showgrid=False, zeroline=False),
                              yaxis=dict(title="Densidad", gridcolor="#f0f0f0", zeroline=False))
        st.plotly_chart(fig_kde, use_container_width=True)
        st.caption("KDE (Kernel Density Estimation) de la volatilidad rolling 30d. Muestra la forma completa de la distribución de volatilidad histórica de cada moneda.")

        st.divider()

        # --- Rolling vs EWMA comparison ---
        st.subheader("Rolling vs EWMA — Comparación Directa")
        cur_comp = st.selectbox("Moneda", selected, format_func=lambda c: c, key="comp")
        w_comp   = st.radio("Ventana rolling", [WINDOW_30D,WINDOW_90D], horizontal=True,
                            format_func=lambda v:{30:"30d",90:"90d"}[v], key="wcomp")
        roll_c = rolling_volatility(returns[[cur_comp]], window=w_comp)[cur_comp] * 100
        ewma_c = ewma_volatility(returns[[cur_comp]], lam=EWMA_LAMBDA)[cur_comp] * 100
        diff_c = ewma_c - roll_c

        fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7,0.3],
                             vertical_spacing=0.04)
        fig2.add_trace(go.Scatter(x=roll_c.index, y=roll_c.values, name=f"Rolling {w_comp}d",
                                  line=dict(color="#1f4e79", width=1.2)), row=1, col=1)
        fig2.add_trace(go.Scatter(x=ewma_c.index, y=ewma_c.values, name=f"EWMA λ={EWMA_LAMBDA}",
                                  line=dict(color="#c0392b", width=1.2)), row=1, col=1)
        fig2.add_trace(go.Bar(x=diff_c.index, y=diff_c.values, name="EWMA − Rolling",
                              marker_color=np.where(diff_c > 0, "#c0392b", "#27ae60"),
                              showlegend=False), row=2, col=1)
        fig2.add_hline(y=0, line_color="#ccc", line_dash="dot", row=2, col=1)
        fig2.update_layout(**L(hovermode="x unified"), legend=dict(orientation="h",y=-0.08,x=0),
                           yaxis=dict(title="Vol (%)", gridcolor="#f0f0f0", zeroline=False),
                           yaxis2=dict(title="Diferencia", gridcolor="#f0f0f0", zeroline=False),
                           xaxis2=dict(showgrid=False, zeroline=False),
                           xaxis=dict(showgrid=False, zeroline=False), height=420)
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Panel inferior: diferencia EWMA−Rolling. Rojo=EWMA percibe más riesgo; verde=Rolling más alto (efecto fantasma activo).")

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Snapshot Actual")
            snap = volatility_summary(returns[selected]) * 100
            snap.index = [CURRENCY_LABELS.get(c,c) for c in snap.index]
            snap.columns = ["30d","90d","252d"]
            st.dataframe(snap.style.background_gradient(cmap="YlOrRd").format("{:.2f}%"),
                         use_container_width=True)
        with col_b:
            st.subheader("Señal de Estrés (Vol 30d / Vol 252d)")
            snap_raw = volatility_summary(returns[selected])
            ratio = (snap_raw["vol_30d"] / snap_raw["vol_252d"]).rename("ratio")
            ratio.index = [CURRENCY_LABELS.get(c,c) for c in ratio.index]
            ratio_df = ratio.sort_values(ascending=False).reset_index()
            ratio_df.columns = ["Moneda","ratio"]
            fig3 = px.bar(ratio_df, x="Moneda", y="ratio", color="ratio",
                          color_continuous_scale="RdYlGn_r", labels={"ratio":"ratio"})
            fig3.add_hline(y=1.0, line_dash="dash", line_color="#999",
                           annotation_text="neutral", annotation_font_size=10)
            fig3.update_layout(**L(), coloraxis_showscale=False, xaxis_tickangle=-30,
                               xaxis=dict(showgrid=False,zeroline=False),
                               yaxis=dict(gridcolor="#f0f0f0",zeroline=False))
            st.plotly_chart(fig3, use_container_width=True)
            st.caption("Ratio > 1: moneda más volátil que su promedio anual.")

        st.divider()

        # --- ACF of squared returns ---
        st.subheader("Efectos ARCH — Autocorrelación de r²")
        arch_cur = st.selectbox("Moneda", selected, format_func=lambda c: c, key="arch")
        max_lags = 20
        sq_ret   = returns[arch_cur] ** 2
        acf_vals = [sq_ret.autocorr(lag=k) for k in range(1, max_lags+1)]
        conf     = 1.96 / np.sqrt(len(sq_ret))

        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=list(range(1, max_lags+1)), y=acf_vals,
                              marker_color=["#c0392b" if abs(v) > conf else "#1f4e79" for v in acf_vals]))
        fig4.add_hline(y=conf, line_dash="dash", line_color="#999",
                       annotation_text="95% CI", annotation_font_size=9)
        fig4.add_hline(y=-conf, line_dash="dash", line_color="#999")
        fig4.update_layout(**L(), xaxis_title="Lag (días)", showlegend=False,
                           xaxis=dict(showgrid=False,zeroline=False),
                           yaxis=dict(gridcolor="#f0f0f0",zeroline=False, title="Autocorrelación"))
        st.plotly_chart(fig4, use_container_width=True)
        st.caption("Barras rojas superan 95% CI. ACF(r²) significativa = efectos ARCH: la varianza condicional varía en el tiempo.")

# ===================================================================
# PAGE 3: Correlaciones
# ===================================================================
elif page == "Correlaciones":
    st.title("Correlaciones")
    st.caption("Calculadas sobre retornos log diarios · matriz positiva semi-definida por construcción")

    tab1, tab2, tab3 = st.tabs(["Heatmap período completo", "Dispersión por par", "Móvil vs CLP"])

    with tab1:
        method = st.radio("Método", ["pearson","spearman"], horizontal=True)
        corr   = full_correlation(returns, method=method)
        labels = [CURRENCY_LABELS.get(c,c) for c in corr.columns]
        fig = go.Figure(go.Heatmap(
            z=corr.values, x=labels, y=labels,
            colorscale="RdBu", zmid=0, zmin=-1, zmax=1,
            text=corr.round(2).values, texttemplate="%{text}",
            textfont={"size":10,"family":"monospace"},
            hovertemplate="<b>%{y}</b> × <b>%{x}</b>: %{z:.2f}<extra></extra>",
        ))
        fig.update_layout(**L(), height=520, xaxis_tickangle=-40,
                          xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Pearson sobre retornos log (no niveles). Positivo semi-definida por construcción — "
            "garantía para VaR de portafolio."
        )

    with tab2:
        corr = full_correlation(returns, method="pearson")
        col1, col2 = st.columns(2)
        with col1:
            cur_x = st.selectbox("Eje X", list(returns.columns), index=0,
                                 format_func=lambda c: c)
        with col2:
            cur_y = st.selectbox("Eje Y", list(returns.columns), index=1,
                                 format_func=lambda c: c)

        rho = corr.loc[cur_x, cur_y]
        rx  = returns[cur_x] * 100
        ry  = returns[cur_y] * 100

        # Joint plot: scatter + marginal violins
        fig_j = px.scatter(
            x=rx, y=ry, opacity=0.3,
            color_discrete_sequence=["#1f4e79"],
            marginal_x="violin", marginal_y="violin",
            trendline="ols",
            labels={"x": f"{cur_x} ret (%)", "y": f"{cur_y} ret (%)"},
        )
        fig_j.update_traces(marker=dict(size=3), selector=dict(mode="markers"))
        # Style trendline
        for trace in fig_j.data:
            if getattr(trace, "mode", None) == "lines":
                trace.line.color = "#c0392b"
                trace.line.width = 2
        fig_j.update_layout(
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font=dict(family="monospace", size=11),
            title=dict(text=f"ρ = {rho:.3f}  (Pearson)", font=dict(size=13, family="monospace")),
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig_j, use_container_width=True)
        st.caption("Joint plot estilo seaborn: scatter + violines marginales + línea OLS. Permite ver asimetría y forma de ambas distribuciones simultáneamente.")

        st.divider()

        # Scatter matrix for a subset
        st.subheader("Matriz de Dispersión")
        sel_matrix = st.multiselect("Monedas (máx 5 recomendado)", list(returns.columns),
                                    default=["CLP","BRL","MXN","COP","PEN"],
                                    format_func=lambda c: c, key="matrix")
        if len(sel_matrix) >= 2:
            df_matrix = (returns[sel_matrix] * 100).copy()
            df_matrix.columns = [c for c in sel_matrix]
            fig_m = px.scatter_matrix(
                df_matrix, dimensions=sel_matrix,
                color_discrete_sequence=["#1f4e79"],
                opacity=0.2,
                labels={c: c for c in sel_matrix},
            )
            fig_m.update_traces(marker=dict(size=2), diagonal_visible=True)
            fig_m.update_layout(**L(), height=500)
            st.plotly_chart(fig_m, use_container_width=True)
            st.caption("Pairplot completo. Diagonal = eje propio. Permite detectar relaciones no lineales o agrupamientos por período.")

    with tab3:
        col1, col2 = st.columns([2,1])
        with col1:
            selected_corr = st.multiselect("Comparar vs CLP",
                                           [c for c in returns.columns if c != "CLP"],
                                           default=["BRL","MXN","COP","PEN"],
                                           format_func=lambda c: c)
        with col2:
            window_corr = st.slider("Ventana (días)", 30, 252, 90, 30)

        if selected_corr:
            rc = rolling_correlation(returns, base="CLP", window=window_corr)[selected_corr]
            fig2 = px.line(rc, color_discrete_sequence=CHART_COLORS,
                           labels={"value":"Correlación vs CLP","date":"","variable":""})
            fig2.add_hline(y=0, line_dash="dot", line_color="#bbb")
            fig2.update_layout(**L(hovermode="x unified"), legend=dict(orientation="h",y=-0.15,x=0),
                               xaxis=dict(showgrid=False,zeroline=False),
                               yaxis=dict(range=[-1,1], gridcolor="#f0f0f0", zeroline=False))
            st.plotly_chart(fig2, use_container_width=True)
            st.caption(f"Correlación Pearson móvil {window_corr}d. Cambios revelan períodos de desacoplamiento o contagio regional.")

# ===================================================================
# PAGE 4: VaR & Riesgo de Cola
# ===================================================================
elif page == "VaR & Riesgo de Cola":
    st.title("VaR & Riesgo de Cola")
    st.caption("Simulación histórica · sin supuesto de normalidad · horizonte 1 día · ES = CVaR")

    selected = st.multiselect("Monedas", list(returns.columns), default=LATAM,
                              format_func=lambda c: c)

    if selected:
        summary = var_summary(returns[selected]) * 100
        summary.index = [CURRENCY_LABELS.get(c,c) for c in summary.index]
        summary.columns = ["VaR 90%","ES 90%","VaR 95%","ES 95%","VaR 99%","ES 99%"]
        st.dataframe(
            summary.style
                .background_gradient(subset=["VaR 95%","VaR 99%"], cmap="YlOrRd_r")
                .format("{:.2f}%"),
            use_container_width=True)
        st.caption("VaR histórico: percentil (1-α) de la distribución empírica. Justificado por fat tails observados en retornos de monedas emergentes.")

        st.divider()

        col1, col2 = st.columns([1,2])
        with col1:
            conf_level    = st.select_slider("Confianza", options=[90,95,99], value=95)
            currency_dist = st.selectbox("Moneda", selected, format_func=lambda c: c)
        with col2:
            st.subheader(f"VaR vs ES — {conf_level}%")
            var_col, es_col = f"VaR {conf_level}%", f"ES {conf_level}%"
            fig = go.Figure()
            fig.add_trace(go.Bar(name=f"VaR {conf_level}%", x=summary.index,
                                 y=summary[var_col], marker_color="#1f4e79"))
            fig.add_trace(go.Bar(name=f"ES {conf_level}%", x=summary.index,
                                 y=summary[es_col], marker_color="#c0392b"))
            fig.update_layout(**L(hovermode="x unified"), barmode="group",
                              xaxis=dict(tickangle=-30,showgrid=False,zeroline=False),
                              yaxis=dict(gridcolor="#f0f0f0",zeroline=False,title="%"),
                              legend=dict(orientation="h",y=-0.25))
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        r      = returns[currency_dist] * 100
        var_val = historical_var(returns[[currency_dist]], confidence=conf_level/100)[currency_dist] * 100
        es_val  = expected_shortfall(returns[[currency_dist]], confidence=conf_level/100)[currency_dist] * 100
        kurt    = returns[currency_dist].kurtosis()
        skew_v  = returns[currency_dist].skew()

        tab_a, tab_b = st.tabs(["Distribución empírica vs normal", "Q-Q Plot"])

        with tab_a:
            st.subheader(f"Distribución — {CURRENCY_LABELS.get(currency_dist,currency_dist)}")
            x_range    = np.linspace(r.quantile(0.001), r.quantile(0.999), 400)
            normal_pdf = stats.norm.pdf(x_range, loc=r.mean(), scale=r.std())
            bin_width  = (r.quantile(0.999) - r.quantile(0.001)) / 80
            normal_sc  = normal_pdf * len(r) * bin_width

            fig2 = go.Figure()
            fig2.add_trace(go.Histogram(x=r, nbinsx=80, name="Empírica",
                                        marker_color="#1f4e79", opacity=0.7))
            fig2.add_trace(go.Scatter(x=x_range, y=normal_sc, mode="lines", name="Normal teórica",
                                      line=dict(color="#c0392b", width=2, dash="dash")))
            fig2.add_vline(x=var_val, line_color="#f39c12", line_dash="dash",
                           annotation_text=f"VaR {conf_level}%: {var_val:.2f}%",
                           annotation_font=dict(family="monospace",size=10))
            fig2.add_vline(x=es_val, line_color="#c0392b", line_dash="dash",
                           annotation_text=f"ES {conf_level}%: {es_val:.2f}%",
                           annotation_position="bottom left",
                           annotation_font=dict(family="monospace",size=10))
            fig2.update_layout(**L(), xaxis_title="retorno diario (%)", yaxis_title="frecuencia",
                               xaxis=dict(showgrid=False,zeroline=False),
                               yaxis=dict(gridcolor="#f0f0f0",zeroline=False),
                               legend=dict(orientation="h",y=-0.15,x=0))
            st.plotly_chart(fig2, use_container_width=True)

            k1, k2, k3 = st.columns(3)
            k1.metric("Curtosis", f"{kurt:.2f}", delta=f"{kurt-3:.2f} vs normal",
                      delta_color="inverse" if kurt > 3 else "normal")
            k2.metric("Sesgo", f"{skew_v:.3f}")
            k3.metric("Obs. cola izq. real",
                      f"{(r < var_val).sum()}",
                      delta=f"esperado normal: {int(len(r)*(1-conf_level/100))}")
            st.caption("Curtosis normal=3. Exceso indica eventos extremos más frecuentes de lo que predice la distribución normal.")

        with tab_b:
            st.subheader(f"Q-Q Plot vs Normal — {CURRENCY_LABELS.get(currency_dist,currency_dist)}")
            r_sorted = np.sort(returns[currency_dist].dropna().values)
            n        = len(r_sorted)
            probs    = (np.arange(1, n+1) - 0.5) / n
            theoretical = stats.norm.ppf(probs, loc=r_sorted.mean(), scale=r_sorted.std())

            fig_qq = go.Figure()
            # Reference line
            lim = max(abs(theoretical.min()), abs(theoretical.max()))
            fig_qq.add_trace(go.Scatter(x=[-lim, lim], y=[-lim, lim], mode="lines",
                                        line=dict(color="#c0392b", dash="dash", width=1.5),
                                        name="Normal perfecta"))
            fig_qq.add_trace(go.Scatter(
                x=theoretical * 100, y=r_sorted * 100,
                mode="markers", name="Retornos empíricos",
                marker=dict(color="#1f4e79", size=3, opacity=0.5),
            ))
            fig_qq.update_layout(**L(hovermode="closest"),
                                 xaxis=dict(title="Cuantiles teóricos normales (%)", showgrid=False, zeroline=False),
                                 yaxis=dict(title="Cuantiles empíricos (%)", gridcolor="#f0f0f0", zeroline=False),
                                 legend=dict(orientation="h",y=-0.15,x=0))
            st.plotly_chart(fig_qq, use_container_width=True)
            st.caption(
                "Q-Q Plot: si los retornos fueran normales, los puntos caerían sobre la línea roja. "
                "Desviación en los extremos = fat tails empíricos. "
                "Cola izquierda por debajo de la línea = pérdidas extremas más frecuentes y severas que lo normal."
            )

# ===================================================================
# PAGE 5: Stress Testing
# ===================================================================
elif page == "Stress Testing":
    st.title("Stress Testing")
    st.caption("Retorno log acumulado durante episodios de estrés · rojo=depreciación, verde=apreciación · Σr_t = ln(p_T/p_0)")

    selected = st.multiselect("Monedas", list(returns.columns),
                              default=LATAM + ["JPY","ORO_USD"],
                              format_func=lambda c: c)

    if selected:
        table = full_stress_table(returns[selected])
        table.columns = [CURRENCY_LABELS.get(c,c) for c in table.columns]

        # Heatmap
        fig = go.Figure(go.Heatmap(
            z=table.values, x=list(table.columns), y=list(table.index),
            colorscale="RdYlGn_r", zmid=0,
            text=table.round(1).values, texttemplate="%{text}%",
            textfont={"size":11,"family":"monospace"},
            hovertemplate="<b>%{y}</b><br>%{x}: %{z:.2f}%<extra></extra>",
        ))
        fig.update_layout(**L(), height=280, xaxis_tickangle=-30,
                          xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        col1, col2 = st.columns([1,2])
        with col1:
            scenario = st.selectbox("Escenario", list(table.index))
        with col2:
            row = table.loc[scenario].sort_values(ascending=True)

            # Lollipop chart
            fig2 = go.Figure()
            # Stems
            for i, (label, val) in enumerate(row.items()):
                fig2.add_shape(type="line", x0=0, x1=val, y0=i, y1=i,
                               line=dict(color="#c0392b" if val > 0 else "#27ae60", width=1.5))
            # Dots
            fig2.add_trace(go.Scatter(
                x=row.values, y=list(range(len(row))),
                mode="markers",
                marker=dict(
                    color=["#c0392b" if v > 0 else "#27ae60" for v in row.values],
                    size=10, line=dict(color="white", width=1.5),
                ),
                text=[f"{v:.1f}%" for v in row.values],
                hovertemplate="%{y}: %{text}<extra></extra>",
                showlegend=False,
            ))
            fig2.add_vline(x=0, line_color="#ccc", line_dash="dot")
            fig2.update_layout(**L(hovermode="closest"),
                               xaxis=dict(title="retorno acumulado (%)", showgrid=True, gridcolor="#f0f0f0", zeroline=False),
                               yaxis=dict(tickvals=list(range(len(row))),
                                          ticktext=list(row.index),
                                          showgrid=False, zeroline=False),
                               height=max(300, len(row)*35))
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Tabla completa")
        st.dataframe(
            table.style.background_gradient(cmap="RdYlGn_r", axis=None, vmin=-30, vmax=30).format("{:.2f}%"),
            use_container_width=True)
        st.caption("Aditividad de log-retornos: el retorno del período = Σr_t, válido sin importar la duración del episodio.")

# ===================================================================
# PAGE 6: Anomalías
# ===================================================================
elif page == "Anomalías":
    st.title("Anomalías")
    st.caption("Z-score móvil · |z| > 3σ bajo normalidad ocurre ~0.3% del tiempo")

    col1, col2 = st.columns([1,3])
    with col1:
        threshold = st.slider("Umbral (σ)", 2.0, 5.0, 3.0, 0.5)
    with col2:
        selected = st.multiselect("Monedas", list(returns.columns), default=LATAM,
                                  format_func=lambda c: c)

    if selected:
        report = anomaly_report(returns[selected], threshold=threshold)

        k1, k2, k3 = st.columns(3)
        k1.metric("Eventos detectados", len(report))
        k2.metric("Monedas afectadas", report["currency"].nunique() if len(report) else 0)
        k3.metric("Mayor z-score", f"{report['zscore'].abs().max():.1f}σ" if len(report) else "—")

        st.divider()

        if len(report):
            tab_a, tab_b, tab_c = st.tabs(["Timeline","Heatmap mensual","Tabla"])

            with tab_a:
                fig = px.scatter(
                    report, x="date", y="zscore", color="currency",
                    size=report["zscore"].abs(), color_discrete_sequence=CHART_COLORS,
                    hover_data=["currency","return_pct","zscore"],
                    labels={"date":"","zscore":"z-score","currency":""},
                )
                fig.add_hline(y=threshold, line_dash="dash", line_color="#c0392b",
                              annotation_text=f"+{threshold}σ", annotation_font=dict(family="monospace",size=10))
                fig.add_hline(y=-threshold, line_dash="dash", line_color="#1f4e79",
                              annotation_text=f"-{threshold}σ", annotation_font=dict(family="monospace",size=10))
                fig.add_hline(y=0, line_color="#ddd", line_dash="dot")
                fig.update_layout(**L(hovermode="closest"),
                                  xaxis=dict(showgrid=False,zeroline=False),
                                  yaxis=dict(gridcolor="#f0f0f0",zeroline=False),
                                  legend=dict(orientation="h",y=-0.15,x=0))
                st.plotly_chart(fig, use_container_width=True)
                st.caption("z_t = (r_t − μ_t)/σ_t · ventana 30d. Tamaño del punto ∝ |z-score|.")

            with tab_b:
                # Monthly anomaly heatmap per currency
                st.subheader("Frecuencia Mensual de Anomalías por Moneda")
                rep2 = report.copy()
                rep2["date"]  = pd.to_datetime(rep2["date"])
                rep2["year"]  = rep2["date"].dt.year
                rep2["month"] = rep2["date"].dt.month

                # One heatmap per currency
                cur_hm2 = st.selectbox("Moneda", selected, format_func=lambda c: c, key="ahm")
                sub = rep2[rep2["currency"] == cur_hm2]
                if len(sub):
                    pivot_a = sub.groupby(["year","month"]).size().unstack(fill_value=0)
                    pivot_a.columns = [MONTHS_ES[m-1] for m in pivot_a.columns]
                    fig_ah = go.Figure(go.Heatmap(
                        z=pivot_a.values, x=list(pivot_a.columns),
                        y=[str(y) for y in pivot_a.index],
                        colorscale="YlOrRd", zmin=0,
                        text=pivot_a.values.astype(str),
                        texttemplate="%{text}", textfont={"size":11,"family":"monospace"},
                        hovertemplate="<b>%{y} %{x}</b>: %{z} eventos<extra></extra>",
                    ))
                    fig_ah.update_layout(**L(), height=250,
                                         xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
                    st.plotly_chart(fig_ah, use_container_width=True)
                    st.caption(f"Número de días con |z| > {threshold}σ por mes y año. Permite identificar períodos de estrés concentrado.")
                else:
                    st.info(f"Sin eventos para {cur_hm2} con umbral {threshold}σ.")

                # Expected vs observed
                st.divider()
                st.subheader("Observado vs Esperado bajo Normalidad")
                counts = report["currency"].value_counts().reset_index()
                counts.columns = ["currency","n"]
                counts["label"] = counts["currency"].map(lambda c: CURRENCY_LABELS.get(c,c))
                n_total     = len(returns[selected[0]])
                expected_n  = int(n_total * 2 * (1 - stats.norm.cdf(threshold)))
                fig_cnt = px.bar(counts, x="label", y="n",
                                 color="n", color_continuous_scale="YlOrRd",
                                 labels={"label":"","n":"eventos"})
                fig_cnt.add_hline(y=expected_n, line_dash="dash", line_color="#1f4e79",
                                  annotation_text=f"esperado normal: {expected_n}",
                                  annotation_font=dict(family="monospace",size=9))
                fig_cnt.update_layout(**L(), coloraxis_showscale=False, xaxis_tickangle=-30,
                                      xaxis=dict(showgrid=False,zeroline=False),
                                      yaxis=dict(gridcolor="#f0f0f0",zeroline=False))
                st.plotly_chart(fig_cnt, use_container_width=True)
                st.caption(f"Línea azul = esperado bajo normalidad ({expected_n} eventos para |z|>{threshold}σ). La superación generalizada confirma fat tails empíricos.")

            with tab_c:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader(f"Top 30 eventos")
                    display = report.head(30).copy()
                    display["currency"] = display["currency"].map(lambda c: CURRENCY_LABELS.get(c,c))
                    display["date"]     = pd.to_datetime(display["date"]).dt.strftime("%Y-%m-%d")
                    display.columns     = ["Fecha","Moneda","Retorno (%)","Z-score"]
                    st.dataframe(display.style.background_gradient(subset=["Z-score"], cmap="RdBu_r"),
                                 use_container_width=True, hide_index=True)
                with col_b:
                    st.subheader("Distribución de z-scores extremos")
                    fig_zd = go.Figure()
                    fig_zd.add_trace(go.Histogram(x=report["zscore"], nbinsx=40,
                                                  marker_color="#1f4e79", opacity=0.75))
                    fig_zd.add_vline(x=threshold, line_color="#c0392b", line_dash="dash")
                    fig_zd.add_vline(x=-threshold, line_color="#1f4e79", line_dash="dash")
                    fig_zd.update_layout(**L(), xaxis_title="z-score",
                                         yaxis_title="frecuencia",
                                         xaxis=dict(showgrid=False,zeroline=False),
                                         yaxis=dict(gridcolor="#f0f0f0",zeroline=False),
                                         showlegend=False)
                    st.plotly_chart(fig_zd, use_container_width=True)
        else:
            st.info(f"Sin eventos sobre {threshold}σ.")
