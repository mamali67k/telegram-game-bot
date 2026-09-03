import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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
MINIAPP_URL = f"{WEBAPP_URL}/app"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="☀️ ورود به NEXA",
            web_app=WebAppInfo(url=MINIAPP_URL)
        )]
    ])
    await message.answer(
        "به NEXA خوش آمدید ☀️\n\nدنیای رقابت، قدرت و آینده.\nبرای ورود روی دکمه زیر بزن:",
        reply_markup=keyboard
    )

# =========================================================
# FASTAPI
# =========================================================
app = FastAPI()

# سرو کردن فایل‌های static (تصاویر)
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    return {"status": "NEXA is alive ✅"}

@app.get("/app", response_class=HTMLResponse)
async def mini_app():
    html = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NEXA</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Vazirmatn', sans-serif;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            min-height: 100vh;
            color: #fff;
            background: #05051a;
            background-image:
                radial-gradient(ellipse 90% 60% at 50% -10%, rgba(255, 200, 50, 0.18), transparent 50%),
                radial-gradient(ellipse 50% 40% at 100% 30%, rgba(255, 150, 0, 0.08), transparent),
                radial-gradient(ellipse 40% 30% at 0% 70%, rgba(0, 100, 255, 0.1), transparent),
                linear-gradient(180deg, #0a0a2e 0%, #05051a 50%, #020210 100%);
            overflow-x: hidden;
            padding: 16px;
            padding-bottom: 48px;
        }

        .cosmos {
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
            overflow: hidden;
        }
        .cosmos span {
            position: absolute;
            opacity: 0.07;
            font-size: 28px;
            color: #ffd700;
        }
        .cosmos span:nth-child(1) { top: 6%; right: 8%; font-size: 36px; }
        .cosmos span:nth-child(2) { top: 18%; left: 6%; }
        .cosmos span:nth-child(3) { top: 45%; right: 5%; font-size: 32px; }
        .cosmos span:nth-child(4) { bottom: 28%; left: 8%; }
        .cosmos span:nth-child(5) { bottom: 12%; right: 15%; font-size: 24px; }
        .cosmos span:nth-child(6) { top: 70%; left: 40%; font-size: 20px; opacity: 0.05; }

        .container {
            position: relative;
            z-index: 1;
            max-width: 420px;
            margin: 0 auto;
        }

        .brand {
            text-align: center;
            padding: 24px 0 18px;
        }
        .brand-logo {
            width: 100px;
            height: 100px;
            margin: 0 auto 14px;
            border-radius: 50%;
            overflow: hidden;
            box-shadow:
                0 0 0 3px rgba(255, 215, 0, 0.4),
                0 0 40px rgba(255, 200, 0, 0.5),
                0 0 80px rgba(255, 150, 0, 0.25);
            position: relative;
        }
        .brand-logo img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        .brand-logo::after {
            content: '';
            position: absolute;
            inset: -8px;
            border-radius: 50%;
            border: 1px solid rgba(255, 215, 0, 0.3);
            animation: glow 2.8s ease-in-out infinite;
            pointer-events: none;
        }
        @keyframes glow {
            0%, 100% { opacity: 0.4; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.05); }
        }
        .brand h1 {
            font-size: 34px;
            font-weight: 800;
            letter-spacing: 6px;
            background: linear-gradient(90deg, #ffe566, #ffb800, #ff8c00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .brand p {
            margin-top: 6px;
            font-size: 13px;
            color: #94a3b8;
            font-weight: 500;
            letter-spacing: 1px;
        }

        .profile-card {
            background: linear-gradient(165deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 100%);
            border: 1px solid rgba(255, 200, 50, 0.15);
            border-radius: 24px;
            padding: 26px 20px 22px;
            text-align: center;
            margin-bottom: 26px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.4);
            position: relative;
            overflow: hidden;
        }
        .profile-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, #ff8c00, #ffd700, #ff8c00);
        }
        .avatar-wrap {
            position: relative;
            display: inline-block;
            margin-bottom: 12px;
        }
        .avatar {
            width: 92px;
            height: 92px;
            border-radius: 50%;
            border: 3px solid transparent;
            background: linear-gradient(#0a0a2e, #0a0a2e) padding-box,
                        linear-gradient(135deg, #ffd700, #ff8c00) border-box;
            object-fit: cover;
            display: block;
        }
        .name {
            font-size: 19px;
            font-weight: 700;
            margin-bottom: 3px;
        }
        .username {
            font-size: 13px;
            color: #94a3b8;
            margin-bottom: 12px;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: linear-gradient(90deg, #b45309, #f59e0b);
            padding: 6px 16px;
            border-radius: 50px;
            font-size: 12px;
            font-weight: 700;
            box-shadow: 0 4px 18px rgba(245, 158, 11, 0.35);
        }

        .section-title {
            font-size: 12px;
            font-weight: 600;
            color: #64748b;
            margin-bottom: 12px;
            letter-spacing: 1px;
        }

        .menu {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .menu-btn {
            background: linear-gradient(160deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.02) 100%);
            border: 1px solid rgba(255, 200, 50, 0.12);
            border-radius: 18px;
            padding: 20px 10px;
            text-align: center;
            color: #fff;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.15s, border-color 0.15s, background 0.15s;
        }
        .menu-btn:active {
            transform: scale(0.96);
            border-color: rgba(255, 200, 50, 0.35);
            background: rgba(255, 200, 50, 0.08);
        }
        .menu-btn .icon {
            font-size: 26px;
            display: block;
            margin-bottom: 8px;
        }
        .menu-btn .coming {
            display: block;
            margin-top: 5px;
            font-size: 10px;
            color: #64748b;
            font-weight: 500;
        }

        .footer {
            margin-top: 40px;
            text-align: center;
            font-size: 11px;
            color: #475569;
            letter-spacing: 2px;
        }
        .footer strong {
            color: #fbbf24;
            font-weight: 700;
        }
    </style>
</head>
<body>
    <div class="cosmos">
        <span>☀️</span>
        <span>👑</span>
        <span>⚡</span>
        <span>💎</span>
        <span>🔥</span>
        <span>✨</span>
    </div>

    <div class="container">
        <div class="brand">
            <div class="brand-logo">
                <img src="/static/nexa-logo.png" alt="NEXA Logo"
                     onerror="this.parentElement.innerHTML='☀️';">
            </div>
            <h1>NEXA</h1>
            <p>قدرت • رقابت • آینده</p>
        </div>

        <div class="profile-card">
            <div class="avatar-wrap">
                <img id="avatar" class="avatar" src="" alt="avatar">
            </div>
            <div class="name" id="name">در حال بارگذاری...</div>
            <div class="username" id="username"></div>
            <div class="badge">🌱 تازه‌وارد NEXA</div>
        </div>

        <div class="section-title">بخش‌های اصلی</div>
        <div class="menu">
            <div class="menu-btn">
                <span class="icon">⚔️</span>
                جنگ‌ها
                <span class="coming">به زودی</span>
            </div>
            <div class="menu-btn">
                <span class="icon">👥</span>
                گروه‌ها
                <span class="coming">به زودی</span>
            </div>
            <div class="menu-btn">
                <span class="icon">🏆</span>
                فصل‌ها
                <span class="coming">به زودی</span>
            </div>
            <div class="menu-btn">
                <span class="icon">💰</span>
                اقتصاد
                <span class="coming">به زودی</span>
            </div>
        </div>

        <div class="footer">
            <strong>NEXA</strong> • نسخه آزمایشی
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        try { tg.setHeaderColor('#0a0a2e'); } catch(e) {}
        try { tg.setBackgroundColor('#05051a'); } catch(e) {}

        const user = tg.initDataUnsafe?.user;

        if (user) {
            document.getElementById('name').innerText =
                (user.first_name || '') + (user.last_name ? ' ' + user.last_name : '');
            document.getElementById('username').innerText =
                user.username ? '@' + user.username : 'بدون یوزرنیم';

            if (user.photo_url) {
                document.getElementById('avatar').src = user.photo_url;
            } else {
                const letter = (user.first_name || 'N')[0];
                document.getElementById('avatar').src =
                    'https://ui-avatars.com/api/?name=' + encodeURIComponent(letter) +
                    '&background=f59e0b&color=0a0a2e&size=128&bold=true';
            }
        } else {
            document.getElementById('name').innerText = 'کاربر مهمان';
            document.getElementById('avatar').src =
                'https://ui-avatars.com/api/?name=N&background=f59e0b&color=0a0a2e&size=128&bold=true';
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)

@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
