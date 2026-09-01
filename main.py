from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils import executor
import os

# 🔑 توکن رباتت را اینجا قرار بده
BOT_TOKEN = "توکن_ربات_خودت"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# 🎮 دکمهٔ MiniApp
keyboard = InlineKeyboardMarkup().add(
    InlineKeyboardButton(
        text="🎮 باز کردن MiniApp",
        web_app=WebAppInfo(url="https://telegram-game-bot-production-09c2.up.railway.app")
    )
)

# 🧩 هندلر شروع
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("به MiniApp خوش آمدی!", reply_markup=keyboard)

# 📨 دریافت داده از MiniApp
@dp.message_handler(content_types=["web_app_data"])
async def receive_data(message: types.Message):
    data = message.web_app_data.data
    await message.answer(f"✅ داده از MiniApp دریافت شد: {data}")

# 🚀 اجرای ربات
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
