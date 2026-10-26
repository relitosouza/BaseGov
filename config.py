import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
MANUALS_DIR = BASE_DIR / "manuals"
CHROMA_DIR = BASE_DIR / "chroma_db"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "nvidia")  # nvidia | anthropic
LLM_MODEL = os.getenv("LLM_MODEL", "meta/llama-3.2-90b-vision-instruct")
# Embeddings locais e multilíngues (bom para português)
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
TOP_K = 4
MIN_SCORE = 0.25  # abaixo disso o trecho é considerado irrelevante
