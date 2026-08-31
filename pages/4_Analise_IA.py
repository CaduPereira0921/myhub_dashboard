import json
import streamlit as st
from utils.data_loader import load_master, sidebar_filters
from utils.llm_client import ask, build_context, get_client

st.set_page_config(page_title="Análise IA", page_icon="🤖", layout="wide")
st.title("🤖 Análise com IA")
st.caption("Pergunte em português sobre os dados filtrados. As respostas usam "
           "agregações reais enviadas ao modelo da OpenAI.")

fdf = sidebar_filters(load_master())
if fdf.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()

if get_client() is None:
    st.error("`OPENAI_API_KEY` ausente ou inválida no `.env`. "
             "Configure a chave para habilitar as respostas.")

context = build_context(fdf)

with st.expander("🔍 Contexto enviado ao modelo"):
    st.json(context)

SUGESTOES = [
    "Quais categorias têm o melhor desempenho de receita e por quê?",
    "Onde estão os maiores gargalos logísticos e como reduzi-los?",
    "Como o frete se relaciona com o tempo de entrega por estado?",
    "Qual a tendência da receita mensal e o que ela indica para o próximo trimestre?",
    "Quais estados oferecem maior potencial de crescimento?",
]

st.markdown("**Sugestões rápidas:**")
cols = st.columns(len(SUGESTOES))
clicked = None
for i, s in enumerate(SUGESTOES):
    if cols[i].button(s[:28] + "…", key=f"sug{i}", help=s, use_container_width=True):
        clicked = s

if "chat" not in st.session_state:
    st.session_state.chat = []

for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

pergunta = st.chat_input("Ex.: qual categoria tem o pior prazo de entrega?") or clicked

if pergunta:
    st.session_state.chat.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)
    with st.chat_message("assistant"):
        with st.spinner("Analisando..."):
            resposta = ask(pergunta, context, st.session_state.chat[:-1])
        st.markdown(resposta)
    st.session_state.chat.append({"role": "assistant", "content": resposta})

if st.session_state.chat and st.sidebar.button("🗑️ Limpar conversa"):
    st.session_state.chat = []
    st.rerun()
