from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
import os

BOT_TOKEN = "8979878132:AAG6uzUr78J4-nNh_TW7g4hxYglKyrVZNo4"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# دکمه MiniApp
keyboard = InlineKeyboardMarkup().add(
    InlineKeyboardButton(
        text="🎮 باز کردن MiniApp",
        web_app=WebAppInfo(url="https://telegram-game-bot-production-09c2.up.railway.app")
    )
)

# هندلر /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("به MiniApp خوش آمدی!", reply_markup=keyboard)

# دریافت داده از MiniApp
@dp.message_handler(content_types=["web_app_data"])
async def receive_data(message: types.Message):
    await message.answer(f"داده دریافت شد: {message.web_app_data.data}")

# ====================== FastAPI ======================
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot is running"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return {"ok": True}

# ست کردن webhook موقع استارت
@app.on_event("startup")
async def on_startup():
    webhook_url = "https://telegram-game-bot-production-09c2.up.railway.app/webhook"
    await bot.set_webhook(webhook_url)
    print(f"Webhook set to: {webhook_url}")
