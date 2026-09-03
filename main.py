import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# =========================================================
# CONFIG
# =========================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://telegram-game-bot-production-09c2.up.railway.app"
).rstrip("/")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBAPP_URL}{WEBHOOK_PATH}"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# =========================================================
# LOGGING
# =========================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================
# BOT & DISPATCHER
# =========================================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# =========================================================
# FASTAPI
# =========================================================
app = FastAPI()

# =========================================================
# /start HANDLER
# =========================================================
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            text="🚀 Open Mini App",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    )

    await message.answer(
        "سلام! 👋\nبرای ورود به مینی‌اپ روی دکمه زیر کلیک کنید:",
        reply_markup=keyboard
    )

# =========================================================
# WEBHOOK ENDPOINT (اصلاح شده)
# =========================================================
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    # این دو خط مشکل context را حل می‌کند
    Bot.set_current(bot)
    Dispatcher.set_current(dp)

    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return {"ok": True}

# =========================================================
# HEALTH CHECK
# =========================================================
@app.get("/")
async def health():
    return {"status": "Bot is alive ✅"}

# =========================================================
# STARTUP & SHUTDOWN
# =========================================================
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set to: {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("Bot stopped")
