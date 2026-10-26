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
