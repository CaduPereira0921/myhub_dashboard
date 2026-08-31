import pandas as pd
import plotly.express as px
import streamlit as st
from utils.data_loader import load_master, load_raw, kpis, sidebar_filters

st.set_page_config(page_title="Visão Geral", page_icon="📈", layout="wide")
st.title("📈 Visão Geral de Vendas")

fdf = sidebar_filters(load_master())
if fdf.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()

k = kpis(fdf)
c = st.columns(5)
c[0].metric("Receita", f"R$ {k['receita']:,.0f}")
c[1].metric("Pedidos", f"{k['pedidos']:,}")
c[2].metric("Ticket médio", f"R$ {k['ticket_medio']:,.2f}")
c[3].metric("Clientes únicos", f"{k['clientes']:,}")
c[4].metric("% Atraso", f"{k['pct_atraso']:.1f}%")

monthly = (fdf.groupby("order_month")
           .agg(receita=("revenue", "sum"), pedidos=("order_id", "nunique"))
           .reset_index())
monthly["ticket"] = monthly["receita"] / monthly["pedidos"]

col1, col2 = st.columns(2)
with col1:
    fig = px.area(monthly, x="order_month", y="receita", title="Receita mensal (R$)",
                  labels={"order_month": "Mês", "receita": "Receita"})
    fig.update_traces(line_color="#2E86DE", fillcolor="rgba(46,134,222,0.25)")
    st.plotly_chart(fig, use_container_width=True)
with col2:
    fig = px.bar(monthly, x="order_month", y="pedidos", title="Pedidos por mês",
                 labels={"order_month": "Mês", "pedidos": "Pedidos"},
                 color_discrete_sequence=["#10AC84"])
    st.plotly_chart(fig, use_container_width=True)

col3, col4 = st.columns(2)
with col3:
    fig = px.line(monthly, x="order_month", y="ticket", markers=True,
                  title="Ticket médio mensal (R$)",
                  labels={"order_month": "Mês", "ticket": "Ticket médio"})
    st.plotly_chart(fig, use_container_width=True)

with col4:
    pay = load_raw()["payments"]
    pay = pay[pay["order_id"].isin(fdf["order_id"].unique())]
    by_type = pay.groupby("payment_type", as_index=False)["payment_value"].sum()
    fig = px.pie(by_type, names="payment_type", values="payment_value", hole=0.45,
                 title="Receita por meio de pagamento")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Top 10 estados por receita")
by_state = (fdf.groupby("customer_state", as_index=False)
            .agg(receita=("revenue", "sum"), pedidos=("order_id", "nunique"))
            .sort_values("receita", ascending=False).head(10))
fig = px.bar(by_state, x="customer_state", y="receita", text_auto=".2s",
             color="receita", color_continuous_scale="Blues",
             labels={"customer_state": "UF", "receita": "Receita (R$)"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Parcelamento")
inst = (pay.groupby("payment_installments", as_index=False)["order_id"].nunique()
        .rename(columns={"order_id": "pedidos"}))
st.plotly_chart(px.bar(inst, x="payment_installments", y="pedidos",
                       labels={"payment_installments": "Parcelas", "pedidos": "Pedidos"}),
                use_container_width=True)
