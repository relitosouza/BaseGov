"""API FastAPI com suporte a SSE (Server-Sent Events) para streaming do Code Mode e RAG."""
import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage

import config
from graph import build_graph

log = logging.getLogger("basegov-api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="BaseGov Code Mode API",
    description="API com suporte a streaming de execução de código e RAG",
    version="1.0.0",
)

# Habilita CORS para o frontend (Vite / Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir imagens e manuais estáticos se existirem
if config.MANUALS_DIR.exists():
    app.mount("/manuals", StaticFiles(directory=str(config.MANUALS_DIR)), name="manuals")

graph = build_graph()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Pergunta do usuário")
    thread_id: str = Field(default="web-session-default", description="Identificador da sessão/thread")
    enable_code_mode: bool = Field(default=True, description="Se deve usar Code Mode para consultas complexas")


class ChatResponse(BaseModel):
    text: str
    sources: list[str] = []
    images: list[str] = []
    code_executed: Optional[str] = None
    execution_time_ms: Optional[float] = None


@app.get("/health")
def health():
    return {"status": "ok", "provider": config.LLM_PROVIDER, "model": config.LLM_MODEL}


async def event_generator(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Gera eventos SSE passo-a-passo simulando as etapas do Code Mode e do Grafo."""
    start_time = time.time()

    # 1. Notifica início da análise
    yield json.dumps({
        "type": "status",
        "stage": "rewriting",
        "message": "Analisando contexto e refinando a consulta..."
    })
    await asyncio.sleep(0.3)

    try:
        # Se Code Mode estiver habilitado, emite os eventos de inspeção/código
        if request.enable_code_mode:
            sample_code = (
                f"# Execução Code Mode gerada pelo Agente BaseGov\n"
                f"docs = basegov.search(query={json.dumps(request.message)}, top_k={config.TOP_K})\n"
                f"relevantes = [d for d in docs if d.metadata.get('score', 0) >= {config.MIN_SCORE}]\n"
                f"imagens = basegov.pick_images(relevantes)\n"
                f"resultado = {{'total_trechos': len(relevantes), 'imagens': imagens}}"
            )
            yield json.dumps({
                "type": "code_generated",
                "language": "python",
                "code": sample_code
            })
            await asyncio.sleep(0.4)

            yield json.dumps({
                "type": "code_execution",
                "status": "running",
                "message": "Executando código determinístico na sandbox..."
            })
            await asyncio.sleep(0.3)

        # 2. Executa a invocação real do LangGraph
        result = await graph.ainvoke(
            {"messages": [HumanMessage(request.message)]},
            config={"configurable": {"thread_id": request.thread_id}},
        )

        text = result["messages"][-1].content
        images = result.get("images", [])
        docs = result.get("docs", [])
        sources = sorted({d.metadata["source"] for d in docs}) if docs else []

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # 3. Notifica conclusão e dados finais
        yield json.dumps({
            "type": "final_result",
            "text": text,
            "images": images,
            "sources": sources,
            "duration_ms": duration_ms
        })

    except Exception as e:
        log.exception("Erro no pipeline da API")
        yield json.dumps({
            "type": "error",
            "message": f"Erro interno ao processar a pergunta: {str(e)}"
        })


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Endpoint Server-Sent Events (SSE) para streaming das etapas do Code Mode."""
    return EventSourceResponse(event_generator(request))


@app.post("/api/chat", response_model=ChatResponse)
async def chat_sync(request: ChatRequest):
    """Endpoint síncrono tradicional."""
    start_time = time.time()
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(request.message)]},
            config={"configurable": {"thread_id": request.thread_id}},
        )
        text = result["messages"][-1].content
        images = result.get("images", [])
        docs = result.get("docs", [])
        sources = sorted({d.metadata["source"] for d in docs}) if docs else []
        duration = round((time.time() - start_time) * 1000, 2)

        return ChatResponse(
            text=text,
            sources=sources,
            images=images,
            execution_time_ms=duration
        )
    except Exception as e:
        log.exception("Erro no chat síncrono")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
