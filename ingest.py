"""Lê os manuais em ./manuals e cria o índice vetorial. Rode após adicionar/alterar manuais."""
import shutil

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

import cache
import config
import images

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


HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]


def is_toc(text: str) -> bool:
    """Sumário: maioria das linhas são links markdown de índice."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    links = [l for l in lines if l.lstrip("- ").startswith("[")]
    return bool(lines) and len(links) / len(lines) > 0.5


def load_pdfs():
    if not config.PDFS_DIR.exists():
        return []
    return [images.PdfImages(p) for p in sorted(config.PDFS_DIR.glob("*.pdf"))]


def split_documents(docs, pdfs=()):
    """Markdown é dividido por seção (título + corpo juntos); o resto, por tamanho.

    Se houver PDFs originais em ./pdfs, as figuras de cada seção são extraídas e
    guardadas no metadado "images" do trecho.
    """
    size = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
    )
    md = MarkdownHeaderTextSplitter(HEADERS, strip_headers=False)
    chunks = []
    for d in docs:
        if not d.metadata["source"].lower().endswith(".md"):
            chunks += size.split_documents([d])
            continue
        sections = [
            s for s in md.split_text(d.page_content)
            if not (is_toc(s.page_content) or s.metadata.get("h2") == "Sumário")
        ]
        titles = [
            next((s.metadata[k] for k in ("h3", "h2", "h1") if k in s.metadata), "")
            for s in sections
        ]
        pdf, positions = images.best_match(titles, list(pdfs))
        figures = pdf.render(positions, config.IMAGES_DIR) if pdf else [[]] * len(sections)
        if pdf:
            print(f"{d.metadata['source']}: {sum(map(len, figures))} imagens de {pdf.path.name}")
        for sec, figs in zip(sections, figures):
            sec.metadata["source"] = d.metadata["source"]
            sec.metadata["images"] = "|".join(figs)
            path = " > ".join(
                sec.metadata[k] for k in ("h1", "h2", "h3") if k in sec.metadata
            )
            sec.page_content = f"[{path}]\n{sec.page_content}" if path else sec.page_content
            chunks += size.split_documents([sec])
    return chunks


def main():
    docs = load_documents()
    if not docs:
        raise SystemExit(f"Nenhum manual encontrado em {config.MANUALS_DIR}")
    shutil.rmtree(config.IMAGES_DIR, ignore_errors=True)
    chunks = split_documents(docs, load_pdfs())
    shutil.rmtree(config.CHROMA_DIR, ignore_errors=True)
    Chroma.from_documents(
        chunks,
        get_embeddings(),
        persist_directory=str(config.CHROMA_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )
    cache.clear()  # respostas antigas podem estar desatualizadas
    print(f"Indexados {len(chunks)} trechos de {len(docs)} páginas/arquivos.")


if __name__ == "__main__":
    main()
