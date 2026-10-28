import logging
import os
import re

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


async def send_response_with_images(update: Update, text: str, fallback_images: list[str]):
    """Envia o passo a passo intercalando cada texto com a sua respectiva imagem."""
    # Divide o texto pelos marcadores [IMG: caminho]
    parts = re.split(r"\[IMG:\s*([^\]]+)\]", text)
    sent_images = set()

    # Se o texto tem tags [IMG: ...]
    if len(parts) > 1:
        # parts alterna entre: [texto_0, img_path_1, texto_1, img_path_2, texto_2, ...]
        for i, piece in enumerate(parts):
            if i % 2 == 0:
                clean_text = piece.strip()
                if clean_text:
                    for chunk_idx in range(0, len(clean_text), 4000):
                        await update.message.reply_text(clean_text[chunk_idx : chunk_idx + 4000])
            else:
                img_path = piece.strip()
                file_path = config.BASE_DIR / img_path
                if file_path.exists():
                    try:
                        with open(file_path, "rb") as photo:
                            await update.message.reply_photo(photo=photo)
                        sent_images.add(img_path)
                    except Exception:
                        log.exception("Falha ao enviar imagem inline %s", img_path)
        return

    # Fallback caso o modelo não tenha gerado tags inline: envia texto e depois fotos
    clean_text = text.strip()
    for i in range(0, len(clean_text), 4000):
        await update.message.reply_text(clean_text[i : i + 4000])

    files = [config.BASE_DIR / p for p in fallback_images]
    files = [f for f in files if f.exists()]
    total = len(files)
    for idx, f in enumerate(files, start=1):
        try:
            caption = f"Figura {idx} de {total}" if total > 1 else None
            with open(f, "rb") as photo:
                await update.message.reply_photo(photo=photo, caption=caption)
        except Exception:
            log.exception("Falha ao enviar imagem fallback %s", f)


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

    await send_response_with_images(update, text, images)


def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))
    app.run_polling()


if __name__ == "__main__":
    main()
