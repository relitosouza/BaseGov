"""Grafo LangGraph: reescreve a pergunta -> busca nos manuais -> responde (ou admite que não sabe)."""
import re
from typing import Annotated, TypedDict

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

import cache
import config
from ingest import get_embeddings

NOT_FOUND = (
    "Não encontrei essa informação nos manuais. "
    "Pode reformular a pergunta ou dar mais detalhes?"
)

SYSTEM_PROMPT = """Você é um assistente de suporte que responde SOMENTE com base nos trechos \
dos manuais fornecidos abaixo. Responda em português, de forma clara, didática e com passos \
numerados bem detalhados quando for um procedimento.

IMPORTANTE SOBRE IMAGENS:
Cada trecho abaixo pode indicar uma ou mais imagens disponíveis com a marcação [FIGURA: caminho/imagem.png].
Sempre que você descrever uma tela, menu, formulário ou botão correspondente àquela figura, inclua \
a marcação exata [IMG: caminho/imagem.png] em uma linha separada logo após o parágrafo ou passo correspondente.
Nunca invente nomes de imagens: use apenas as que aparecem no contexto.

Se os trechos não bastarem para responder, diga que não encontrou no manual. Nunca invente informações.

Trechos dos manuais:
{context}"""



def build_llm():
    if config.LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=config.LLM_MODEL, temperature=0)
    if config.LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        def gemini(model: str):
            # lê a chave de GOOGLE_API_KEY
            return ChatGoogleGenerativeAI(
                model=model,
                temperature=0,
                timeout=config.LLM_TIMEOUT,
                max_retries=4,  # 503/429 são comuns e passageiros
            )

        primary = gemini(config.LLM_MODEL)
        backups = [gemini(m) for m in config.LLM_FALLBACK_MODELS]
        # se o modelo principal falhar mesmo após as tentativas, usa os reservas
        return primary.with_fallbacks(backups) if backups else primary
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


def text_of(content) -> str:
    """Extrai só o texto da resposta (alguns modelos devolvem uma lista de blocos)."""
    if isinstance(content, str):
        return content
    return "".join(
        b if isinstance(b, str) else b.get("text", "")
        for b in content
        if isinstance(b, str) or b.get("type") == "text"
    )


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    query: str
    cached: str
    images: list[str]
    docs: list[Document]


def rewrite(state: State) -> dict:
    """Transforma a última pergunta em uma consulta autônoma, usando o histórico."""
    msgs = state["messages"]
    question = text_of(msgs[-1].content)
    if len(msgs) < 2:
        return {"query": question}
    history = "\n".join(
        f"{'Usuário' if isinstance(m, HumanMessage) else 'Bot'}: {text_of(m.content)}"
        for m in msgs[-7:-1]
    )
    out = llm.invoke(
        "Reescreva a última pergunta como uma pergunta completa e independente, "
        "usando o histórico. Responda apenas com a pergunta.\n\n"
        f"Histórico:\n{history}\n\nÚltima pergunta: {question}"
    )
    return {"query": text_of(out.content).strip()}


def lookup(state: State) -> dict:
    hit = cache.get(state["query"])
    # "images" é zerado a cada pergunta (o estado persiste entre turnos)
    return {"cached": hit[0], "images": hit[1]} if hit else {"cached": "", "images": []}


def route_cache(state: State) -> str:
    return "from_cache" if state["cached"] else "retrieve"


def from_cache(state: State) -> dict:
    return {
        "messages": [AIMessage(state["cached"])],
        "images": state.get("images", []),
    }


def retrieve(state: State) -> dict:
    # Busca um conjunto mais amplo para poder agrupar por manual
    results = vectorstore.similarity_search_with_relevance_scores(
        state["query"], k=10
    )
    docs = []
    for d, score in results:
        if score >= config.MIN_SCORE:
            d.metadata["score"] = score
            docs.append(d)

    if not docs:
        return {"docs": []}

    # Identifica o manual mais relevante para priorizar suas informações e imagens
    best_source = docs[0].metadata.get("source")
    # Mantém os trechos do manual principal e trechos de altíssima relevância
    filtered = [
        d for d in docs
        if d.metadata.get("source") == best_source or d.metadata.get("score", 0) >= docs[0].metadata.get("score", 0) - 0.03
    ][: config.TOP_K]

    return {"docs": filtered}


def route(state: State) -> str:
    return "generate" if state["docs"] else "not_found"


def _image_sort_key(path: str):
    # Ordena naturalmente por números: ex. _p1_1, _p1_2, _p2_1 ou _s1_1, _s1_2
    parts = re.split(r"(\d+)", path)
    return [int(p) if p.isdigit() else p for p in parts]


def pick_images(docs: list[Document]) -> list[str]:
    """Imagens dos trechos mais relevantes, preservando a ordem cronológica do manual."""
    ranked = sorted(docs, key=lambda d: d.metadata.get("score", 0), reverse=True)
    if not ranked:
        return []
    top = ranked[0].metadata.get("score", 0)
    chosen = [
        d for d in ranked if d.metadata.get("score", 0) >= top - config.IMAGE_SCORE_MARGIN
    ][: config.IMAGE_DOCS]

    # Ordena os trechos pela ordem natural do documento (source e página/posição)
    chosen = sorted(
        chosen,
        key=lambda d: (
            d.metadata.get("source", ""),
            d.metadata.get("page", 0),
        ),
    )

    paths: list[str] = []
    for d in chosen:
        raw_imgs = [p for p in d.metadata.get("images", "").split("|") if p]
        # Ordena as imagens do trecho sequencialmente
        raw_imgs = sorted(raw_imgs, key=_image_sort_key)
        for p in raw_imgs:
            if p not in paths:
                paths.append(p)
    return paths[: config.MAX_IMAGES]


def generate(state: State) -> dict:
    context_parts = []
    available_images: list[str] = []

    for d in state["docs"]:
        header = f"[{d.metadata['source']}" + (f", pág. {d.metadata['page'] + 1}" if "page" in d.metadata else "") + "]"
        imgs = [p for p in d.metadata.get("images", "").split("|") if p]
        fig_text = ""
        if imgs:
            available_images.extend(imgs)
            fig_text = "\nImagens deste trecho:\n" + "\n".join(f"[FIGURA: {p}]" for p in imgs)
        context_parts.append(f"{header}\n{d.page_content}{fig_text}")

    context = "\n\n".join(context_parts)
    answer = llm.invoke(
        [SystemMessage(SYSTEM_PROMPT.format(context=context)), *state["messages"][-7:]]
    )
    raw_text = text_of(answer.content).strip()

    # Extrai imagens mencionadas inline na resposta [IMG: caminho]
    inline_imgs = re.findall(r"\[IMG:\s*([^\]]+)\]", raw_text)
    inline_imgs = [img.strip() for img in inline_imgs if img.strip() in available_images]

    # Se o LLM não colocou tags inline, usa pick_images como fallback
    fallback_imgs = pick_images(state["docs"])
    images = inline_imgs if inline_imgs else fallback_imgs

    sources = sorted({d.metadata["source"] for d in state["docs"]})
    text = f"{raw_text}\n\n📚 Fontes: {', '.join(sources)}"
    cache.put(state["query"], text, images)
    return {"messages": [AIMessage(text)], "images": images}


def not_found(state: State) -> dict:
    return {"messages": [AIMessage(NOT_FOUND)]}


def build_graph():
    g = StateGraph(State)
    g.add_node("rewrite", rewrite)
    g.add_node("lookup", lookup)
    g.add_node("from_cache", from_cache)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.add_node("not_found", not_found)
    g.add_edge(START, "rewrite")
    g.add_edge("rewrite", "lookup")
    g.add_conditional_edges("lookup", route_cache, ["from_cache", "retrieve"])
    g.add_edge("from_cache", END)
    g.add_conditional_edges("retrieve", route, ["generate", "not_found"])
    g.add_edge("generate", END)
    g.add_edge("not_found", END)
    # Memória por conversa (thread_id = chat_id do Telegram)
    return g.compile(checkpointer=MemorySaver())
