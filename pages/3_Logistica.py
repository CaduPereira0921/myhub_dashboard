import plotly.express as px
import streamlit as st
from utils.data_loader import load_master, sidebar_filters

st.set_page_config(page_title="Logística", page_icon="🚚", layout="wide")
st.title("🚚 Logística: Entrega e Frete")

fdf = sidebar_filters(load_master())
fdf = fdf[fdf["delivery_days"].notna()]
if fdf.empty:
    st.warning("Nenhum pedido entregue para os filtros selecionados.")
    st.stop()

c = st.columns(4)
c[0].metric("Prazo médio real", f"{fdf['delivery_days'].mean():.1f} dias")
c[1].metric("Prazo estimado médio", f"{fdf['estimated_days'].mean():.1f} dias")
c[2].metric("% Entregas atrasadas", f"{fdf['is_late'].mean() * 100:.1f}%")
c[3].metric("Frete médio", f"R$ {fdf['freight_value'].mean():.2f}")

col1, col2 = st.columns(2)
with col1:
    fig = px.histogram(fdf, x="delivery_days", nbins=60,
                       title="Distribuição do tempo de entrega (dias)",
                       labels={"delivery_days": "Dias até a entrega"},
                       color_discrete_sequence=["#5F27CD"])
    fig.add_vline(x=fdf["delivery_days"].median(), line_dash="dash",
                  annotation_text="mediana")
    st.plotly_chart(fig, use_container_width=True)
with col2:
    fig = px.box(fdf, x="is_late", y="freight_value", points=False,
                 title="Frete: pedidos no prazo vs. atrasados",
                 labels={"is_late": "Atrasado", "freight_value": "Frete (R$)"})
    fig.update_yaxes(range=[0, fdf["freight_value"].quantile(0.98)])
    st.plotly_chart(fig, use_container_width=True)

by_state = (fdf.groupby("customer_state")
            .agg(prazo_medio=("delivery_days", "mean"),
                 prazo_estimado=("estimated_days", "mean"),
                 frete_medio=("freight_value", "mean"),
                 pct_atraso=("is_late", "mean"),
                 pedidos=("order_id", "nunique"))
            .reset_index())
by_state["pct_atraso"] *= 100

col3, col4 = st.columns(2)
with col3:
    d = by_state.sort_values("prazo_medio", ascending=False)
    fig = px.bar(d, x="prazo_medio", y="customer_state", orientation="h",
                 color="prazo_medio", color_continuous_scale="Reds",
                 title="Tempo médio de entrega por UF",
                 labels={"prazo_medio": "Dias", "customer_state": ""})
    fig.update_layout(height=680)
    st.plotly_chart(fig, use_container_width=True)
with col4:
    d = by_state.sort_values("frete_medio", ascending=False)
    fig = px.bar(d, x="frete_medio", y="customer_state", orientation="h",
                 color="frete_medio", color_continuous_scale="Purples",
                 title="Frete médio por UF",
                 labels={"frete_medio": "Frete (R$)", "customer_state": ""})
    fig.update_layout(height=680)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Prazo × frete × volume por estado")
fig = px.scatter(by_state, x="prazo_medio", y="frete_medio", size="pedidos",
                 color="pct_atraso", text="customer_state", size_max=60,
                 color_continuous_scale="RdYlGn_r",
                 labels={"prazo_medio": "Prazo médio (dias)",
                         "frete_medio": "Frete médio (R$)",
                         "pct_atraso": "% atraso"})
fig.update_traces(textposition="top center")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Evolução mensal do prazo de entrega")
ts = (fdf.groupby("order_month")
      .agg(real=("delivery_days", "mean"), estimado=("estimated_days", "mean"))
      .reset_index())
fig = px.line(ts, x="order_month", y=["real", "estimado"], markers=True,
              labels={"order_month": "Mês", "value": "Dias", "variable": ""})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Detalhamento por estado")
st.dataframe(by_state.round(2).sort_values("pedidos", ascending=False),
             use_container_width=True)
