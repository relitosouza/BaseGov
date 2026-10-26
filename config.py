import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
MANUALS_DIR = BASE_DIR / "manuals"
CHROMA_DIR = BASE_DIR / "chroma_db"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "nvidia")  # nvidia | anthropic
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "180"))  # segundos
LLM_FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("LLM_FALLBACK_MODELS", "gemini-2.5-flash,gemini-2.5-flash-lite").split(",")
    if m.strip()
]  # só usados com LLM_PROVIDER=gemini
LLM_MODEL = os.getenv("LLM_MODEL", "meta/llama-3.2-90b-vision-instruct")
# Embeddings locais e multilíngues (bom para português)
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 150
TOP_K = 6
MIN_SCORE = 0.25  # abaixo disso o trecho é considerado irrelevante

# Imagens: PDFs originais (só para extrair figuras, não são indexados como texto)
PDFS_DIR = BASE_DIR / "pdfs"
IMAGES_DIR = BASE_DIR / "images"
MAX_IMAGES = 4  # por resposta
IMAGE_DOCS = 2  # de quantos trechos (os mais relevantes) vêm as imagens
IMAGE_SCORE_MARGIN = 0.05  # só trechos quase tão relevantes quanto o melhor
