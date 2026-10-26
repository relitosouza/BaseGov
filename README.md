# BaseGov – Chatbot de manuais (LangGraph + Telegram)

Lê os manuais do sistema (PDF/MD/TXT) e responde perguntas dos usuários pelo Telegram.

## Uso
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencha TELEGRAM_BOT_TOKEN e ANTHROPIC_API_KEY
# coloque os manuais em ./manuals/
python ingest.py       # reindexe ao alterar manuais
python bot.py
```

## Imagens nas respostas
Os manuais em `.md` não trazem as figuras. Para o bot enviá-las junto com a resposta:
1. Coloque o **PDF original** em `pdfs/` (ele só serve para extrair figuras; o texto continua vindo do `.md`).
2. Rode `python ingest.py`. Ele liga cada figura à seção do `.md` cujo título aparece antes dela no PDF.
3. Ao responder, o bot envia as figuras da seção mais relevante (`MAX_IMAGES`, `IMAGE_DOCS`, `IMAGE_SCORE_MARGIN` em `config.py`).
