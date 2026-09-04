import os
import json
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
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
USERS_FILE = "nexa_users.json"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =========================================================
# USER STORAGE (پایه هویت حرفه‌ای)
# =========================================================
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_or_create_pro(user_id: int, first_name: str = "", username: str = None):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "user_id": user_id,
            "first_name": first_name,
            "username": username,
            "level": 1,
            "score": 10,
            "badge": "تازه‌وارد",
            "title": "Novice",
            "joined_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "wars_joined": 0,
            "groups": [],
            "season_points": 0,
        }
        save_users(users)
        logger.info(f"New NEXA pro: {user_id}")
    else:
        users[uid]["last_seen"] = datetime.now().isoformat()
        if first_name:
            users[uid]["first_name"] = first_name
        if username is not None:
            users[uid]["username"] = username
        save_users(users)
    return users[uid]

def badge_for_level(level: int) -> str:
    if level >= 10:
        return "افسانه‌ای"
    if level >= 5:
        return "حرفه‌ای"
    if level >= 3:
        return "مبارز"
    return "تازه‌وارد"

# =========================================================
# BOT
# =========================================================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☀️ ورود به NEXA", web_app=WebAppInfo(url=MINIAPP_URL))]
    ])
    await message.answer(
        "به NEXA خوش آمدید ☀️\n\nقدرتت را بیدار کن.\nآینده از آنِ توست.",
        reply_markup=keyboard
    )

# =========================================================
# FASTAPI
# =========================================================
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

# ثبت / به‌روزرسانی کاربر از داخل مینی‌اپ
@app.post("/api/user/sync")
async def api_user_sync(request: Request):
    try:
        body = await request.json()
        user_id = body.get("id")
        if not user_id:
            return JSONResponse({"ok": False}, status_code=400)
        pro = get_or_create_pro(
            user_id=int(user_id),
            first_name=body.get("first_name") or "",
            username=body.get("username")
        )
        pro["badge"] = badge_for_level(pro.get("level", 1))
        return {
            "ok": True,
            "level": pro["level"],
            "score": pro["score"],
            "badge": pro["badge"],
            "title": pro.get("title", "Novice"),
        }
    except Exception as e:
        logger.exception("sync error")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

# =========================================================
# صفحه اصلی (اسپلش + داشبورد)
# =========================================================
@app.get("/app", response_class=HTMLResponse)
async def mini_app():
    html = r"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>NEXA</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box;font-family:'Vazirmatn',sans-serif;-webkit-tap-highlight-color:transparent}
body{min-height:100vh;background:#05051a;color:#fff;overflow-x:hidden}

#splash{position:fixed;inset:0;z-index:9999;background:#05051a;
background-image:radial-gradient(ellipse 80% 50% at 50% 20%,rgba(255,200,50,.2),transparent 55%);
display:flex;flex-direction:column;align-items:center;justify-content:center;
transition:opacity .55s ease,visibility .55s ease}
#splash.hide{opacity:0;visibility:hidden;pointer-events:none}
.splash-logo{width:130px;height:130px;border-radius:50%;overflow:hidden;margin-bottom:24px;
box-shadow:0 0 0 4px rgba(255,215,0,.35),0 0 50px rgba(255,200,0,.45);animation:pulse 2s ease-in-out infinite}
.splash-logo img{width:100%;height:100%;object-fit:cover}
.splash-logo.fb{display:flex;align-items:center;justify-content:center;font-size:60px;
background:radial-gradient(circle at 30% 30%,#ffe566,#f5a623 70%)}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.04)}}
.splash-title{font-size:40px;font-weight:800;letter-spacing:8px;
background:linear-gradient(90deg,#ffe566,#ffb800,#ff8c00);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.splash-slogan{margin-top:12px;font-size:14px;color:#fbbf24;font-weight:600;opacity:0;animation:up .7s ease .25s forwards}
@keyframes up{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.loader{margin-top:28px;width:52px;height:4px;background:rgba(255,255,255,.1);border-radius:4px;overflow:hidden}
.loader-bar{height:100%;width:0;background:linear-gradient(90deg,#ff8c00,#ffd700);animation:load 1.9s ease forwards}
@keyframes load{to{width:100%}}

#main{display:none;padding:14px 14px 36px;
background-image:radial-gradient(ellipse 90% 45% at 50% -8%,rgba(255,200,50,.12),transparent 50%),
linear-gradient(180deg,#0a0a2e 0%,#05051a 55%,#020210 100%)}
#main.show{display:block}

.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.brand{display:flex;align-items:center;gap:10px}
.brand-logo{width:38px;height:38px;border-radius:50%;overflow:hidden;box-shadow:0 0 0 2px rgba(255,215,0,.4)}
.brand-logo img{width:100%;height:100%;object-fit:cover}
.brand-logo.fb{display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#ffd700,#ff8c00);font-size:18px}
.brand-name{font-size:18px;font-weight:800;letter-spacing:3px;
background:linear-gradient(90deg,#ffe566,#ffb800);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.chip{font-size:11px;background:rgba(251,191,36,.15);color:#fbbf24;padding:5px 11px;border-radius:20px;font-weight:600}

.profile{background:linear-gradient(165deg,rgba(255,255,255,.09),rgba(255,255,255,.03));
border:1px solid rgba(255,200,50,.16);border-radius:18px;padding:14px 16px;display:flex;align-items:center;gap:12px;margin-bottom:18px}
.profile img{width:52px;height:52px;border-radius:50%;border:2px solid #fbbf24;object-fit:cover}
.profile .meta{flex:1}
.profile .name{font-weight:700;font-size:15px}
.profile .user{font-size:12px;color:#94a3b8;margin-top:2px}
.stats{display:flex;gap:10px;margin-top:8px}
.stat{flex:1;text-align:center;background:rgba(0,0,0,.25);border-radius:12px;padding:8px 4px}
.stat b{display:block;font-size:15px;color:#fbbf24}
.stat span{font-size:10px;color:#94a3b8}

.label{font-size:11px;color:#64748b;font-weight:600;margin-bottom:10px;letter-spacing:1px}
.menu{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.menu a{text-decoration:none;color:#fff;background:linear-gradient(160deg,rgba(255,255,255,.08),rgba(255,255,255,.02));
border:1px solid rgba(255,200,50,.14);border-radius:16px;padding:18px 10px;text-align:center;font-size:13px;font-weight:700}
.menu a:active{transform:scale(.97);border-color:rgba(255,200,50,.4)}
.menu a .ic{display:block;font-size:26px;margin-bottom:8px}
.menu a .sub{display:block;margin-top:5px;font-size:10px;font-weight:500;color:#94a3b8}

.footer{text-align:center;margin-top:26px;font-size:11px;color:#475569;letter-spacing:2px}
.footer strong{color:#fbbf24}
</style>
</head>
<body>
<div id="splash">
  <div class="splash-logo" id="sLogo"><img src="/static/nexa-logo.png" alt="NEXA" onerror="fbSplash()"></div>
  <div class="splash-title">NEXA</div>
  <div class="splash-slogan">قدرتت را بیدار کن • آینده از آنِ توست</div>
  <div class="loader"><div class="loader-bar"></div></div>
</div>

<div id="main">
  <div class="top">
    <div class="brand">
      <div class="brand-logo" id="hLogo"><img src="/static/nexa-logo.png" alt="" onerror="fbHeader()"></div>
      <div class="brand-name">NEXA</div>
    </div>
    <div class="chip" id="badge">تازه‌وارد</div>
  </div>

  <div class="profile">
    <img id="avatar" src="" alt="">
    <div class="meta">
      <div class="name" id="name">...</div>
      <div class="user" id="username"></div>
      <div class="stats">
        <div class="stat"><b id="level">1</b><span>سطح</span></div>
        <div class="stat"><b id="score">10</b><span>امتیاز</span></div>
      </div>
    </div>
  </div>

  <div class="label">موتورهای NEXA</div>
  <div class="menu">
    <a href="/app/wars"><span class="ic">⚔️</span>جنگ‌ها<span class="sub">حمله • دفاع • رتبه</span></a>
    <a href="/app/groups"><span class="ic">👥</span>گروه‌ها<span class="sub">دعوت • جنگ گروهی</span></a>
    <a href="/app/seasons"><span class="ic">🏆</span>فصل‌ها<span class="sub">مأموریت • پاداش</span></a>
    <a href="/app/economy"><span class="ic">💰</span>اقتصاد<span class="sub">Boost • صندوق</span></a>
  </div>
  <div class="footer"><strong>NEXA</strong> • Pro Arena</div>
</div>

<script>
const tg = window.Telegram.WebApp;
tg.ready(); tg.expand();
try{tg.setHeaderColor('#05051a')}catch(e){}
try{tg.setBackgroundColor('#05051a')}catch(e){}

function fbSplash(){const e=document.getElementById('sLogo');e.classList.add('fb');e.innerHTML='☀️'}
function fbHeader(){const e=document.getElementById('hLogo');e.classList.add('fb');e.innerHTML='☀️'}

setTimeout(()=>{
  document.getElementById('splash').classList.add('hide');
  document.getElementById('main').classList.add('show');
}, 2100);

const user = tg.initDataUnsafe?.user;
if(user){
  document.getElementById('name').innerText = (user.first_name||'') + (user.last_name?(' '+user.last_name):'');
  document.getElementById('username').innerText = user.username ? '@'+user.username : '';
  document.getElementById('avatar').src = user.photo_url ||
    ('https://ui-avatars.com/api/?name='+encodeURIComponent((user.first_name||'N')[0])+'&background=f59e0b&color=0a0a2e&size=128&bold=true');

  // همگام‌سازی با سرور (هویت حرفه‌ای)
  fetch('/api/user/sync', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      id: user.id,
      first_name: user.first_name,
      last_name: user.last_name,
      username: user.username
    })
  }).then(r=>r.json()).then(d=>{
    if(d && d.ok){
      document.getElementById('level').innerText = d.level;
      document.getElementById('score').innerText = d.score;
      document.getElementById('badge').innerText = d.badge || 'تازه‌وارد';
    }
  }).catch(()=>{});
}else{
  document.getElementById('name').innerText = 'کاربر مهمان';
  document.getElementById('avatar').src = 'https://ui-avatars.com/api/?name=N&background=f59e0b&color=0a0a2e&size=128&bold=true';
}
</script>
</body>
</html>
"""
    return HTMLResponse(html)

# =========================================================
# صفحات موتورها (طبق پلن)
# =========================================================
def section_html(title, icon, desc, blocks):
    cards = ""
    for b in blocks:
        cards += f"""
        <div style="background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));
        border:1px solid rgba(255,200,50,.12);border-radius:16px;padding:16px;margin-bottom:12px">
          <div style="font-weight:700;font-size:15px;margin-bottom:4px">{b[0]}</div>
          <div style="font-size:12px;color:#94a3b8;margin-bottom:8px;line-height:1.5">{b[1]}</div>
          <span style="font-size:11px;font-weight:600;background:rgba(251,191,36,.15);color:#fbbf24;
          padding:4px 10px;border-radius:20px">{b[2]}</span>
        </div>"""
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>NEXA - {title}</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Vazirmatn',sans-serif}}
body{{min-height:100vh;color:#fff;background:#05051a;
background-image:radial-gradient(ellipse 80% 45% at 50% -8%,rgba(255,200,50,.12),transparent 50%),
linear-gradient(180deg,#0a0a2e,#05051a);padding:14px 14px 36px}}
.top{{display:flex;align-items:center;gap:12px;margin-bottom:18px}}
.back{{width:42px;height:42px;border-radius:14px;background:rgba(255,255,255,.08);
border:1px solid rgba(255,200,50,.25);display:flex;align-items:center;justify-content:center;
color:#fbbf24;text-decoration:none;font-size:18px}}
h1{{font-size:21px;font-weight:800}}
.desc{{color:#94a3b8;font-size:13px;line-height:1.7;margin-bottom:18px}}
.footer{{text-align:center;margin-top:24px;font-size:11px;color:#475569;letter-spacing:2px}}
.footer strong{{color:#fbbf24}}
</style></head><body>
<div class="top"><a class="back" href="/app">→</a><span style="font-size:24px">{icon}</span><h1>{title}</h1></div>
<p class="desc">{desc}</p>
{cards}
<div class="footer"><strong>NEXA</strong> • {title}</div>
<script>const tg=window.Telegram.WebApp;tg.ready();tg.expand();try{{tg.setHeaderColor('#05051a')}}catch(e){{}}</script>
</body></html>"""

@app.get("/app/wars", response_class=HTMLResponse)
async def page_wars():
    return HTMLResponse(section_html(
        "جنگ‌ها", "⚔️",
        "موتور جنگ (War Engine): ورود، حمله، دفاع و رتبه‌بندی.",
        [
            ("ورود به جنگ", "پاداش ورود + امتیاز اولیه برای شروع رقابت", "به زودی"),
            ("حمله", "امتیاز حمله، پاداش ضربه و تأثیر روی رتبه", "به زودی"),
            ("دفاع", "جلوگیری از سقوط رتبه و پاداش دفاع موفق", "به زودی"),
            ("رتبه جنگ", "جدول گروه‌ها و حرفه‌ای‌ها در جنگ جاری", "به زودی"),
        ]
    ))

@app.get("/app/groups", response_class=HTMLResponse)
async def page_groups():
    return HTMLResponse(section_html(
        "گروه‌ها", "👥",
        "موتور گروه + رشد ویروسی: هویت، دعوت، جنگ گروهی، ارتقا.",
        [
            ("ساخت / عضویت گروه", "Badge گروه، عنوان و پروفایل گروهی", "به زودی"),
            ("دعوت و صندوق دعوت", "پاداش دعوت، رتبه دعوت، رشد ویروسی", "به زودی"),
            ("جنگ گروهی", "حمله و دفاع جمعی + امتیاز جنگ گروه", "به زودی"),
            ("ارتقا گروه", "افزایش ظرفیت، پاداش و قدرت گروه", "به زودی"),
        ]
    ))

@app.get("/app/seasons", response_class=HTMLResponse)
async def page_seasons():
    return HTMLResponse(section_html(
        "فصل‌ها", "🏆",
        "موتور فصل: تایمر، مأموریت، جنگ فصل، رتبه و پاداش فصل.",
        [
            ("فصل جاری", "تایمر فصل و پاداش شروع برای همه", "به زودی"),
            ("مأموریت فصل", "امتیاز فصل و دسترسی به صندوق فصل", "به زودی"),
            ("جنگ فصل", "امتیاز جنگ فصل + توکن فصل", "به زودی"),
            ("رتبه فصل", "پاداش رتبه‌های برتر گروه‌ها و حرفه‌ای‌ها", "به زودی"),
        ]
    ))

@app.get("/app/economy", response_class=HTMLResponse)
async def page_economy():
    return HTMLResponse(section_html(
        "اقتصاد", "💰",
        "موتور اقتصاد حرفه‌ای: Boost، Season Pass، Mystery Box، ارتقا و فشار اقتصادی.",
        [
            ("Boost", "افزایش موقت قدرت و امتیاز رقابت", "به زودی"),
            ("Season Pass", "پاداش ویژه و مسیر پیشرفت فصل", "به زودی"),
            ("Mystery Box", "جعبه شانس با پاداش تصادفی", "به زودی"),
            ("ارتقا و صندوق‌ها", "مزایای دائمی + صندوق خرید و ارتقا", "به زودی"),
        ]
    ))

@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"NEXA webhook → {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
