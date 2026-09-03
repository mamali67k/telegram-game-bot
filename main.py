import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
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
MINIAPP_URL = f"{WEBAPP_URL}/app"          # آدرس صحیح مینی‌اپ

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# =========================================================
# LOGGING
# =========================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================
# BOT
# =========================================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 ورود به مینی‌اپ",
            web_app=WebAppInfo(url=MINIAPP_URL)   # ← اینجا اصلاح شد
        )]
    ])
    await message.answer(
        "سلام! 👋\nبرای ورود به دنیای حرفه‌ای‌ها روی دکمه زیر بزن:",
        reply_markup=keyboard
    )

# =========================================================
# FASTAPI
# =========================================================
app = FastAPI()

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logger.exception("Webhook error")
        return {"ok": False}

@app.api_route("/", methods=["GET", "HEAD"])
async def health():
    return {"status": "Bot is alive ✅"}

# =========================================================
# MINI APP
# =========================================================
@app.get("/app", response_class=HTMLResponse)
async def mini_app():
    html = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Pro Arena</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Vazirmatn', sans-serif;
        }

        body {
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: white;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
        }

        .header {
            width: 100%;
            max-width: 420px;
            text-align: center;
            margin-top: 30px;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(90deg, #00d2ff, #3a7bd5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }

        .header p {
            color: #a0aec0;
            font-size: 14px;
        }

        .profile-card {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 24px;
            width: 100%;
            max-width: 420px;
            text-align: center;
            margin-bottom: 30px;
        }

        .avatar {
            width: 90px;
            height: 90px;
            border-radius: 50%;
            border: 3px solid #3a7bd5;
            object-fit: cover;
            margin-bottom: 16px;
        }

        .name {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .username {
            color: #a0aec0;
            font-size: 14px;
            margin-bottom: 16px;
        }

        .badge {
            display: inline-block;
            background: linear-gradient(90deg, #ff6a00, #ee0979);
            padding: 6px 16px;
            border-radius: 50px;
            font-size: 13px;
            font-weight: 600;
        }

        .menu {
            width: 100%;
            max-width: 420px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        .menu-btn {
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 20px 10px;
            text-align: center;
            color: white;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
        }

        .menu-btn:active {
            transform: scale(0.97);
            background: rgba(255, 255, 255, 0.12);
        }

        .menu-btn span {
            display: block;
            font-size: 24px;
            margin-bottom: 8px;
        }

        .coming {
            opacity: 0.5;
            font-size: 11px;
            margin-top: 4px;
            color: #a0aec0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Pro Arena</h1>
        <p>دنیای رقابت حرفه‌ای‌ها</p>
    </div>

    <div class="profile-card">
        <img id="avatar" class="avatar" src="" alt="avatar">
        <div class="name" id="name">در حال بارگذاری...</div>
        <div class="username" id="username"></div>
        <div class="badge">تازه‌وارد</div>
    </div>

    <div class="menu">
        <div class="menu-btn">
            <span>⚔️</span>
            جنگ‌ها
            <div class="coming">به زودی</div>
        </div>
        <div class="menu-btn">
            <span>👥</span>
            گروه‌ها
            <div class="coming">به زودی</div>
        </div>
        <div class="menu-btn">
            <span>🏆</span>
            فصل‌ها
            <div class="coming">به زودی</div>
        </div>
        <div class="menu-btn">
            <span>💰</span>
            اقتصاد
            <div class="coming">به زودی</div>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();

        const user = tg.initDataUnsafe?.user;

        if (user) {
            document.getElementById('name').innerText = 
                (user.first_name || '') + (user.last_name ? ' ' + user.last_name : '');
            document.getElementById('username').innerText = 
                user.username ? '@' + user.username : 'بدون یوزرنیم';

            if (user.photo_url) {
                document.getElementById('avatar').src = user.photo_url;
            } else {
                const letter = (user.first_name || 'U')[0];
                document.getElementById('avatar').src = 
                    `https://via.placeholder.com/90x90/3a7bd5/ffffff?text=${letter}`;
            }
        } else {
            document.getElementById('name').innerText = 'کاربر مهمان';
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)

# =========================================================
# STARTUP
# =========================================================
@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
