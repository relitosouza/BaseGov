"""Grafo LangGraph: reescreve a pergunta -> busca nos manuais -> responde (ou admite que não sabe)."""
from typing import Annotated, TypedDict

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

import config
from ingest import get_embeddings

NOT_FOUND = (
    "Não encontrei essa informação nos manuais. "
    "Pode reformular a pergunta ou dar mais detalhes?"
)

SYSTEM_PROMPT = """Você é um assistente de suporte que responde SOMENTE com base nos trechos \
dos manuais fornecidos abaixo. Responda em português, de forma clara e objetiva, com passos \
numerados quando for um procedimento. Se os trechos não bastarem, diga que não encontrou no \
manual. Nunca invente informações.

Trechos dos manuais:
{context}"""



def build_llm():
    if config.LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=config.LLM_MODEL, temperature=0)
    if config.LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        # lê a chave de GOOGLE_API_KEY
        return ChatGoogleGenerativeAI(
            model=config.LLM_MODEL,
            temperature=0,
            timeout=config.LLM_TIMEOUT,
            max_retries=2,
        )
    # NVIDIA lê a chave de NVIDIA_API_KEY
    from langchain_nvidia_ai_endpoints import ChatNVIDIA

    chat = ChatNVIDIA(
        model=config.LLM_MODEL, temperature=0, max_completion_tokens=1024
    )
    # o padrão (60s) estoura com modelos grandes no plano gratuito
    chat._client.timeout = config.LLM_TIMEOUT
    return chat


llm = build_llm()
vectorstore = Chroma(
    persist_directory=str(config.CHROMA_DIR),
    embedding_function=get_embeddings(),
    collection_metadata={"hnsw:space": "cosine"},
)


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    query: str
    docs: list[Document]


def rewrite(state: State) -> dict:
    """Transforma a última pergunta em uma consulta autônoma, usando o histórico."""
    msgs = state["messages"]
    question = msgs[-1].content
    if len(msgs) < 2:
        return {"query": question}
    history = "\n".join(
        f"{'Usuário' if isinstance(m, HumanMessage) else 'Bot'}: {m.content}"
        for m in msgs[-7:-1]
    )
    out = llm.invoke(
        "Reescreva a última pergunta como uma pergunta completa e independente, "
        "usando o histórico. Responda apenas com a pergunta.\n\n"
        f"Histórico:\n{history}\n\nÚltima pergunta: {question}"
    )
    return {"query": out.content.strip()}


def retrieve(state: State) -> dict:
    results = vectorstore.similarity_search_with_relevance_scores(
        state["query"], k=config.TOP_K
    )
    return {"docs": [d for d, score in results if score >= config.MIN_SCORE]}


def route(state: State) -> str:
    return "generate" if state["docs"] else "not_found"


def generate(state: State) -> dict:
    context = "\n\n".join(
        f"[{d.metadata['source']}"
        + (f", pág. {d.metadata['page'] + 1}" if "page" in d.metadata else "")
        + f"]\n{d.page_content}"
        for d in state["docs"]
    )
    answer = llm.invoke(
        [SystemMessage(SYSTEM_PROMPT.format(context=context)), *state["messages"][-7:]]
    )
    sources = sorted({d.metadata["source"] for d in state["docs"]})
    return {
        "messages": [AIMessage(f"{answer.content}\n\n📚 Fontes: {', '.join(sources)}")]
    }


def not_found(state: State) -> dict:
    return {"messages": [AIMessage(NOT_FOUND)]}


def build_graph():
    g = StateGraph(State)
    g.add_node("rewrite", rewrite)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.add_node("not_found", not_found)
    g.add_edge(START, "rewrite")
    g.add_edge("rewrite", "retrieve")
    g.add_conditional_edges("retrieve", route, ["generate", "not_found"])
    g.add_edge("generate", END)
    g.add_edge("not_found", END)
    # Memória por conversa (thread_id = chat_id do Telegram)
    return g.compile(checkpointer=MemorySaver())
