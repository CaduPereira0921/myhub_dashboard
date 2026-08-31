import plotly.express as px
import streamlit as st
from utils.data_loader import load_master, load_reviews_by_order, sidebar_filters

st.set_page_config(page_title="Produtos", page_icon="🛍️", layout="wide")
st.title("🛍️ Análise de Produtos por Categoria")

fdf = sidebar_filters(load_master())
if fdf.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()

top_n = st.slider("Top N categorias", 5, 30, 15)

agg = (fdf.groupby("category")
       .agg(receita=("revenue", "sum"), itens=("order_id", "count"),
            pedidos=("order_id", "nunique"), preco_medio=("price", "mean"),
            frete_medio=("freight_value", "mean"),
            peso_medio=("product_weight_g", "mean"))
       .reset_index().sort_values("receita", ascending=False))
top = agg.head(top_n)

c = st.columns(3)
c[0].metric("Categorias", f"{fdf['category'].nunique()}")
c[1].metric("Produtos distintos", f"{fdf['product_id'].nunique():,}")
c[2].metric("Preço médio do item", f"R$ {fdf['price'].mean():,.2f}")

col1, col2 = st.columns(2)
with col1:
    fig = px.bar(top.sort_values("receita"), x="receita", y="category",
                 orientation="h", title=f"Top {top_n} categorias por receita",
                 color="receita", color_continuous_scale="Teal",
                 labels={"receita": "Receita (R$)", "category": ""})
    fig.update_layout(height=520)
    st.plotly_chart(fig, use_container_width=True)
with col2:
    fig = px.bar(top.sort_values("itens"), x="itens", y="category",
                 orientation="h", title=f"Top {top_n} categorias por volume de itens",
                 color="itens", color_continuous_scale="Oranges",
                 labels={"itens": "Itens vendidos", "category": ""})
    fig.update_layout(height=520)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Preço médio vs. frete médio")
fig = px.scatter(top, x="preco_medio", y="frete_medio", size="receita",
                 color="category", hover_name="category", size_max=55,
                 labels={"preco_medio": "Preço médio (R$)",
                         "frete_medio": "Frete médio (R$)"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Evolução mensal das principais categorias")
sel = st.multiselect("Categorias", agg["category"].tolist(),
                     default=agg["category"].head(5).tolist())
if sel:
    ts = (fdf[fdf["category"].isin(sel)]
          .groupby(["order_month", "category"], as_index=False)["revenue"].sum())
    st.plotly_chart(px.line(ts, x="order_month", y="revenue", color="category",
                            markers=True, labels={"order_month": "Mês",
                                                  "revenue": "Receita (R$)"}),
                    use_container_width=True)

st.subheader("Satisfação média por categoria")
rev = load_reviews_by_order()
scored = fdf.merge(rev, on="order_id", how="inner")
if not scored.empty:
    sc = (scored.groupby("category", as_index=False)
          .agg(nota=("review_score", "mean"), avaliacoes=("review_score", "count"))
          .query("avaliacoes >= 30").sort_values("nota"))
    fig = px.bar(sc.head(15), x="nota", y="category", orientation="h",
                 range_x=[1, 5], color="nota", color_continuous_scale="RdYlGn",
                 title="15 categorias com pior nota média (mín. 30 avaliações)",
                 labels={"nota": "Nota média", "category": ""})
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Tabela detalhada")
st.dataframe(agg.round(2), use_container_width=True)
st.download_button("⬇️ Baixar CSV", agg.to_csv(index=False).encode("utf-8"),
                   "categorias_olist.csv", "text/csv")
