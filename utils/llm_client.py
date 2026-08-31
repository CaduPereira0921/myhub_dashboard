import os
import json
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = """Você é um analista de dados sênior especializado em e-commerce.
Analise os dados agregados do dataset Olist (marketplace brasileiro, 2016-2018)
fornecidos como contexto JSON e responda à pergunta do usuário em português do Brasil.

Regras:
- Baseie-se APENAS nos dados do contexto. Se algo não estiver disponível, diga claramente.
- Cite números concretos (valores em R$, percentuais, prazos em dias).
- Estruture a resposta: resumo direto, evidências numéricas, e 2-3 recomendações práticas.
- Seja conciso; use markdown com listas e negrito quando ajudar.
"""


def get_client() -> OpenAI | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key or key.startswith("sk-sua-chave"):
        return None
    return OpenAI(api_key=key)


def build_context(df: pd.DataFrame, top_n: int = 12) -> dict:
    """Agrega o dataframe filtrado em um contexto compacto para o LLM."""
    if df.empty:
        return {"aviso": "nenhum dado no filtro atual"}

    monthly = (
        df.groupby("order_month")
        .agg(receita=("revenue", "sum"), pedidos=("order_id", "nunique"))
        .round(2).reset_index()
    )
    monthly["order_month"] = monthly["order_month"].dt.strftime("%Y-%m")

    by_cat = (
        df.groupby("category")
        .agg(receita=("revenue", "sum"), itens=("order_id", "count"),
             preco_medio=("price", "mean"))
        .round(2).sort_values("receita", ascending=False).head(top_n).reset_index()
    )

    by_state = (
        df.groupby("customer_state")
        .agg(receita=("revenue", "sum"), pedidos=("order_id", "nunique"),
             frete_medio=("freight_value", "mean"),
             prazo_medio=("delivery_days", "mean"),
             pct_atraso=("is_late", "mean"))
        .round(2).sort_values("receita", ascending=False).head(top_n).reset_index()
    )

    return {
        "periodo": {
            "inicio": str(df["order_purchase_timestamp"].min().date()),
            "fim": str(df["order_purchase_timestamp"].max().date()),
        },
        "totais": {
            "receita_total": round(df["revenue"].sum(), 2),
            "pedidos": int(df["order_id"].nunique()),
            "itens": len(df),
            "ticket_medio": round(df["revenue"].sum() / df["order_id"].nunique(), 2),
            "frete_medio": round(df["freight_value"].mean(), 2),
            "prazo_entrega_medio_dias": round(df["delivery_days"].mean(), 2),
            "pct_pedidos_atrasados": round(df["is_late"].mean() * 100, 2),
            "categorias_distintas": int(df["category"].nunique()),
            "vendedores": int(df["seller_id"].nunique()),
        },
        "evolucao_mensal": monthly.to_dict("records"),
        "top_categorias": by_cat.to_dict("records"),
        "top_estados": by_state.to_dict("records"),
    }


def ask(question: str, context: dict, history: list[dict] | None = None,
        model: str | None = None) -> str:
    client = get_client()
    if client is None:
        return ("⚠️ Chave da OpenAI não configurada. Defina `OPENAI_API_KEY` "
                "no arquivo `.env` e reinicie o app.")

    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content":
            "CONTEXTO (dados agregados):\n" + json.dumps(context, ensure_ascii=False, default=str)},
    ]
    messages += (history or [])[-6:]
    messages.append({"role": "user", "content": question})

    try:
        resp = client.chat.completions.create(
            model=model, messages=messages, temperature=0.3, max_tokens=1200
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ Erro ao chamar a API da OpenAI: `{e}`"
