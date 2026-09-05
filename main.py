import os
import json
import random
from datetime import date
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message, Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.storage.memory import MemoryStorage

# ====================== CONFIG ======================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")  # مثال: https://nexa-xxxx.up.railway.app

# ====================== STORAGE (JSON) ======================
users = {}

def load_storage():
    global users
    try:
        if os.path.exists("nexa_users.json"):
            with open("nexa_users.json", "r", encoding="utf-8") as f:
                users = json.load(f)
    except:
        users = {}

def save_storage():
    try:
        with open("nexa_users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Save error:", e)

def get_user(uid: str) -> dict:
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
            "name": "بازیکن"
        }
    return users[uid]

# ====================== CSS ======================
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Vazirmatn',sans-serif;background:linear-gradient(160deg,#0a0f1c,#141e30);color:#fff;min-height:100vh;direction:rtl}
.container{max-width:900px;margin:0 auto;padding:20px 14px 70px}
.header{text-align:center;margin-bottom:24px}
.header h1{font-size:1.9rem;font-weight:800;background:linear-gradient(90deg,#ffd700,#ffec8b);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.stats{display:flex;justify-content:center;gap:12px;flex-wrap:wrap;margin-top:12px;font-size:1rem}
.stats span{background:rgba(255,215,0,.12);border:1px solid rgba(255,200,80,.3);padding:6px 14px;border-radius:999px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:15px 24px;font-size:1.1rem;font-weight:700;color:#ffd700;border-radius:16px;border:1.5px solid rgba(255,200,80,.4);cursor:pointer;text-decoration:none;background:rgba(20,30,50,.8);background-image:radial-gradient(ellipse 120% 80% at 20% 0%,rgba(255,215,0,.25),transparent 55%),repeating-linear-gradient(-45deg,rgba(255,215,0,.08) 0,transparent 10px);box-shadow:0 4px 18px rgba(0,0,0,.4),0 0 20px rgba(255,215,0,.15);transition:all .15s}
.btn:hover{filter:brightness(1.3) saturate(1.15);transform:translateY(-3px);box-shadow:0 8px 28px rgba(0,0,0,.5),0 0 40px rgba(255,215,0,.5)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:24px 0}
.card{background:rgba(15,22,40,.75);border:1px solid rgba(255,200,80,.2);border-radius:16px;padding:18px;margin-bottom:16px}
.card h3{color:#ffd700;margin-bottom:8px}
.success{color:#7CFC00}.warning{color:#FFD700}.danger{color:#FF6B6B}
.splash{position:fixed;inset:0;background:#0a0f1c;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:9999;transition:opacity .4s}
.splash.done{opacity:0;pointer-events:none}
.splash h1{font-size:3.2rem;text-shadow:0 0 30px #ffd700}
"""

def page(content: str, title: str = "نِکسا") -> str:
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>{title}</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>{CSS}</style>
</head>
<body>
<div class="splash" id="splash"><h1>🌞 نِکسا</h1><p>آرزوها به آسمان می‌رسند</p></div>
<div class="container">{content}</div>
<script>
const tg=window.Telegram?.WebApp;
if(tg){{tg.ready();tg.expand();tg.setHeaderColor('#0a0f1c');tg.setBackgroundColor('#0a0f1c');}}
const s=document.getElementById('splash');
if(sessionStorage.getItem('nexa_s')){{s.classList.add('done');setTimeout(()=>s.remove(),50);}}
else{{setTimeout(()=>{{s.classList.add('done');sessionStorage.setItem('nexa_s','1');setTimeout(()=>s.remove(),400);}},1800);}}
document.querySelectorAll('.btn').forEach(b=>b.onclick=()=>{{try{{tg?.HapticFeedback?.impactOccurred('medium')}}catch(e){{}}}});
</script>
</body></html>"""

# ====================== APP ======================
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/health")
async def health():
    return {"ok": True, "service": "nexa"}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    load_storage()
    uid = request.query_params.get("uid") or "1001"
    u = get_user(uid)
    content = f"""
    <div class="header">
        <h1>🌞 نِکسا • آکادمی خورشیدی</h1>
        <div class="stats">
            <span>💰 {u['coins']}</span>
            <span>⭐ {u['score']}</span>
            <span>🏆 {u['wins']}</span>
        </div>
    </div>
    <div class="grid">
        <a class="btn" href="/daily?uid={uid}">📅 مأموریت روزانه</a>
        <a class="btn" href="/war?uid={uid}">⚔️ جنگ آفتابی</a>
        <a class="btn" href="/economy?uid={uid}">💎 اقتصاد</a>
        <a class="btn" href="/profile?uid={uid}">👤 پروفایل</a>
    </div>
    <div class="card">
        <h3>وضعیت امروز</h3>
        <p>آخرین مأموریت: <b>{u['last_daily'] or 'هنوز انجام نشده'}</b></p>
        <p>مأموریت‌های انجام‌شده: {u['missions_done']}</p>
    </div>
    """
    return HTMLResponse(page(content))

@app.get("/daily", response_class=HTMLResponse)
async def daily(request: Request):
    load_storage()
    uid = request.query_params.get("uid") or "1001"
    u = get_user(uid)
    today = str(date.today())
    can = u["last_daily"] != today
    msg = '<p class="success">مأموریت آماده است!</p>' if can else '<p class="warning">امروز انجام دادی. فردا بیا 🌞</p>'
    content = f"""
    <div class="header"><h1>📅 مأموریت روزانه</h1></div>
    <div class="card">
        <h3>پاداش: ۱۲۰ سکه + ۳۵ امتیاز</h3>
        {msg}
        <br>
        <button class="btn" id="btn" {'disabled' if not can else ''} onclick="claim()">
            {'دریافت پاداش' if can else 'انجام شده'}
        </button>
    </div>
    <a class="btn" href="/?uid={uid}" style="width:100%;margin-top:16px">← بازگشت</a>
    <script>
    async function claim(){{
        const r=await fetch('/api/daily?uid={uid}');
        const d=await r.json();
        alert(d.message);
        location.reload();
    }}
    </script>
    """
    return HTMLResponse(page(content, "مأموریت"))

@app.get("/war", response_class=HTMLResponse)
async def war(request: Request):
    load_storage()
    uid = request.query_params.get("uid") or "1001"
    u = get_user(uid)
    content = f"""
    <div class="header">
        <h1>⚔️ جنگ آفتابی</h1>
        <div class="stats"><span>برد: {u['wins']}</span><span>باخت: {u['losses']}</span></div>
    </div>
    <div class="card">
        <p>با رقیب تصادفی بجنگ. قدرت بر اساس امتیازت محاسبه می‌شه.</p>
        <button class="btn" style="width:100%;margin-top:12px" onclick="fight()">⚔️ شروع جنگ</button>
        <div id="res" style="margin-top:16px;font-size:1.1rem"></div>
    </div>
    <a class="btn" href="/?uid={uid}" style="width:100%;margin-top:16px">← بازگشت</a>
    <script>
    async function fight(){{
        const r=await fetch('/api/war?uid={uid}');
        const d=await r.json();
        document.getElementById('res').innerHTML=d.html;
        setTimeout(()=>location.reload(),2000);
    }}
    </script>
    """
    return HTMLResponse(page(content, "جنگ"))

@app.get("/economy", response_class=HTMLResponse)
async def economy(request: Request):
    load_storage()
    uid = request.query_params.get("uid") or "1001"
    u = get_user(uid)
    content = f"""
    <div class="header"><h1>💎 اقتصاد</h1></div>
    <div class="card">
        <h3>موجودی</h3>
        <p style="font-size:1.7rem;color:#ffd700;font-weight:800">{u['coins']} سکه</p>
        <p>امتیاز: {u['score']} • سطح: {u['level']}</p>
    </div>
    <div class="card">
        <h3>منابع درآمد</h3>
        <p>• مأموریت روزانه: +۱۲۰ سکه</p>
        <p>• برد جنگ: +۸۰ تا ۱۵۰ سکه</p>
    </div>
    <a class="btn" href="/?uid={uid}" style="width:100%">← بازگشت</a>
    """
    return HTMLResponse(page(content, "اقتصاد"))

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    load_storage()
    uid = request.query_params.get("uid") or "1001"
    u = get_user(uid)
    content = f"""
    <div class="header"><h1>👤 پروفایل</h1></div>
    <div class="card">
        <h3>{u.get('name','بازیکن')}</h3>
        <p>شناسه: {uid}</p>
        <p>سکه: <b>{u['coins']}</b></p>
        <p>امتیاز: <b>{u['score']}</b> • سطح: <b>{u['level']}</b></p>
        <p>برد/باخت: {u['wins']}/{u['losses']}</p>
        <p>مأموریت‌ها: {u['missions_done']}</p>
    </div>
    <a class="btn" href="/?uid={uid}" style="width:100%">← بازگشت</a>
    """
    return HTMLResponse(page(content, "پروفایل"))

# ========== API ==========
@app.get("/api/daily")
async def api_daily(uid: str = "1001"):
    load_storage()
    u = get_user(uid)
    today = str(date.today())
    if u["last_daily"] == today:
        return JSONResponse({"ok": False, "message": "امروز قبلاً گرفتی!"})
    u["coins"] += 120
    u["score"] += 35
    u["missions_done"] += 1
    u["last_daily"] = today
    u["level"] = 1 + u["score"] // 200
    save_storage()
    return JSONResponse({"ok": True, "message": f"۱۲۰ سکه و ۳۵ امتیاز گرفتی! موجودی: {u['coins']}"})

@app.get("/api/war")
async def api_war(uid: str = "1001"):
    load_storage()
    u = get_user(uid)
    power = 40 + min(u["score"] // 10, 55) + random.randint(0, 20)
    enemy = random.randint(48, 92)
    if power >= enemy:
        reward = random.randint(80, 150)
        u["coins"] += reward
        u["score"] += 25
        u["wins"] += 1
        html = f'<p class="success">🎉 پیروزی! قدرت {power} vs {enemy}<br>+{reward} سکه و +۲۵ امتیاز</p>'
    else:
        u["losses"] += 1
        u["score"] = max(0, u["score"] - 8)
        html = f'<p class="danger">💥 شکست... قدرت {power} vs {enemy}<br>−۸ امتیاز</p>'
    u["level"] = 1 + u["score"] // 200
    save_storage()
    return JSONResponse({"ok": True, "html": html})

# ========== BOT ==========
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

@dp.message()
async def on_start(message: Message):
    if not message.text or not message.text.startswith("/start"):
        return
    uid = str(message.from_user.id)
    u = get_user(uid)
    u["name"] = message.from_user.first_name or "بازیکن"
    save_storage()

    if not WEBAPP_URL:
        await message.answer("⚠️ WEBAPP_URL تنظیم نشده. به ادمین بگو.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 ورود به نِکسا", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    await message.answer(
        f"سلام <b>{message.from_user.first_name}</b> 🌞\n\n"
        f"به <b>نِکسا</b> خوش اومدی!\n"
        f"موجودی: <b>{u['coins']}</b> سکه\n\n"
        f"برای ورود روی دکمه زیر بزن:",
        reply_markup=kb
    )

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        print("Webhook error:", e)
        return JSONResponse({"ok": False}, status_code=200)

# ========== RUN ==========
if __name__ == "__main__":
    load_storage()
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
