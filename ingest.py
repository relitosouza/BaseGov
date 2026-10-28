"""Lê os manuais (.md em ./manuals ou .pdf em ./pdfs) e cria o índice vetorial.
Extrai e vincula imagens automaticamente aos trechos dos manuais.
"""
from collections import defaultdict
from pathlib import Path
import re
import shutil
import unicodedata

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

import cache
import config
import images

MIN_W, MIN_H = 80, 40
MAX_PAGES_PER_IMAGE = 2
HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def is_toc(text: str) -> bool:
    """Sumário: maioria das linhas são links markdown de índice."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    links = [l for l in lines if l.lstrip("- ").startswith("[")]
    return bool(lines) and len(links) / len(lines) > 0.5


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"\W+", "_", s).strip("_") or "doc"


def load_pdfs():
    if not config.PDFS_DIR.exists():
        return []
    return [images.PdfImages(p) for p in sorted(config.PDFS_DIR.glob("*.pdf"))]


def process_markdown_manuals(pdfs=()):
    """Processa manuais estruturados em .md e casa com os PDFs se existirem."""
    if not config.MANUALS_DIR.exists():
        return [], set()

    size = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
    )
    md_splitter = MarkdownHeaderTextSplitter(HEADERS, strip_headers=False)
    chunks = []
    matched_pdfs = set()

    for path in sorted(config.MANUALS_DIR.glob("*.md")):
        docs = TextLoader(str(path), encoding="utf-8").load()
        for d in docs:
            sections = [
                s for s in md_splitter.split_text(d.page_content)
                if not (is_toc(s.page_content) or s.metadata.get("h2") == "Sumário")
            ]
            titles = [
                next((s.metadata[k] for k in ("h3", "h2", "h1") if k in s.metadata), "")
                for s in sections
            ]
            pdf, positions = images.best_match(titles, list(pdfs))
            if pdf:
                matched_pdfs.add(pdf.path.resolve())
            figures = pdf.render(positions, config.IMAGES_DIR) if pdf else [[]] * len(sections)
            if pdf:
                print(f"{path.name}: {sum(map(len, figures))} imagens associadas de {pdf.path.name}")
            for sec, figs in zip(sections, figures):
                sec.metadata["source"] = path.name
                sec.metadata["images"] = "|".join(figs)
                header_path = " > ".join(
                    sec.metadata[k] for k in ("h1", "h2", "h3") if k in sec.metadata
                )
                sec.page_content = f"[{header_path}]\n{sec.page_content}" if header_path else sec.page_content
                chunks += size.split_documents([sec])
        print(f"Lido Markdown: {path.name}")
    return chunks, matched_pdfs


def process_pdf_directly(pdf_path: Path) -> list[Document]:
    """Lê um PDF diretamente, extrai o texto página a página e salva/vincula as imagens."""
    doc = fitz.open(pdf_path)
    pages_of = defaultdict(set)
    page_images = defaultdict(list)

    # Identifica imagens e remove logotipos/cabeçalhos repetidos
    for pno, page in enumerate(doc):
        for img in page.get_images(full=True):
            xref = img[0]
            for r in page.get_image_rects(xref):
                if r.width >= MIN_W and r.height >= MIN_H:
                    pages_of[xref].add(pno)
                    page_images[pno].append((xref, tuple(r)))

    slug = slugify(pdf_path.stem)
    config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    size = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
    )
    chunks = []
    total_imgs = 0

    for pno, page in enumerate(doc):
        text = page.get_text("text").strip()
        if not text:
            continue
        # Ignora páginas puramente de sumário que atraem buscas sem ter o conteúdo
        if "SUMÁRIO" in text.upper() and ("....." in text or "····" in text):
            continue

        # Filtra imagens válidas não repetitivas
        valid_rects = [
            rect for xref, rect in page_images[pno]
            if len(pages_of[xref]) <= MAX_PAGES_PER_IMAGE
        ]

        saved_img_paths = []
        for idx, rect_coords in enumerate(valid_rects):
            rect = fitz.Rect(rect_coords)
            img_file = config.IMAGES_DIR / f"{slug}_p{pno+1}_{idx+1}.png"
            page.get_pixmap(clip=rect, dpi=130).save(img_file)
            saved_img_paths.append(img_file.relative_to(config.BASE_DIR).as_posix())
            total_imgs += 1

        doc_page = Document(
            page_content=text,
            metadata={
                "source": pdf_path.name,
                "page": pno,
                "images": "|".join(saved_img_paths),
            },
        )
        sub_chunks = size.split_documents([doc_page])
        chunks.extend(sub_chunks)

    print(f"Lido PDF direto: {pdf_path.name} ({len(doc)} págs, {total_imgs} imagens)")
    return chunks


def main():
    config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(config.IMAGES_DIR, ignore_errors=True)
    config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    pdf_objects = load_pdfs()
    chunks, matched_pdfs = process_markdown_manuals(pdf_objects)

    # Processa todos os PDFs em pdfs/ que não foram absorvidos por um .md em manuals/
    all_pdfs = sorted(config.PDFS_DIR.glob("*.pdf")) if config.PDFS_DIR.exists() else []
    for p in all_pdfs:
        if p.resolve() not in matched_pdfs:
            chunks.extend(process_pdf_directly(p))

    if not chunks:
        raise SystemExit(f"Nenhum manual encontrado em {config.MANUALS_DIR} ou {config.PDFS_DIR}")

    shutil.rmtree(config.CHROMA_DIR, ignore_errors=True)
    Chroma.from_documents(
        chunks,
        get_embeddings(),
        persist_directory=str(config.CHROMA_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )
    cache.clear()
    print(f"\nFinalizado! Indexados {len(chunks)} trechos de todos os manuais e PDFs.")


if __name__ == "__main__":
    main()
