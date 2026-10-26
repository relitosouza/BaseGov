"""Extrai imagens dos PDFs originais e as liga às seções dos manuais em markdown.

O texto vem do .md; o PDF só serve para achar a posição de cada título e das figuras.
Cada imagem pertence à seção cujo título aparece logo antes dela no PDF.
"""
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # versões antigas do PyMuPDF
    import fitz

import config

MIN_W, MIN_H = 80, 40  # em pontos: descarta ícones e filetes
MAX_PAGES_PER_IMAGE = 2  # logotipo/cabeçalho se repete em várias páginas
MIN_MATCH = 0.5  # fração dos títulos do .md que precisa existir no PDF


def _key(text: str) -> str:
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\W+", "", s)


class PdfImages:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.doc = fitz.open(self.path)
        self.items = self._scan()  # em ordem de leitura: (página, y, tipo, dado)

    def _scan(self):
        items, pages_of = [], defaultdict(set)
        for pno, page in enumerate(self.doc):
            for block in page.get_text("dict")["blocks"]:
                if block["type"] != 0:
                    continue
                for line in block["lines"]:
                    text = "".join(sp["text"] for sp in line["spans"]).strip()
                    if text:
                        items.append((pno, line["bbox"][1], "text", text))
            for img in page.get_images(full=True):
                xref = img[0]
                for r in page.get_image_rects(xref):
                    if r.width >= MIN_W and r.height >= MIN_H:
                        items.append((pno, r.y0, "image", (xref, tuple(r))))
                        pages_of[xref].add(pno)
        items = [
            i for i in items
            if i[2] == "text" or len(pages_of[i[3][0]]) <= MAX_PAGES_PER_IMAGE
        ]
        items.sort(key=lambda i: (i[0], i[1]))
        return items

    def match(self, headings: list[str]) -> list[int | None]:
        """Posição (índice em self.items) de cada título; None se não achou."""
        texts = [(n, _key(it[3])) for n, it in enumerate(self.items) if it[2] == "text"]
        positions = []
        for h in headings:
            k, found = _key(h), None
            if k:
                for n, tk in texts:
                    # o sumário pode acrescentar o nº da página: aceita pequena sobra
                    if tk == k or (tk.startswith(k) and len(tk) <= len(k) + 4):
                        found = n  # a última ocorrência é a do corpo, não a do sumário
            positions.append(found)
        return positions

    def render(self, positions: list[int | None], out_dir: Path) -> list[list[str]]:
        """Salva as imagens como PNG e devolve, por título, os caminhos relativos."""
        starts = sorted((p, i) for i, p in enumerate(positions) if p is not None)
        result: list[list[str]] = [[] for _ in positions]
        slug = re.sub(r"\W+", "_", unicodedata.normalize("NFKD", self.path.stem)
                      .encode("ascii", "ignore").decode()).strip("_") or "manual"
        out_dir.mkdir(parents=True, exist_ok=True)
        for n, (pno, _, kind, data) in enumerate(self.items):
            if kind != "image":
                continue
            owner = None
            for p, i in starts:
                if p < n:
                    owner = i
                else:
                    break
            if owner is None:
                continue
            rect = fitz.Rect(data[1])
            file = out_dir / f"{slug}_s{owner}_{len(result[owner]) + 1}.png"
            self.doc[pno].get_pixmap(clip=rect, dpi=130).save(file)
            result[owner].append(file.relative_to(config.BASE_DIR).as_posix())
        return result


def best_match(headings: list[str], pdfs: list[PdfImages]):
    """Escolhe o PDF que contém a maioria dos títulos do manual."""
    best = None
    for pdf in pdfs:
        positions = pdf.match(headings)
        ratio = sum(p is not None for p in positions) / max(len(headings), 1)
        if ratio >= MIN_MATCH and (best is None or ratio > best[0]):
            best = (ratio, pdf, positions)
    return (best[1], best[2]) if best else (None, None)
