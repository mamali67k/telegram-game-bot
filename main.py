import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://telegram-game-bot-production-09c2.up.railway.app",
).rstrip("/")
WEBHOOK_URL = f"{WEBAPP_URL}/webhook"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in Railway Variables")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
app = FastAPI()

keyboard = InlineKeyboardMarkup().add(
    InlineKeyboardButton(
        text="🎮 باز کردن MiniApp",
        web_app=WebAppInfo(url=WEBAPP_URL),
    )
)


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("به MiniApp خوش آمدی!", reply_markup=keyboard)


@dp.message_handler(content_types=["web_app_data"])
async def receive_data(message: types.Message):
    await message.answer(f"داده دریافت شد: {message.web_app_data.data}")


@app.get("/")
async def root():
    return FileResponse(Path(__file__).with_name("index.html"))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return {"ok": True}


@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook set to: {WEBHOOK_URL}")


@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    await bot.session.close()
