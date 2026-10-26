"""Cache de respostas em SQLite: pergunta repetida não gasta tokens do LLM."""
import json
import re
import sqlite3
import unicodedata

import config

_DB = config.BASE_DIR / "cache.db"


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(_DB)
    con.execute(
        "CREATE TABLE IF NOT EXISTS answers ("
        "key TEXT PRIMARY KEY, answer TEXT NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    try:  # bancos criados antes de existir o suporte a imagens
        con.execute("ALTER TABLE answers ADD COLUMN images TEXT NOT NULL DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass
    return con


def normalize(question: str) -> str:
    """minúsculas, sem acento, sem pontuação, espaços únicos."""
    s = unicodedata.normalize("NFKD", question.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def get(question: str) -> tuple[str, list[str]] | None:
    key = normalize(question)
    if not key:
        return None
    with _connect() as con:
        row = con.execute(
            "SELECT answer, images FROM answers WHERE key = ?", (key,)
        ).fetchone()
    return (row[0], json.loads(row[1])) if row else None


def put(question: str, answer: str, images: list[str] | None = None) -> None:
    key = normalize(question)
    if not key:
        return
    with _connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO answers (key, answer, images) VALUES (?, ?, ?)",
            (key, answer, json.dumps(images or [])),
        )


def clear() -> None:
    """Chamado pelo ingest.py: manuais mudaram, respostas antigas ficam inválidas."""
    with _connect() as con:
        con.execute("DELETE FROM answers")
