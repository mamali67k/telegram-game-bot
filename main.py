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

# پوشه static برای تصاویر (لوگوی NEXA)
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
# صفحه اصلی مینی‌اپ
# =========================================================
@app.get("/app", response_class=HTMLResponse)
async def mini_app_home():
    return HTMLResponse(content=HOME_HTML)

# =========================================================
# صفحات داخلی منو
# =========================================================
@app.get("/app/wars", response_class=HTMLResponse)
async def page_wars():
    return HTMLResponse(content=section_page(
        title="جنگ‌ها",
        icon="⚔️",
        desc="رقابت، حمله، دفاع و رتبه‌بندی جنگ‌ها",
        items=[
            ("ورود به جنگ", "پاداش ورود + امتیاز اولیه"),
            ("حمله", "امتیاز حمله و پاداش"),
            ("دفاع", "جلوگیری از سقوط رتبه"),
            ("رتبه جنگ", "گروه‌ها و حرفه‌ای‌ها"),
        ]
    ))

@app.get("/app/groups", response_class=HTMLResponse)
async def page_groups():
    return HTMLResponse(content=section_page(
        title="گروه‌ها",
        icon="👥",
        desc="ساخت گروه، دعوت، جنگ گروهی و رشد ویروسی",
        items=[
            ("ساخت / عضویت گروه", "هویت و Badge گروه"),
            ("دعوت دوستان", "صندوق دعوت و پاداش"),
            ("جنگ گروهی", "حمله و دفاع جمعی"),
            ("ارتقا گروه", "ظرفیت و پاداش بیشتر"),
        ]
    ))

@app.get("/app/seasons", response_class=HTMLResponse)
async def page_seasons():
    return HTMLResponse(content=section_page(
        title="فصل‌ها",
        icon="🏆",
        desc="فصل جاری، مأموریت‌ها، جنگ فصل و رتبه‌بندی",
        items=[
            ("فصل جاری", "تایمر و پاداش اولیه"),
            ("مأموریت فصل", "امتیاز و صندوق فصل"),
            ("جنگ فصل", "امتیاز و توکن فصل"),
            ("رتبه فصل", "پاداش رتبه‌های برتر"),
        ]
    ))

@app.get("/app/economy", response_class=HTMLResponse)
async def page_economy():
    return HTMLResponse(content=section_page(
        title="اقتصاد",
        icon="💰",
        desc="Boost، Season Pass، Mystery Box و ارتقا",
        items=[
            ("Boost", "افزایش موقت قدرت"),
            ("Season Pass", "پاداش ویژه فصل"),
            ("Mystery Box", "جعبه شانس"),
            ("ارتقا", "سطح و مزایای دائمی"),
        ]
    ))

# =========================================================
# قالب صفحات داخلی
# =========================================================
def section_page(title: str, icon: str, desc: str, items: list) -> str:
    items_html = ""
    for name, detail in items:
        items_html += f"""
        <div class="item">
            <div class="item-title">{name}</div>
            <div class="item-desc">{detail}</div>
            <div class="item-soon">به زودی فعال می‌شود</div>
        </div>
        """
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
        * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Vazirmatn',sans-serif; -webkit-tap-highlight-color:transparent; }}
        body {{
            min-height:100vh; color:#fff; background:#05051a;
            background-image:
                radial-gradient(ellipse 80% 50% at 50% -10%, rgba(255,200,50,0.15), transparent 50%),
                linear-gradient(180deg, #0a0a2e 0%, #05051a 100%);
            padding:16px; padding-bottom:40px;
        }}
        .top {{
            display:flex; align-items:center; gap:12px; margin-bottom:24px; padding-top:8px;
        }}
        .back {{
            width:42px; height:42px; border-radius:14px;
            background:rgba(255,255,255,0.08); border:1px solid rgba(255,200,50,0.2);
            display:flex; align-items:center; justify-content:center;
            font-size:20px; cursor:pointer; color:#fbbf24;
        }}
        .top h1 {{ font-size:22px; font-weight:800; }}
        .top .icon {{ font-size:28px; }}
        .desc {{
            color:#94a3b8; font-size:13px; margin-bottom:22px; line-height:1.6;
        }}
        .item {{
            background:linear-gradient(160deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02));
            border:1px solid rgba(255,200,50,0.12);
            border-radius:16px; padding:16px 18px; margin-bottom:12px;
        }}
        .item-title {{ font-weight:700; font-size:15px; margin-bottom:4px; }}
        .item-desc {{ font-size:12px; color:#94a3b8; margin-bottom:8px; }}
        .item-soon {{
            display:inline-block; font-size:11px; font-weight:600;
            background:rgba(251,191,36,0.15); color:#fbbf24;
            padding:4px 10px; border-radius:20px;
        }}
        .footer {{ text-align:center; margin-top:32px; font-size:11px; color:#475569; letter-spacing:2px; }}
        .footer strong {{ color:#fbbf24; }}
    </style>
</head>
<body>
    <div class="top">
        <div class="back" onclick="location.href='/app'">→</div>
        <span class="icon">{icon}</span>
        <h1>{title}</h1>
    </div>
    <p class="desc">{desc}</p>
    {items_html}
    <div class="footer"><strong>NEXA</strong> • نسخه آزمایشی</div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready(); tg.expand();
        try {{ tg.setHeaderColor('#0a0a2e'); }} catch(e) {{}}
        try {{ tg.setBackgroundColor('#05051a'); }} catch(e) {{}}
    </script>
</body>
</html>
"""

# =========================================================
# HTML صفحه اصلی
# =========================================================
HOME_HTML = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NEXA</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
        * { margin:0; padding:0; box-sizing:border-box; font-family:'Vazirmatn',sans-serif; -webkit-tap-highlight-color:transparent; }
        body {
            min-height:100vh; color:#fff; background:#05051a;
            background-image:
                radial-gradient(ellipse 90% 60% at 50% -10%, rgba(255,200,50,0.18), transparent 50%),
                radial-gradient(ellipse 50% 40% at 100% 30%, rgba(255,150,0,0.08), transparent),
                linear-gradient(180deg, #0a0a2e 0%, #05051a 50%, #020210 100%);
            overflow-x:hidden; padding:16px; padding-bottom:48px;
        }
        .cosmos { position:fixed; inset:0; pointer-events:none; z-index:0; overflow:hidden; }
        .cosmos span { position:absolute; opacity:0.07; font-size:28px; color:#ffd700; }
        .cosmos span:nth-child(1) { top:6%; right:8%; font-size:36px; }
        .cosmos span:nth-child(2) { top:18%; left:6%; }
        .cosmos span:nth-child(3) { top:45%; right:5%; font-size:32px; }
        .cosmos span:nth-child(4) { bottom:28%; left:8%; }
        .cosmos span:nth-child(5) { bottom:12%; right:15%; font-size:24px; }
        .container { position:relative; z-index:1; max-width:420px; margin:0 auto; }
        .brand { text-align:center; padding:24px 0 18px; }
        .brand-logo {
            width:100px; height:100px; margin:0 auto 14px; border-radius:50%; overflow:hidden;
            box-shadow: 0 0 0 3px rgba(255,215,0,0.4), 0 0 40px rgba(255,200,0,0.5), 0 0 80px rgba(255,150,0,0.25);
            position:relative;
        }
        .brand-logo img { width:100%; height:100%; object-fit:cover; display:block; }
        .brand-logo::after {
            content:''; position:absolute; inset:-8px; border-radius:50%;
            border:1px solid rgba(255,215,0,0.3); animation:glow 2.8s ease-in-out infinite; pointer-events:none;
        }
        @keyframes glow {
            0%,100% { opacity:0.4; transform:scale(1); }
            50% { opacity:1; transform:scale(1.05); }
        }
        .brand h1 {
            font-size:34px; font-weight:800; letter-spacing:6px;
            background:linear-gradient(90deg,#ffe566,#ffb800,#ff8c00);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
        }
        .brand p { margin-top:6px; font-size:13px; color:#94a3b8; letter-spacing:1px; }
        .profile-card {
            background:linear-gradient(165deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02));
            border:1px solid rgba(255,200,50,0.15); border-radius:24px;
            padding:26px 20px 22px; text-align:center; margin-bottom:26px;
            box-shadow:0 25px 50px rgba(0,0,0,0.4); position:relative; overflow:hidden;
        }
        .profile-card::before {
            content:''; position:absolute; top:0; left:0; right:0; height:3px;
            background:linear-gradient(90deg,#ff8c00,#ffd700,#ff8c00);
        }
        .avatar {
            width:92px; height:92px; border-radius:50%;
            border:3px solid transparent;
            background:linear-gradient(#0a0a2e,#0a0a2e) padding-box, linear-gradient(135deg,#ffd700,#ff8c00) border-box;
            object-fit:cover; display:block; margin:0 auto 12px;
        }
        .name { font-size:19px; font-weight:700; margin-bottom:3px; }
        .username { font-size:13px; color:#94a3b8; margin-bottom:12px; }
        .badge {
            display:inline-flex; align-items:center; gap:6px;
            background:linear-gradient(90deg,#b45309,#f59e0b);
            padding:6px 16px; border-radius:50px; font-size:12px; font-weight:700;
            box-shadow:0 4px 18px rgba(245,158,11,0.35);
        }
        .section-title { font-size:12px; font-weight:600; color:#64748b; margin-bottom:12px; letter-spacing:1px; }
        .menu { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
        .menu-btn {
            background:linear-gradient(160deg,rgba(255,255,255,0.07),rgba(255,255,255,0.02));
            border:1px solid rgba(255,200,50,0.12); border-radius:18px;
            padding:20px 10px; text-align:center; color:#fff; font-size:13px; font-weight:600;
            cursor:pointer; transition:transform 0.15s, border-color 0.15s;
            text-decoration:none; display:block;
        }
        .menu-btn:active { transform:scale(0.96); border-color:rgba(255,200,50,0.35); }
        .menu-btn .icon { font-size:26px; display:block; margin-bottom:8px; }
        .menu-btn .coming { display:block; margin-top:5px; font-size:10px; color:#64748b; }
        .footer { margin-top:40px; text-align:center; font-size:11px; color:#475569; letter-spacing:2px; }
        .footer strong { color:#fbbf24; font-weight:700; }
    </style>
</head>
<body>
    <div class="cosmos">
        <span>☀️</span><span>👑</span><span>⚡</span><span>💎</span><span>🔥</span>
    </div>
    <div class="container">
        <div class="brand">
            <div class="brand-logo">
                <img src="/static/nexa-logo.png" alt="NEXA"
                     onerror="this.parentElement.innerHTML='☀️'; this.parentElement.style.fontSize='48px'; this.parentElement.style.display='flex'; this.parentElement.style.alignItems='center'; this.parentElement.style.justifyContent='center';">
            </div>
            <h1>NEXA</h1>
            <p>قدرت • رقابت • آینده</p>
        </div>

        <div class="profile-card">
            <img id="avatar" class="avatar" src="" alt="avatar">
            <div class="name" id="name">در حال بارگذاری...</div>
            <div class="username" id="username"></div>
            <div class="badge">🌱 تازه‌وارد NEXA</div>
        </div>

        <div class="section-title">بخش‌های اصلی</div>
        <div class="menu">
            <a class="menu-btn" href="/app/wars">
                <span class="icon">⚔️</span>
                جنگ‌ها
                <span class="coming">ورود به بخش</span>
            </a>
            <a class="menu-btn" href="/app/groups">
                <span class="icon">👥</span>
                گروه‌ها
                <span class="coming">ورود به بخش</span>
            </a>
            <a class="menu-btn" href="/app/seasons">
                <span class="icon">🏆</span>
                فصل‌ها
                <span class="coming">ورود به بخش</span>
            </a>
            <a class="menu-btn" href="/app/economy">
                <span class="icon">💰</span>
                اقتصاد
                <span class="coming">ورود به بخش</span>
            </a>
        </div>

        <div class="footer"><strong>NEXA</strong> • نسخه آزمایشی</div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.ready(); tg.expand();
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

@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
