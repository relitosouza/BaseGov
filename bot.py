import logging
import os

from langchain_core.messages import HumanMessage
from telegram import InputMediaPhoto, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from graph import build_graph

logging.basicConfig(level=logging.INFO)
# evita imprimir o token do bot (vai na URL) nos logs
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("manual-bot")
DEBUG = os.getenv("DEBUG") == "1"

graph = build_graph()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Sou o assistente dos manuais do sistema. Pergunte o que precisar."
    )


async def send_images(update: Update, paths: list[str]):
    files = [config.BASE_DIR / p for p in paths]
    files = [f for f in files if f.exists()]
    try:
        if len(files) == 1:
            await update.message.reply_photo(files[0].read_bytes())
        elif files:
            await update.message.reply_media_group(
                [InputMediaPhoto(f.read_bytes()) for f in files]
            )
    except Exception:  # a resposta em texto já foi enviada; imagem é um extra
        log.exception("Falha ao enviar imagens")


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
    images: list[str] = []
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(update.message.text)]},
            config={"configurable": {"thread_id": str(chat_id)}},
        )
        text = result["messages"][-1].content
        images = result.get("images", [])
    except Exception as e:
        log.exception("Erro ao processar pergunta")
        text = "Ocorreu um erro ao processar sua pergunta. Tente novamente."
        if DEBUG:
            text += f"\n\n[debug] {type(e).__name__}: {str(e)[:500]}"
    # Telegram limita mensagens a 4096 caracteres
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i : i + 4000])
    await send_images(update, images)


def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))
    app.run_polling()


if __name__ == "__main__":
    main()
