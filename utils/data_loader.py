import os
import pandas as pd
import streamlit as st

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "categories": "product_category_name_translation.csv",
}

DATE_COLS = {
    "orders": [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}


@st.cache_data(show_spinner="Carregando dados...")
def load_raw() -> dict[str, pd.DataFrame]:
    dfs = {}
    for key, fname in FILES.items():
        path = os.path.join(DATA_DIR, fname)
        df = pd.read_csv(path, dtype={"customer_zip_code_prefix": str,
                                      "seller_zip_code_prefix": str})
        for col in DATE_COLS.get(key, []):
            df[col] = pd.to_datetime(df[col], errors="coerce")
        dfs[key] = df
    return dfs


@st.cache_data(show_spinner="Montando tabela analítica...")
def load_master() -> pd.DataFrame:
    d = load_raw()

    products = d["products"].merge(d["categories"], on="product_category_name", how="left")
    products["category"] = (
        products["product_category_name_english"]
        .fillna(products["product_category_name"])
        .fillna("desconhecida")
    )

    df = (
        d["items"]
        .merge(d["orders"], on="order_id", how="left")
        .merge(d["customers"], on="customer_id", how="left")
        .merge(products[["product_id", "category", "product_weight_g",
                         "product_photos_qty"]], on="product_id", how="left")
        .merge(d["sellers"], on="seller_id", how="left")
    )

    df["revenue"] = df["price"] + df["freight_value"]
    df["order_month"] = df["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    df["delivery_days"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    df["estimated_days"] = (
        df["order_estimated_delivery_date"] - df["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    df["delay_days"] = (
        df["order_delivered_customer_date"] - df["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400
    df["is_late"] = df["delay_days"] > 0
    df["freight_ratio"] = df["freight_value"] / df["price"].replace(0, pd.NA)

    return df


@st.cache_data
def load_reviews_by_order() -> pd.DataFrame:
    r = load_raw()["reviews"]
    return r.groupby("order_id", as_index=False).agg(review_score=("review_score", "mean"))


def apply_filters(df: pd.DataFrame, date_range=None, states=None,
                  categories=None, status=("delivered",)) -> pd.DataFrame:
    out = df
    if status:
        out = out[out["order_status"].isin(status)]
    if date_range and len(date_range) == 2:
        start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        out = out[out["order_purchase_timestamp"].between(start, end)]
    if states:
        out = out[out["customer_state"].isin(states)]
    if categories:
        out = out[out["category"].isin(categories)]
    return out


def kpis(df: pd.DataFrame) -> dict:
    orders = df["order_id"].nunique()
    revenue = df["revenue"].sum()
    return {
        "receita": revenue,
        "pedidos": orders,
        "itens": len(df),
        "ticket_medio": revenue / orders if orders else 0,
        "clientes": df["customer_unique_id"].nunique(),
        "frete_medio": df["freight_value"].mean(),
        "prazo_medio": df["delivery_days"].mean(),
        "pct_atraso": df["is_late"].mean() * 100 if len(df) else 0,
    }


def sidebar_filters(df: pd.DataFrame):
    st.sidebar.header("Filtros")
    min_d = df["order_purchase_timestamp"].min().date()
    max_d = df["order_purchase_timestamp"].max().date()
    date_range = st.sidebar.date_input("Período", (min_d, max_d),
                                       min_value=min_d, max_value=max_d)
    states = st.sidebar.multiselect("Estados (UF do cliente)",
                                    sorted(df["customer_state"].dropna().unique()))
    cats = st.sidebar.multiselect("Categorias",
                                 sorted(df["category"].dropna().unique()))
    only_delivered = st.sidebar.checkbox("Somente pedidos entregues", value=True)
    status = ("delivered",) if only_delivered else tuple(df["order_status"].unique())
    return apply_filters(df, date_range, states, cats, status)
