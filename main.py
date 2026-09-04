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
        "به NEXA خوش آمدید ☀️\n\nقدرتت را بیدار کن.\nبرای ورود روی دکمه زیر بزن:",
        reply_markup=keyboard
    )

app = FastAPI()
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

# =========================================================
# صفحه اصلی مینی‌اپ (لودینگ + منو)
# =========================================================
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
            background: #05051a;
            color: #fff;
            overflow-x: hidden;
        }

        /* ========== SPLASH / LOADING ========== */
        #splash {
            position: fixed;
            inset: 0;
            z-index: 9999;
            background: #05051a;
            background-image:
                radial-gradient(ellipse 80% 50% at 50% 20%, rgba(255, 200, 50, 0.2), transparent 55%),
                radial-gradient(ellipse 60% 40% at 50% 80%, rgba(255, 140, 0, 0.1), transparent);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transition: opacity 0.6s ease, visibility 0.6s ease;
        }
        #splash.hide {
            opacity: 0;
            visibility: hidden;
            pointer-events: none;
        }
        .splash-logo {
            width: 140px;
            height: 140px;
            border-radius: 50%;
            overflow: hidden;
            box-shadow:
                0 0 0 4px rgba(255, 215, 0, 0.35),
                0 0 60px rgba(255, 200, 0, 0.5),
                0 0 120px rgba(255, 150, 0, 0.25);
            margin-bottom: 28px;
            animation: logoPulse 2s ease-in-out infinite;
        }
        .splash-logo img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .splash-logo.fallback {
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 64px;
            background: radial-gradient(circle at 30% 30%, #ffe566, #f5a623 70%);
        }
        @keyframes logoPulse {
            0%, 100% { transform: scale(1); box-shadow: 0 0 0 4px rgba(255,215,0,0.35), 0 0 60px rgba(255,200,0,0.5); }
            50% { transform: scale(1.04); box-shadow: 0 0 0 6px rgba(255,215,0,0.5), 0 0 80px rgba(255,200,0,0.65); }
        }
        .splash-title {
            font-size: 42px;
            font-weight: 800;
            letter-spacing: 8px;
            background: linear-gradient(90deg, #ffe566, #ffb800, #ff8c00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 12px;
        }
        .splash-slogan {
            font-size: 15px;
            color: #fbbf24;
            font-weight: 600;
            margin-bottom: 36px;
            opacity: 0;
            animation: fadeUp 0.8s ease 0.3s forwards;
        }
        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .loader {
            width: 48px;
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
        }
        .loader-bar {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #ff8c00, #ffd700);
            border-radius: 4px;
            animation: load 1.8s ease-in-out forwards;
        }
        @keyframes load {
            0% { width: 0%; }
            100% { width: 100%; }
        }

        /* ========== MAIN APP ========== */
        #main {
            display: none;
            min-height: 100vh;
            padding: 16px 16px 40px;
            background-image:
                radial-gradient(ellipse 90% 50% at 50% -10%, rgba(255,200,50,0.14), transparent 50%),
                linear-gradient(180deg, #0a0a2e 0%, #05051a 60%, #020210 100%);
        }
        #main.show { display: block; }

        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 0 20px;
        }
        .header-brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .header-logo {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            overflow: hidden;
            box-shadow: 0 0 0 2px rgba(255,215,0,0.4);
        }
        .header-logo img { width:100%; height:100%; object-fit:cover; }
        .header-logo.fallback {
            display:flex; align-items:center; justify-content:center;
            background: linear-gradient(135deg,#ffd700,#ff8c00); font-size:20px;
        }
        .header-name {
            font-size: 20px;
            font-weight: 800;
            letter-spacing: 3px;
            background: linear-gradient(90deg,#ffe566,#ffb800);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header-badge {
            font-size: 11px;
            background: rgba(251,191,36,0.15);
            color: #fbbf24;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: 600;
        }

        .profile {
            background: linear-gradient(165deg, rgba(255,255,255,0.09), rgba(255,255,255,0.03));
            border: 1px solid rgba(255,200,50,0.18);
            border-radius: 20px;
            padding: 18px;
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 24px;
        }
        .profile img {
            width: 56px;
            height: 56px;
            border-radius: 50%;
            border: 2px solid #fbbf24;
            object-fit: cover;
        }
        .profile-info { flex: 1; }
        .profile-name { font-weight: 700; font-size: 16px; }
        .profile-user { font-size: 12px; color: #94a3b8; margin-top: 2px; }

        .section-label {
            font-size: 12px;
            color: #64748b;
            font-weight: 600;
            margin-bottom: 12px;
            letter-spacing: 1px;
        }

        .menu {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 20px;
        }
        .menu a {
            text-decoration: none;
            color: #fff;
            background: linear-gradient(160deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
            border: 1px solid rgba(255,200,50,0.14);
            border-radius: 18px;
            padding: 22px 12px;
            text-align: center;
            font-size: 14px;
            font-weight: 700;
            transition: transform 0.15s, border-color 0.15s;
        }
        .menu a:active {
            transform: scale(0.96);
            border-color: rgba(255,200,50,0.4);
        }
        .menu a .icon {
            display: block;
            font-size: 28px;
            margin-bottom: 10px;
        }
        .menu a .sub {
            display: block;
            margin-top: 6px;
            font-size: 11px;
            font-weight: 500;
            color: #94a3b8;
        }

        .footer {
            text-align: center;
            margin-top: 28px;
            font-size: 11px;
            color: #475569;
            letter-spacing: 2px;
        }
        .footer strong { color: #fbbf24; }
    </style>
</head>
<body>
    <!-- SPLASH -->
    <div id="splash">
        <div class="splash-logo" id="splashLogo">
            <img src="/static/nexa-logo.png" alt="NEXA"
                 onerror="showFallbackLogo()">
        </div>
        <div class="splash-title">NEXA</div>
        <div class="splash-slogan">قدرتت را بیدار کن • آینده از آنِ توست</div>
        <div class="loader"><div class="loader-bar"></div></div>
    </div>

    <!-- MAIN -->
    <div id="main">
        <div class="header">
            <div class="header-brand">
                <div class="header-logo" id="headerLogo">
                    <img src="/static/nexa-logo.png" alt="NEXA"
                         onerror="this.parentElement.classList.add('fallback'); this.parentElement.innerHTML='☀️';">
                </div>
                <div class="header-name">NEXA</div>
            </div>
            <div class="header-badge" id="userBadge">تازه‌وارد</div>
        </div>

        <div class="profile">
            <img id="avatar" src="" alt="avatar">
            <div class="profile-info">
                <div class="profile-name" id="name">...</div>
                <div class="profile-user" id="username"></div>
            </div>
        </div>

        <div class="section-label">ورود به بخش‌ها</div>
        <div class="menu">
            <a href="/app/wars">
                <span class="icon">⚔️</span>
                جنگ‌ها
                <span class="sub">حمله • دفاع • رتبه</span>
            </a>
            <a href="/app/groups">
                <span class="icon">👥</span>
                گروه‌ها
                <span class="sub">دعوت • جنگ گروهی</span>
            </a>
            <a href="/app/seasons">
                <span class="icon">🏆</span>
                فصل‌ها
                <span class="sub">مأموریت • پاداش</span>
            </a>
            <a href="/app/economy">
                <span class="icon">💰</span>
                اقتصاد
                <span class="sub">Boost • صندوق</span>
            </a>
        </div>

        <div class="footer"><strong>NEXA</strong> • نسخه آزمایشی</div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        try { tg.setHeaderColor('#05051a'); } catch(e) {}
        try { tg.setBackgroundColor('#05051a'); } catch(e) {}

        function showFallbackLogo() {
            const el = document.getElementById('splashLogo');
            el.classList.add('fallback');
            el.innerHTML = '☀️';
        }

        // لودینگ ۲ ثانیه سپس ورود به اپ
        setTimeout(() => {
            document.getElementById('splash').classList.add('hide');
            document.getElementById('main').classList.add('show');
        }, 2200);

        const user = tg.initDataUnsafe?.user;
        if (user) {
            document.getElementById('name').innerText =
                (user.first_name || '') + (user.last_name ? ' ' + user.last_name : '');
            document.getElementById('username').innerText =
                user.username ? '@' + user.username : '';
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

# =========================================================
# صفحات داخلی منو
# =========================================================
def section_page(title: str, icon: str, desc: str, items: list) -> str:
    items_html = "".join([
        f"""
        <div style="background:linear-gradient(160deg,rgba(255,255,255,0.07),rgba(255,255,255,0.02));
                    border:1px solid rgba(255,200,50,0.12);border-radius:16px;padding:16px 18px;margin-bottom:12px;">
            <div style="font-weight:700;font-size:15px;margin-bottom:4px;">{name}</div>
            <div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">{detail}</div>
            <div style="display:inline-block;font-size:11px;font-weight:600;background:rgba(251,191,36,0.15);
                        color:#fbbf24;padding:4px 10px;border-radius:20px;">به زودی</div>
        </div>
        """ for name, detail in items
    ])
    return f"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NEXA - {title}</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
        * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Vazirmatn',sans-serif; }}
        body {{
            min-height:100vh; color:#fff; background:#05051a;
            background-image: radial-gradient(ellipse 80% 50% at 50% -10%, rgba(255,200,50,0.12), transparent 50%),
                              linear-gradient(180deg,#0a0a2e,#05051a);
            padding:16px 16px 40px;
        }}
        .top {{ display:flex; align-items:center; gap:12px; margin-bottom:20px; padding-top:6px; }}
        .back {{
            width:42px; height:42px; border-radius:14px; background:rgba(255,255,255,0.08);
            border:1px solid rgba(255,200,50,0.25); display:flex; align-items:center; justify-content:center;
            font-size:18px; color:#fbbf24; cursor:pointer; text-decoration:none;
        }}
        h1 {{ font-size:22px; font-weight:800; }}
        .desc {{ color:#94a3b8; font-size:13px; margin-bottom:20px; line-height:1.7; }}
        .footer {{ text-align:center; margin-top:28px; font-size:11px; color:#475569; letter-spacing:2px; }}
        .footer strong {{ color:#fbbf24; }}
    </style>
</head>
<body>
    <div class="top">
        <a class="back" href="/app">→</a>
        <span style="font-size:26px;">{icon}</span>
        <h1>{title}</h1>
    </div>
    <p class="desc">{desc}</p>
    {items_html}
    <div class="footer"><strong>NEXA</strong></div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready(); tg.expand();
        try {{ tg.setHeaderColor('#05051a'); }} catch(e) {{}}
    </script>
</body>
</html>
"""

@app.get("/app/wars", response_class=HTMLResponse)
async def page_wars():
    return HTMLResponse(section_page(
        "جنگ‌ها", "⚔️",
        "رقابت مستقیم، حمله، دفاع و فتح رتبه در میدان جنگ.",
        [("ورود به جنگ", "پاداش ورود و امتیاز اولیه"),
         ("حمله", "امتیاز حمله + پاداش"),
         ("دفاع", "محافظت از رتبه"),
         ("رتبه‌بندی جنگ", "گروه‌ها و حرفه‌ای‌ها")]
    ))

@app.get("/app/groups", response_class=HTMLResponse)
async def page_groups():
    return HTMLResponse(section_page(
        "گروه‌ها", "👥",
        "بساز، دعوت کن، با هم بجنگ و رشد ویروسی داشته باش.",
        [("ساخت / عضویت", "Badge و هویت گروه"),
         ("دعوت دوستان", "صندوق و پاداش دعوت"),
         ("جنگ گروهی", "حمله و دفاع جمعی"),
         ("ارتقا گروه", "ظرفیت و پاداش بیشتر")]
    ))

@app.get("/app/seasons", response_class=HTMLResponse)
async def page_seasons():
    return HTMLResponse(section_page(
        "فصل‌ها", "🏆",
        "هر فصل یک میدان تازه برای رقابت و پاداش‌های بزرگ.",
        [("فصل جاری", "تایمر و پاداش شروع"),
         ("مأموریت فصل", "امتیاز و صندوق"),
         ("جنگ فصل", "توکن و پاداش ویژه"),
         ("رتبه فصل", "پاداش برترین‌ها")]
    ))

@app.get("/app/economy", response_class=HTMLResponse)
async def page_economy():
    return HTMLResponse(section_page(
        "اقتصاد", "💰",
        "Boost، Season Pass، جعبه‌های شانس و ارتقاهای دائمی.",
        [("Boost", "قدرت موقت بیشتر"),
         ("Season Pass", "پاداش ویژه فصل"),
         ("Mystery Box", "جعبه شانس"),
         ("ارتقا", "مزایای دائمی")]
    ))

@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set → {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
