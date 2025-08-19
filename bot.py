import os
import re
import logging
from langdetect import detect
from deep_translator import GoogleTranslator
import language_tool_python
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]

# ------- Grammar tool (LanguageTool public API: free but rate-limited) -------
LT = language_tool_python.LanguageToolPublicAPI('en-US')

# ------- Translator (Google Translate via deep-translator, free) -------
translator = GoogleTranslator(source='en', target='fa')

MAX_LEN = 4096  # Telegram message limit safeguard

def extract_english(text: str) -> str:
    """Pick out English sentences; fall back to ASCII-only if unsure."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    eng = []
    for p in parts:
        t = p.strip()
        if not t:
            continue
        try:
            if detect(t) == "en":
                eng.append(t)
        except Exception:
            pass
    if eng:
        return " ".join(eng)
    # fallback: keep characters that look English-ish
    ascii_only = "".join(ch for ch in text if ch.isascii())
    return ascii_only.strip() or text

async def cmd_g(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.reply_to_message or not (msg.reply_to_message.text or msg.reply_to_message.caption):
        await msg.reply_text("Reply to a *text* message with /g.", parse_mode="Markdown")
        return
    original = (msg.reply_to_message.text or msg.reply_to_message.caption).strip()
    try:
        matches = LT.check(original)
        corrected = language_tool_python.utils.correct(original, matches)
        if corrected.strip() == original.strip():
            await msg.reply_text("Looks good ✅ No grammar issues found.")
        else:
            out = corrected[:MAX_LEN]
            await msg.reply_text(out)
    except Exception as e:
        logging.exception("Grammar check failed")
        await msg.reply_text("Sorry, I couldn't check this right now.")

async def cmd_tr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.reply_to_message or not (msg.reply_to_message.text or msg.reply_to_message.caption):
        await msg.reply_text("Reply to an *English* text message with /tr.", parse_mode="Markdown")
        return
    original = (msg.reply_to_message.text or msg.reply_to_message.caption).strip()
    english = extract_english(original)
    try:
        # Only translate if it looks like English
        try:
            if detect(english) != "en":
                await msg.reply_text("That doesn't look like English.")
                return
        except Exception:
            pass
        fa = translator.translate(english)[:MAX_LEN]
        await msg.reply_text(fa)
    except Exception:
        logging.exception("Translation failed")
        await msg.reply_text("Sorry, I couldn't translate this right now.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Add me to a group and use:\n"
        "/g (reply) → grammar fix\n"
        "/tr (reply) → English → Persian"
    )

def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("g", cmd_g))
    app.add_handler(CommandHandler("tr", cmd_tr))
    return app

if __name__ == "__main__":
    app = build_app()
    port = int(os.environ.get("PORT", "8080"))
    # If you want to use polling instead of webhook (simpler for local dev):
    app.run_polling()
