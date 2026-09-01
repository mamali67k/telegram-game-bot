from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
import asyncio

BOT_TOKEN = "توکن_ربات_خودت"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# MiniApp Button
keyboard = InlineKeyboardMarkup().add(
    InlineKeyboardButton(
        text="🎮 باز کردن MiniApp",
        web_app=WebAppInfo(url="https://telegram-game-bot-production-09c2.up.railway.app")
    )
)

# /start handler
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("به MiniApp خوش آمدی!", reply_markup=keyboard)

# Receive data from MiniApp
@dp.message_handler(content_types=["web_app_data"])
async def receive_data(message: types.Message):
    await message.answer(f"داده دریافت شد: {message.web_app_data.data}")

# FastAPI app
app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    webhook_url = "https://telegram-game-bot-production-09c2.up.railway.app/webhook"
    await bot.set_webhook(webhook_url)
