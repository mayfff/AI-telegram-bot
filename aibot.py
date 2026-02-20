import os
import logging
import re
from dotenv import load_dotenv
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from google import genai
from google.genai import errors as genai_errors


# =======================
# Environment & Config
# =======================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.ERROR,
)

logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)

MENU, PROMPT = range(2)

MAIN_KB = ReplyKeyboardMarkup(
    [
        ["Студент", "IT-технології"],
        ["Контакти", "Prompt Gemini"],
    ],
    resize_keyboard=True,
)

MENU_CHOICES = {"Студент", "IT-технології", "Контакти", "Prompt Gemini"}

gclient = genai.Client(api_key=GEMINI_API_KEY)

MAX_TG_LEN = 4000
user_states: dict[int, int] = {}


# =======================
# State Management
# =======================

def get_state(user_id: int) -> int:
    return user_states.get(user_id, MENU)


def set_state(user_id: int, state: int) -> None:
    user_states[user_id] = state


# =======================
# Helpers
# =======================

def split_for_telegram(text: str, max_len: int = MAX_TG_LEN):
    chunks = []
    current = ""

    for paragraph in text.split("\n"):
        if len(paragraph) > max_len:
            if current:
                chunks.append(current)
            current = ""
            for i in range(0, len(paragraph), max_len):
                chunks.append(paragraph[i:i + max_len])
            continue

        if len(current) + len(paragraph) + 1 <= max_len:
            current += ("\n" if current else "") + paragraph
        else:
            if current:
                chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def format_markdown(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = re.sub(r"^#{1,6}\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"([_\[\]()~`>#+\-=|{}.!])", r"\\\1", text)
    return text


# =======================
# Handlers
# =======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    set_state(user.id, MENU)

    logger.info("Incoming /start from %s (%s)", user.id, user.username)

    await update.message.reply_text(
        f"Привіт, {user.first_name or 'друже'}! Обери пункт меню:",
        reply_markup=MAIN_KB,
    )


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    txt = (update.message.text or "").strip()

    if txt == "Студент":
        await update.message.reply_text(
            "Студент: Закревський Данило\n"
            "Група: ІО-24\n"
            "Спеціальність: 123 Комп'ютерна інженерія",
            reply_markup=MAIN_KB,
        )
        return

    if txt == "IT-технології":
        await update.message.reply_text(
            "Використано: Python 3.10, google-genai 1.50.1, python-telegram-bot 22.5.",
            reply_markup=MAIN_KB,
        )
        return

    if txt == "Контакти":
        await update.message.reply_text(
            "Тел.: +380 95 391 56 18\n"
            "E-mail: io24zakrevsky@gmail.com",
            reply_markup=MAIN_KB,
        )
        return

    if txt == "Prompt Gemini":
        set_state(user.id, PROMPT)
        await update.message.reply_text(
            "Надішли свій запит для Gemini (одним повідомленням).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await update.message.reply_text(
        "Будь ласка, обери пункт меню:",
        reply_markup=MAIN_KB,
    )
    set_state(user.id, MENU)


async def prompt_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_prompt = (update.message.text or "").strip()

    logger.info(
        "Incoming Gemini prompt from %s (%s): %s",
        user.id,
        user.username,
        user_prompt,
    )

    if not user_prompt:
        await update.message.reply_text("Надішли, будь ласка, текст запиту.")
        return

    await update.message.chat.send_action("typing")

    try:
        resp = gclient.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
        )

        answer = (getattr(resp, "text", "") or "").strip()

        if not answer:
            answer = "Вибач, не вдалося отримати відповідь від моделі."

    except genai_errors.ServerError as e:
        code = getattr(e, "status_code", None) or getattr(e, "code", None)
        logger.error("Gemini ServerError (%s): %s", code, e, exc_info=True)

        if code == 503:
            answer = (
                "🤖 Модель Gemini зараз перевантажена (помилка 503).\n"
                "Спробуй, будь ласка, ще раз трохи пізніше."
            )
        else:
            answer = f"Серверна помилка Gemini: {e}"

    except Exception as e:
        logger.error("Gemini error: %s", e, exc_info=True)
        answer = f"Сталася помилка під час звернення до Gemini: {e}"

    chunks = split_for_telegram(answer)

    for i, chunk in enumerate(chunks):
        formatted = format_markdown(chunk)

        if i == len(chunks) - 1:
            await update.message.reply_text(
                formatted,
                reply_markup=MAIN_KB,
                parse_mode="MarkdownV2",
            )
        else:
            await update.message.reply_text(
                formatted,
                parse_mode="MarkdownV2",
            )

    set_state(user.id, MENU)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    text = (update.message.text or "").strip()

    logger.info(
        "Incoming text from %s (%s): %s",
        user.id,
        user.username,
        text,
    )

    state = get_state(user.id)

    if text in MENU_CHOICES:
        set_state(user.id, MENU)
        await menu_router(update, context)
        return

    if state == PROMPT:
        await prompt_gemini(update, context)
        return

    await update.message.reply_text(
        "Будь ласка, обери пункт меню:",
        reply_markup=MAIN_KB,
    )
    set_state(user.id, MENU)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info("Incoming /cancel from %s (%s)", user.id, user.username)

    set_state(user.id, MENU)

    await update.message.reply_text(
        "Готово. Повертаю в меню.",
        reply_markup=MAIN_KB,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info("Incoming /help from %s (%s)", user.id, user.username)

    await update.message.reply_text(
        "Меню: Студент / IT-технології / Контакти / Prompt Gemini.\n"
        "Команди: /start, /help, /cancel"
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(
        "Exception while handling an update: %s",
        context.error,
        exc_info=True,
    )


# =======================
# Main
# =======================

def main():
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        raise RuntimeError(
            "Будь ласка, заповни TELEGRAM_TOKEN та GEMINI_API_KEY у .env"
        )

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.add_error_handler(error_handler)

    logger.info("🤖 Бот успішно запущений і очікує повідомлень.")

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()