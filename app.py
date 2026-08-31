import streamlit as st
from utils.data_loader import load_master, kpis, sidebar_filters

st.set_page_config(page_title="Olist Analytics", page_icon="📦", layout="wide")

st.title("📦 Olist Analytics")
st.caption("Dashboard de vendas, produtos, logística e análise com IA — dataset Olist (2016–2018).")

df = load_master()
fdf = sidebar_filters(df)
st.session_state["filtered_df"] = fdf

k = kpis(fdf)
c = st.columns(4)
c[0].metric("Receita", f"R$ {k['receita']:,.0f}".replace(",", "."))
c[1].metric("Pedidos", f"{k['pedidos']:,}".replace(",", "."))
c[2].metric("Ticket médio", f"R$ {k['ticket_medio']:,.2f}")
c[3].metric("Prazo médio", f"{k['prazo_medio']:.1f} dias")

st.markdown("""
### Navegação
- **1 · Visão Geral** — KPIs, evolução mensal, meios de pagamento
- **2 · Produtos** — receita e volume por categoria, preço vs. frete
- **3 · Logística** — tempo de entrega, atrasos e frete por estado
- **4 · Análise IA** — perguntas em português sobre os dados via OpenAI

Use os filtros na barra lateral: eles valem para todas as páginas.
""")

with st.expander("Amostra dos dados"):
    st.dataframe(fdf.head(200), use_container_width=True)
