import logging

from langchain_core.messages import HumanMessage
from telegram import Update
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
log = logging.getLogger("manual-bot")

graph = build_graph()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Sou o assistente dos manuais do sistema. Pergunte o que precisar."
    )


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(update.message.text)]},
            config={"configurable": {"thread_id": str(chat_id)}},
        )
        text = result["messages"][-1].content
    except Exception:
        log.exception("Erro ao processar pergunta")
        text = "Ocorreu um erro ao processar sua pergunta. Tente novamente."
    # Telegram limita mensagens a 4096 caracteres
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i : i + 4000])


def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))
    app.run_polling()


if __name__ == "__main__":
    main()
