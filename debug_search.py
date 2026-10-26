"""Mostra os trechos que a busca recupera para uma pergunta.
Uso: python debug_search.py "sua pergunta"
"""
import sys

from langchain_chroma import Chroma

import config
from ingest import get_embeddings

query = " ".join(sys.argv[1:]) or input("Pergunta: ")
store = Chroma(
    persist_directory=str(config.CHROMA_DIR),
    embedding_function=get_embeddings(),
    collection_metadata={"hnsw:space": "cosine"},
)
for doc, score in store.similarity_search_with_relevance_scores(query, k=8):
    mark = "OK " if score >= config.MIN_SCORE else "-- "
    print(f"{mark}{score:.2f} [{doc.metadata.get('source')}]")
    print("   ", doc.page_content[:300].replace("\n", " "), "\n")
