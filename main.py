```python
import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo


# ============================================================
# SETTINGS
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://telegram-game-bot-production-09c2.up.railway.app"
).rstrip("/")

WEBHOOK_URL = f"{WEBAPP_URL}/webhook"


# ============================================================
# SAFETY CHECK
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")


# ============================================================
# TELEGRAM
# ============================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI()


# ============================================================
# TELEGRAM /START
# ============================================================

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):

    keyboard = InlineKeyboardMarkup()

    keyboard.add(
        InlineKeyboardButton(
            "Open Mini App",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    )

    await message.answer(
        "Open the Mini App:",
        reply_markup=keyboard
    )


# ============================================================
# MINI APP DATA
# ============================================================

@dp.message_handler(content_types=types.ContentType.WEB_APP_DATA)
async def web_app_data_handler(message: types.Message):

    await message.answer(
        f"Received: {message.web_app_data.data}"
    )


# ============================================================
# WEBSITE / MINI APP
# ============================================================

@app.get("/")
async def root():

    return FileResponse("index.html")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "ok"
    }


# ============================================================
# WEBHOOK DIAGNOSTIC
# ============================================================

@app.get("/webhook-info")
async def webhook_info():

    info = await bot.get_webhook_info()

    return {
        "url": info.url,
        "has_custom_certificate": info.has_custom_certificate,
        "pending_update_count": info.pending_update_count,
        "last_error_date": info.last_error_date,
        "last_error_message": info.last_error_message,
        "max_connections": info.max_connections
    }


# ============================================================
# TELEGRAM WEBHOOK
# ============================================================

@app.post("/webhook")
async def webhook(request: Request):

    data = await request.json()

    update = types.Update(**data)

    await dp.process_update(update)

    return {
        "ok": True
    }


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def on_startup():

    await bot.set_webhook(
        WEBHOOK_URL
    )

    print(
        f"Webhook set to: {WEBHOOK_URL}"
    )


# ============================================================
# SHUTDOWN
# ============================================================

@app.on_event("shutdown")
async def on_shutdown():

    await bot.delete_webhook()

    await bot.close()
```
