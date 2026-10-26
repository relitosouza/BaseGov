"""Lê os manuais em ./manuals e cria o índice vetorial. Rode após adicionar/alterar manuais."""
import shutil

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config

LOADERS = {
    ".pdf": lambda p: PyPDFLoader(str(p)),
    ".md": lambda p: TextLoader(str(p), encoding="utf-8"),
    ".txt": lambda p: TextLoader(str(p), encoding="utf-8"),
}


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def load_documents():
    docs = []
    for path in sorted(config.MANUALS_DIR.rglob("*")):
        loader = LOADERS.get(path.suffix.lower())
        if not loader:
            continue
        for d in loader(path).load():
            d.metadata["source"] = path.name
            docs.append(d)
        print(f"Lido: {path.name}")
    return docs


def main():
    docs = load_documents()
    if not docs:
        raise SystemExit(f"Nenhum manual encontrado em {config.MANUALS_DIR}")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(docs)
    shutil.rmtree(config.CHROMA_DIR, ignore_errors=True)
    Chroma.from_documents(
        chunks,
        get_embeddings(),
        persist_directory=str(config.CHROMA_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )
    print(f"Indexados {len(chunks)} trechos de {len(docs)} páginas/arquivos.")


if __name__ == "__main__":
    main()
