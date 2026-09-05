import asyncio
import json
import os
import random
from datetime import datetime, date
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message, Update
from aiogram.fsm.storage.memory import MemoryStorage

# ====================== CONFIG ======================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = [123456789]  # آیدی ادمین‌ها را اینجا بگذار
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ====================== STORAGE ======================
users = {}
groups = {}

def load_storage():
    global users, groups
    try:
        if os.path.exists("nexa_users.json"):
            with open("nexa_users.json", "r", encoding="utf-8") as f:
                users = json.load(f)
        if os.path.exists("nexa_groups.json"):
            with open("nexa_groups.json", "r", encoding="utf-8") as f:
                groups = json.load(f)
    except Exception as e:
        print("Load error:", e)

def save_storage():
    try:
        with open("nexa_users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        with open("nexa_groups.json", "w", encoding="utf-8") as f:
            json.dump(groups, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Save error:", e)

def get_user(uid: int | str) -> dict:
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "coins": 300,
            "score": 0,
            "level": 1,
            "last_daily": "",
            "missions_done": 0,
            "wins": 0,
            "losses": 0,
            "badges": ["sunrise"],
            "name": "بازیکن"
        }
    return users[uid]

# ====================== CSS (WEALTH + STRONG HOVER) ======================
WEALTH_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');

:root {
    --gold: #ffd700;
    --gold-soft: rgba(255, 215, 0, 0.25);
    --bg-dark: #0a0f1c;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: 'Vazirmatn', sans-serif;
    background: linear-gradient(160deg, #0a0f1c 0%, #141e30 50%, #0c1525 100%);
    color: #fff;
    min-height: 100vh;
    overflow-x: hidden;
    direction: rtl;
}

.splash {
    position: fixed; inset: 0;
    background: url('/static/nexa-logo.jpg') center/cover no-repeat;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    z-index: 9999;
    transition: opacity 0.45s ease;
}
.splash.done { opacity: 0; pointer-events: none; }
.splash h1 {
    font-size: 3.8rem; font-weight: 800;
    text-shadow: 0 0 40px #ffd700, 0 0 80px rgba(255,215,0,0.5);
    margin-bottom: 12px;
}
.splash p {
    font-size: 1.35rem; opacity: 0.95;
    text-shadow: 0 0 20px #ffd700;
}

.container {
    max-width: 920px;
    margin: 0 auto;
    padding: 24px 16px 80px;
}

.header {
    text-align: center;
    margin-bottom: 28px;
}
.header h1 {
    font-size: 2.1rem; font-weight: 800;
    background: linear-gradient(90deg, #ffd700, #ffec8b, #ffd700);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 30px rgba(255,215,0,0.3);
}
.header .stats {
    margin-top: 12px;
    display: flex; justify-content: center; gap: 18px; flex-wrap: wrap;
    font-size: 1.05rem;
}
.header .stats span {
    background: rgba(255,215,0,0.12);
    border: 1px solid rgba(255,200,80,0.25);
    padding: 6px 14px; border-radius: 999px;
}

/* ========== WEALTH BUTTONS ========== */
.btn, .menu-btn, button.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 16px 28px;
    font-size: 1.15rem;
    font-weight: 700;
    color: #ffd700;
    text-shadow: 0 0 12px rgba(255,215,0,0.6);
    border-radius: 16px;
    border: 1.5px solid rgba(255,200,80,0.35);
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: all 0.15s ease;
    text-decoration: none;
    background-color: rgba(20, 30, 50, 0.75);
    background-image:
        radial-gradient(ellipse 130% 90% at 15% -10%, rgba(255,215,0,0.28), transparent 55%),
        radial-gradient(ellipse 80% 60% at 85% 110%, rgba(255,180,0,0.15), transparent 50%),
        repeating-linear-gradient(
            -45deg,
            rgba(255,215,0,0.07) 0px,
            transparent 8px,
            rgba(255,215,0,0.04) 16px,
            transparent 24px
        );
    box-shadow:
        0 4px 20px rgba(0,0,0,0.4),
        0 0 25px rgba(255,215,0,0.15),
        inset 0 1px 0 rgba(255,255,255,0.08);
}

@media (hover: hover) and (pointer: fine) {
    .btn:hover:not(:disabled),
    .menu-btn:hover,
    button.btn:hover:not(:disabled) {
        filter: brightness(1.32) saturate(1.18);
        transform: translateY(-4px) scale(1.03);
        box-shadow:
            0 8px 32px rgba(0,0,0,0.5),
            0 0 45px rgba(255,215,0,0.55),
            inset 0 1px 0 rgba(255,255,255,0.15);
        border-color: rgba(255,220,100,0.7);
    }
}

.btn:active { transform: scale(0.97); }

.btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
    filter: grayscale(0.4);
}

.grid-menu {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin: 28px 0;
}

.card {
    background: rgba(15, 22, 40, 0.7);
    border: 1px solid rgba(255,200,80,0.18);
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 18px;
    backdrop-filter: blur(8px);
}
.card h3 {
    color: #ffd700;
    margin-bottom: 10px;
    font-size: 1.25rem;
}
.card p { opacity: 0.9; line-height: 1.6; margin-bottom: 14px; }

.success { color: #7CFC00; }
.warning { color: #FFD700; }
.danger  { color: #FF6B6B; }

.footer {
    text-align: center;
    margin-top: 40px;
    opacity: 0.6;
    font-size: 0.9rem;
}
"""

HAPTIC_JS = """
function haptic(type='medium') {
    try {
        if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred(type);
        }
    } catch(e) {}
}
"""

def page_shell(content: str, title: str = "نِکسا") -> str:
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{title} • آکادمی خورشیدی</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>{WEALTH_CSS}</style>
</head>
<body>
    <div class="splash" id="splash">
        <h1>🌞 نِکسا</h1>
        <p>آرزوها به آسمان می‌رسند</p>
    </div>

    <div class="container">
        {content}
    </div>

    <script>
        {HAPTIC_JS}
        const tg = window.Telegram?.WebApp;
        if (tg) {{
            tg.ready();
            tg.expand();
            tg.setHeaderColor('#0a0f1c');
            tg.setBackgroundColor('#0a0f1c');
        }}

        // Splash timing
        const splash = document.getElementById('splash');
        const already = sessionStorage.getItem('nexa_splash');
        if (already) {{
            splash.classList.add('done');
            setTimeout(() => splash.remove(), 100);
        }} else {{
            setTimeout(() => {{
                splash.classList.add('done');
                sessionStorage.setItem('nexa_splash', '1');
                setTimeout(() => splash.remove(), 500);
            }}, 2200);
        }}

        // Haptic on all buttons
        document.querySelectorAll('.btn, .menu-btn').forEach(el => {{
            el.addEventListener('click', () => haptic('medium'));
        }});
    </script>
</body>
</html>"""

# ====================== FASTAPI ======================
app = FastAPI(title="NEXA Arena")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Static files (logo)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    os.makedirs("static", exist_ok=True)

# ====================== PAGES ======================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    load_storage()
    # در مینی‌اپ واقعی از initData استفاده کن. فعلاً تستی:
    uid = request.query_params.get("uid", "1001")
    user = get_user(uid)

    content = f"""
    <div class="header">
        <h1>🌞 نِکسا • آکادمی خورشیدی</h1>
        <div class="stats">
            <span>💰 {user['coins']} سکه</span>
            <span>⭐ {user['score']} امتیاز</span>
            <span>🏆 {user['wins']} برد</span>
        </div>
    </div>

    <div class="grid-menu">
        <a href="/daily?uid={uid}" class="btn menu-btn">📅 مأموریت روزانه</a>
        <a href="/war?uid={uid}" class="btn menu-btn">⚔️ جنگ آفتابی</a>
        <a href="/economy?uid={uid}" class="btn menu-btn">💎 اقتصاد</a>
        <a href="/profile?uid={uid}" class="btn menu-btn">👤 پروفایل</a>
    </div>

    <div class="card">
        <h3>🔥 وضعیت امروز</h3>
        <p>آخرین مأموریت روزانه: <b>{user['last_daily'] or 'هنوز انجام نشده'}</b></p>
        <p>تعداد مأموریت‌های انجام‌شده: <b>{user['missions_done']}</b></p>
    </div>

    <div class="footer">نِکسا • فصل اول • قدرت خورشید</div>
    """
    return HTMLResponse(page_shell(content))

@app.get("/daily", response_class=HTMLResponse)
async def daily_page(request: Request):
    load_storage()
    uid = request.query_params.get("uid", "1001")
    user = get_user(uid)
    today = str(date.today())

    can_claim = user["last_daily"] != today
    msg = ""
    if can_claim:
        msg = '<p class="success">مأموریت روزانه آماده است! دکمه زیر را بزن.</p>'
    else:
        msg = '<p class="warning">امروز مأموریتت رو انجام دادی. فردا دوباره بیا 🌞</p>'

    content = f"""
    <div class="header">
        <h1>📅 مأموریت روزانه</h1>
    </div>

    <div class="card">
        <h3>پاداش امروز</h3>
        <p>۱۲۰ سکه + ۳۵ امتیاز + ۱ امتیاز سطح</p>
        {msg}
        <br>
        <button class="btn" id="claimBtn" {"disabled" if not can_claim else ""} 
                onclick="claimDaily()">
            {"دریافت پاداش روزانه" if can_claim else "امروز انجام شده"}
        </button>
    </div>

    <a href="/?uid={uid}" class="btn" style="margin-top:20px;width:100%;">← بازگشت</a>

    <script>
        async function claimDaily() {{
            haptic('heavy');
            const res = await fetch('/api/daily/claim?uid={uid}');
            const data = await res.json();
            if (data.ok) {{
                alert('🎉 ' + data.message);
                location.reload();
            }} else {{
                alert(data.message);
            }}
        }}
    </script>
    """
    return HTMLResponse(page_shell(content, "مأموریت روزانه"))

@app.get("/war", response_class=HTMLResponse)
async def war_page(request: Request):
    load_storage()
    uid = request.query_params.get("uid", "1001")
    user = get_user(uid)

    content = f"""
    <div class="header">
        <h1>⚔️ جنگ آفتابی</h1>
        <div class="stats">
            <span>برد: {user['wins']}</span>
            <span>باخت: {user['losses']}</span>
        </div>
    </div>

    <div class="card">
        <h3>چالش امروز</h3>
        <p>با یک رقیب تصادفی از آکادمی بجنگ. قدرت تو بر اساس امتیازت محاسبه می‌شود.</p>
        <button class="btn" onclick="startWar()" style="width:100%;margin-top:12px;">
            ⚔️ شروع جنگ
        </button>
        <div id="result" style="margin-top:18px;font-size:1.15rem;"></div>
    </div>

    <a href="/?uid={uid}" class="btn" style="margin-top:20px;width:100%;">← بازگشت</a>

    <script>
        async function startWar() {{
            haptic('heavy');
            const res = await fetch('/api/war/fight?uid={uid}');
            const data = await res.json();
            const el = document.getElementById('result');
            if (data.ok) {{
                el.innerHTML = data.html;
                setTimeout(() => location.reload(), 2200);
            }} else {{
                el.innerHTML = '<span class="danger">' + data.message + '</span>';
            }}
        }}
    </script>
    """
    return HTMLResponse(page_shell(content, "جنگ"))

@app.get("/economy", response_class=HTMLResponse)
async def economy_page(request: Request):
    load_storage()
    uid = request.query_params.get("uid", "1001")
    user = get_user(uid)

    content = f"""
    <div class="header">
        <h1>💎 اقتصاد نِکسا</h1>
    </div>

    <div class="card">
        <h3>موجودی فعلی</h3>
        <p style="font-size:1.8rem;color:#ffd700;font-weight:800;">{user['coins']} سکه</p>
        <p>امتیاز: {user['score']} • سطح: {user['level']}</p>
    </div>

    <div class="card">
        <h3>منابع درآمد</h3>
        <p>• مأموریت روزانه: +۱۲۰ سکه</p>
        <p>• برد در جنگ: +۸۰ تا ۱۵۰ سکه</p>
        <p>• فصل‌ها و گروه‌ها (به زودی)</p>
    </div>

    <a href="/?uid={uid}" class="btn" style="width:100%;">← بازگشت</a>
    """
    return HTMLResponse(page_shell(content, "اقتصاد"))

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    load_storage()
    uid = request.query_params.get("uid", "1001")
    user = get_user(uid)

    content = f"""
    <div class="header">
        <h1>👤 پروفایل</h1>
    </div>

    <div class="card">
        <h3>{user.get('name', 'بازیکن')}</h3>
        <p>شناسه: {uid}</p>
        <p>سکه: <b>{user['coins']}</b></p>
        <p>امتیاز: <b>{user['score']}</b></p>
        <p>سطح: <b>{user['level']}</b></p>
        <p>برد / باخت: {user['wins']} / {user['losses']}</p>
        <p>مأموریت‌های انجام‌شده: {user['missions_done']}</p>
        <p>نشان‌ها: {', '.join(user['badges'])}</p>
    </div>

    <a href="/?uid={uid}" class="btn" style="width:100%;">← بازگشت</a>
    """
    return HTMLResponse(page_shell(content, "پروفایل"))

# ====================== API ======================
@app.get("/api/daily/claim")
async def api_daily_claim(uid: str = "1001"):
    load_storage()
    user = get_user(uid)
    today = str(date.today())

    if user["last_daily"] == today:
        return JSONResponse({"ok": False, "message": "امروز قبلاً دریافت کردی!"})

    user["coins"] += 120
    user["score"] += 35
    user["missions_done"] += 1
    user["last_daily"] = today
    user["level"] = 1 + user["score"] // 200

    save_storage()
    return JSONResponse({
        "ok": True,
        "message": f"۱۲۰ سکه و ۳۵ امتیاز دریافت شد! موجودی جدید: {user['coins']}"
    })

@app.get("/api/war/fight")
async def api_war_fight(uid: str = "1001"):
    load_storage()
    user = get_user(uid)

    # قدرت بر اساس امتیاز
    power = 40 + min(user["score"] // 10, 60) + random.randint(0, 25)
    enemy_power = random.randint(45, 95)

    won = power >= enemy_power
    if won:
        reward = random.randint(80, 150)
        user["coins"] += reward
        user["score"] += 25
        user["wins"] += 1
        html = f'<p class="success">🎉 پیروزی! قدرت تو {power} در برابر {enemy_power}<br>+{reward} سکه و +۲۵ امتیاز</p>'
    else:
        user["losses"] += 1
        user["score"] = max(0, user["score"] - 8)
        html = f'<p class="danger">💥 شکست خوردی... قدرت تو {power} در برابر {enemy_power}<br>−۸ امتیاز</p>'

    user["level"] = 1 + user["score"] // 200
    save_storage()

    return JSONResponse({"ok": True, "html": html})

# ====================== BOT ======================
bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

@dp.message()
async def start_handler(message: Message):
    if message.text and message.text.startswith("/start"):
        uid = message.from_user.id
        user = get_user(uid)
        user["name"] = message.from_user.first_name or "بازیکن"
        save_storage()

        # لینک مینی‌اپ (آدرس واقعی Railway خودت را بگذار)
        webapp_url = os.getenv("WEBAPP_URL", "https://your-railway-url.up.railway.app")
        text = (
            f"سلام <b>{message.from_user.first_name}</b> 🌞\n\n"
            f"به <b>نِکسا • آکادمی خورشیدی</b> خوش آمدی!\n"
            f"موجودی فعلی: <b>{user['coins']}</b> سکه\n\n"
            f"برای ورود به عرصه روی دکمه زیر بزن:"
        )
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 ورود به نِکسا", web_app=WebAppInfo(url=webapp_url))]
        ])
        await message.answer(text, reply_markup=kb)

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        print("Webhook error:", e)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "nexa"}

# ====================== START ======================
if __name__ == "__main__":
    load_storage()
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
