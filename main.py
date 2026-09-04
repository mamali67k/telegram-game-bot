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
            "attacks": 0,
            "defenses": 0,
            "groups": [],
            "season_points": 0,
            "in_war": False,
        }
        save_users(users)
    else:
        users[uid]["last_seen"] = datetime.now().isoformat()
        if first_name:
            users[uid]["first_name"] = first_name
        if username is not None:
            users[uid]["username"] = username
        for k, v in [("attacks", 0), ("defenses", 0), ("in_war", False)]:
            if k not in users[uid]:
                users[uid][k] = v
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

def recalc_level(score: int) -> int:
    return max(1, score // 100 + 1)

def apply_score(uid: str, delta: int, users: dict) -> dict:
    u = users[uid]
    u["score"] = max(0, u.get("score", 0) + delta)
    u["level"] = recalc_level(u["score"])
    u["badge"] = badge_for_level(u["level"])
    return u

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☀️ ورود به NEXA", web_app=WebAppInfo(url=MINIAPP_URL))]
    ])
    await message.answer(
        "به NEXA خوش آمدید ☀️\n\nقدرتت را بیدار کن.\nآینده از آنِ توست.",
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

@app.post("/api/user/sync")
async def api_user_sync(request: Request):
    try:
        body = await request.json()
        user_id = body.get("id")
        if not user_id:
            return JSONResponse({"ok": False}, status_code=400)
        pro = get_or_create_pro(int(user_id), body.get("first_name") or "", body.get("username"))
        return {
            "ok": True,
            "level": pro["level"],
            "score": pro["score"],
            "badge": pro.get("badge") or badge_for_level(pro["level"]),
            "wars_joined": pro.get("wars_joined", 0),
            "attacks": pro.get("attacks", 0),
            "in_war": pro.get("in_war", False),
        }
    except Exception as e:
        logger.exception("sync")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/api/war/join")
async def api_war_join(request: Request):
    try:
        body = await request.json()
        user_id = body.get("id")
        if not user_id:
            return JSONResponse({"ok": False, "msg": "no user"}, status_code=400)
        users = load_users()
        uid = str(user_id)
        if uid not in users:
            get_or_create_pro(int(user_id))
            users = load_users()
        u = users[uid]
        if u.get("in_war"):
            return {"ok": True, "msg": "قبلاً در جنگ هستی", "score": u["score"], "level": u["level"], "badge": u["badge"], "in_war": True}
        u["in_war"] = True
        u["wars_joined"] = u.get("wars_joined", 0) + 1
        apply_score(uid, 10, users)
        save_users(users)
        u = users[uid]
        return {"ok": True, "msg": "وارد جنگ شدی! +۱۰ امتیاز", "score": u["score"], "level": u["level"], "badge": u["badge"], "in_war": True, "wars_joined": u["wars_joined"]}
    except Exception as e:
        logger.exception("war join")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/war/attack")
async def api_war_attack(request: Request):
    try:
        body = await request.json()
        user_id = body.get("id")
        if not user_id:
            return JSONResponse({"ok": False, "msg": "no user"}, status_code=400)
        users = load_users()
        uid = str(user_id)
        if uid not in users:
            return JSONResponse({"ok": False, "msg": "اول وارد شو"}, status_code=400)
        u = users[uid]
        if not u.get("in_war"):
            return {"ok": False, "msg": "اول باید وارد جنگ شوی"}
        u["attacks"] = u.get("attacks", 0) + 1
        apply_score(uid, 20, users)
        save_users(users)
        u = users[uid]
        return {"ok": True, "msg": "حمله موفق! +۲۰ امتیاز", "score": u["score"], "level": u["level"], "badge": u["badge"], "attacks": u["attacks"]}
    except Exception as e:
        logger.exception("attack")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

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

/* واترمارک نیمه‌محو در کل اپ */
.nexa-wm{position:fixed;inset:0;pointer-events:none;z-index:0;
background:url('/static/nexa-logo.jpg') center 38%/min(72vw,300px) no-repeat;opacity:.08}
.nexa-wm::after{content:'NEXA';position:absolute;bottom:10%;left:0;right:0;text-align:center;
font-size:42px;font-weight:800;letter-spacing:14px;color:#ffd700;opacity:.07}

#splash{position:fixed;inset:0;z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:center;
background:#05051a url('/static/nexa-logo.jpg') center/cover no-repeat;transition:opacity .55s,visibility .55s}
#splash::before{content:'';position:absolute;inset:0;background:rgba(5,5,26,.75);z-index:0}
#splash > *{position:relative;z-index:1}
#splash.hide{opacity:0;visibility:hidden;pointer-events:none}
.splash-logo{width:120px;height:120px;border-radius:50%;overflow:hidden;margin-bottom:20px;
box-shadow:0 0 0 4px rgba(255,215,0,.4),0 0 50px rgba(255,200,0,.5);animation:pulse 2s ease-in-out infinite}
.splash-logo img{width:100%;height:100%;object-fit:cover}
.splash-logo.fb{display:flex;align-items:center;justify-content:center;font-size:56px;background:radial-gradient(circle at 30% 30%,#ffe566,#f5a623 70%)}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.04)}}
.splash-title{font-size:42px;font-weight:800;letter-spacing:10px;
background:linear-gradient(90deg,#ffe566,#ffb800,#ff8c00);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.splash-slogan{margin-top:14px;font-size:15px;color:#fbbf24;font-weight:600;opacity:0;animation:up .7s ease .3s forwards;text-align:center;padding:0 20px}
@keyframes up{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.loader{margin-top:32px;width:56px;height:4px;background:rgba(255,255,255,.15);border-radius:4px;overflow:hidden}
.loader-bar{height:100%;width:0;background:linear-gradient(90deg,#ff8c00,#ffd700);animation:load 1.9s ease forwards}
@keyframes load{to{width:100%}}

#main{display:none;position:relative;z-index:1;padding:14px 14px 36px;
background-image:radial-gradient(ellipse 90% 45% at 50% -8%,rgba(255,200,50,.1),transparent 50%),linear-gradient(180deg,#0a0a2e 0%,#05051a 55%,#020210 100%)}
#main.show{display:block}
.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.brand{display:flex;align-items:center;gap:10px}
.brand-logo{width:38px;height:38px;border-radius:50%;overflow:hidden;box-shadow:0 0 0 2px rgba(255,215,0,.4)}
.brand-logo img{width:100%;height:100%;object-fit:cover}
.brand-logo.fb{display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#ffd700,#ff8c00);font-size:18px}
.brand-name{font-size:18px;font-weight:800;letter-spacing:3px;background:linear-gradient(90deg,#ffe566,#ffb800);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.chip{font-size:11px;background:rgba(251,191,36,.15);color:#fbbf24;padding:5px 11px;border-radius:20px;font-weight:600}
.profile{background:linear-gradient(165deg,rgba(255,255,255,.09),rgba(255,255,255,.03));border:1px solid rgba(255,200,50,.16);border-radius:18px;padding:14px 16px;display:flex;align-items:center;gap:12px;margin-bottom:18px}
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
.menu a{text-decoration:none;color:#fff;background:linear-gradient(160deg,rgba(255,255,255,.08),rgba(255,255,255,.02));border:1px solid rgba(255,200,50,.14);border-radius:16px;padding:18px 10px;text-align:center;font-size:13px;font-weight:700}
.menu a:active{transform:scale(.97);border-color:rgba(255,200,50,.4)}
.menu a .ic{display:block;font-size:26px;margin-bottom:8px}
.menu a .sub{display:block;margin-top:5px;font-size:10px;font-weight:500;color:#94a3b8}
.footer{text-align:center;margin-top:26px;font-size:11px;color:#475569;letter-spacing:2px}
.footer strong{color:#fbbf24}
</style>
</head>
<body>
<div class="nexa-wm"></div>

<div id="splash">
  <div class="splash-logo" id="sLogo">
    <img src="/static/nexa-logo.jpg" alt="NEXA" onerror="fbSplash()">
  </div>
  <div class="splash-title">NEXA</div>
  <div class="splash-slogan">قدرتت را بیدار کن • آینده از آنِ توست</div>
  <div class="loader"><div class="loader-bar"></div></div>
</div>

<div id="main">
  <div class="top">
    <div class="brand">
      <div class="brand-logo" id="hLogo">
        <img src="/static/nexa-logo.jpg" alt="" onerror="fbHeader()">
      </div>
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
    <a href="/app/wars"><span class="ic">⚔️</span>جنگ‌ها<span class="sub">حمله فعال شد</span></a>
    <a href="/app/groups"><span class="ic">👥</span>گروه‌ها<span class="sub">دعوت • جنگ گروهی</span></a>
    <a href="/app/seasons"><span class="ic">🏆</span>فصل‌ها<span class="sub">مأموریت • پاداش</span></a>
    <a href="/app/economy"><span class="ic">💰</span>اقتصاد<span class="sub">Boost • صندوق</span></a>
  </div>
  <div class="footer"><strong>NEXA</strong> • Pro Arena</div>
</div>

<script>
const tg=window.Telegram.WebApp;tg.ready();tg.expand();
try{tg.setHeaderColor('#05051a')}catch(e){}
try{tg.setBackgroundColor('#05051a')}catch(e){}
function fbSplash(){const e=document.getElementById('sLogo');e.classList.add('fb');e.innerHTML='☀️'}
function fbHeader(){const e=document.getElementById('hLogo');e.classList.add('fb');e.innerHTML='☀️'}
setTimeout(()=>{document.getElementById('splash').classList.add('hide');document.getElementById('main').classList.add('show')},2200);
const user=tg.initDataUnsafe?.user;
if(user){
  document.getElementById('name').innerText=(user.first_name||'')+(user.last_name?(' '+user.last_name):'');
  document.getElementById('username').innerText=user.username?'@'+user.username:'';
  document.getElementById('avatar').src=user.photo_url||('https://ui-avatars.com/api/?name='+encodeURIComponent((user.first_name||'N')[0])+'&background=f59e0b&color=0a0a2e&size=128&bold=true');
  fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:user.id,first_name:user.first_name,username:user.username})})
  .then(r=>r.json()).then(d=>{if(d&&d.ok){document.getElementById('level').innerText=d.level;document.getElementById('score').innerText=d.score;document.getElementById('badge').innerText=d.badge||'تازه‌وارد'}}).catch(()=>{});
}else{
  document.getElementById('name').innerText='کاربر مهمان';
  document.getElementById('avatar').src='https://ui-avatars.com/api/?name=N&background=f59e0b&color=0a0a2e&size=128&bold=true';
}
</script>
</body>
</html>
"""
    return HTMLResponse(html)

@app.get("/app/wars", response_class=HTMLResponse)
async def page_wars():
    html = r"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>NEXA - جنگ‌ها</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box;font-family:'Vazirmatn',sans-serif}
body{min-height:100vh;color:#fff;background:#05051a;position:relative}
.nexa-wm{position:fixed;inset:0;pointer-events:none;z-index:0;background:url('/static/nexa-logo.jpg') center 40%/min(70vw,280px) no-repeat;opacity:.07}
.nexa-wm::after{content:'NEXA';position:absolute;bottom:12%;left:0;right:0;text-align:center;font-size:40px;font-weight:800;letter-spacing:12px;color:#ffd700;opacity:.06}
.wrap{position:relative;z-index:1;padding:14px 14px 40px;background-image:radial-gradient(ellipse 80% 45% at 50% -8%,rgba(255,200,50,.1),transparent 50%),linear-gradient(180deg,#0a0a2e,#05051a)}
.top{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.back{width:42px;height:42px;border-radius:14px;background:rgba(255,255,255,.08);border:1px solid rgba(255,200,50,.25);display:flex;align-items:center;justify-content:center;color:#fbbf24;text-decoration:none;font-size:18px}
h1{font-size:21px;font-weight:800}
.panel{background:linear-gradient(165deg,rgba(255,255,255,.08),rgba(255,255,255,.02));border:1px solid rgba(255,200,50,.15);border-radius:18px;padding:16px;margin-bottom:14px}
.panel .row{display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px}
.panel .row b{color:#fbbf24}
.desc{color:#94a3b8;font-size:13px;line-height:1.6;margin-bottom:16px}
.btn{display:block;width:100%;border:none;border-radius:14px;padding:14px;font-size:15px;font-weight:700;margin-bottom:10px;cursor:pointer;font-family:inherit}
.btn-join{background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e}
.btn-attack{background:linear-gradient(90deg,#dc2626,#f97316);color:#fff}
.btn:disabled{opacity:.45;cursor:not-allowed}
.toast{position:fixed;bottom:24px;left:16px;right:16px;background:rgba(15,15,40,.95);border:1px solid rgba(251,191,36,.4);border-radius:14px;padding:12px 16px;text-align:center;font-size:13px;font-weight:600;color:#fbbf24;display:none;z-index:50}
.toast.show{display:block}
.footer{text-align:center;margin-top:20px;font-size:11px;color:#475569;letter-spacing:2px}
.footer strong{color:#fbbf24}
</style>
</head>
<body>
<div class="nexa-wm"></div>
<div class="wrap">
<div class="top"><a class="back" href="/app">→</a><span style="font-size:24px">⚔️</span><h1>جنگ‌ها</h1></div>
<p class="desc">موتور جنگ فعال است. وارد شو، حمله کن و امتیاز بگیر.</p>
<div class="panel">
  <div class="row"><span>وضعیت جنگ</span><b id="warStatus">خارج از جنگ</b></div>
  <div class="row"><span>امتیاز تو</span><b id="score">—</b></div>
  <div class="row"><span>سطح</span><b id="level">—</b></div>
  <div class="row"><span>تعداد حمله</span><b id="attacks">0</b></div>
</div>
<button class="btn btn-join" id="btnJoin" onclick="doJoin()">ورود به جنگ (+۱۰)</button>
<button class="btn btn-attack" id="btnAttack" onclick="doAttack()" disabled>حمله (+۲۰)</button>
<div class="toast" id="toast"></div>
<div class="footer"><strong>NEXA</strong> • War Engine</div>
</div>
<script>
const tg=window.Telegram.WebApp;tg.ready();tg.expand();
try{tg.setHeaderColor('#05051a')}catch(e){}
const user=tg.initDataUnsafe?.user;let uid=user?user.id:null;
function toast(msg){const t=document.getElementById('toast');t.innerText=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2200)}
function apply(d){if(!d)return;if(d.score!=null)document.getElementById('score').innerText=d.score;if(d.level!=null)document.getElementById('level').innerText=d.level;if(d.attacks!=null)document.getElementById('attacks').innerText=d.attacks;if(d.in_war){document.getElementById('warStatus').innerText='در میدان جنگ';document.getElementById('btnAttack').disabled=false;document.getElementById('btnJoin').disabled=true}}
async function sync(){if(!uid)return;const r=await fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})});const d=await r.json();if(d.ok)apply(d)}
async function doJoin(){if(!uid){toast('ابتدا از تلگرام وارد شو');return}const r=await fetch('/api/war/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})});const d=await r.json();toast(d.msg||'انجام شد');if(d.ok)apply(d)}
async function doAttack(){if(!uid){toast('ابتدا از تلگرام وارد شو');return}const r=await fetch('/api/war/attack',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})});const d=await r.json();toast(d.msg||'انجام شد');if(d.ok)apply(d);else if(d.msg)toast(d.msg)}
sync();
</script>
</body>
</html>
"""
    return HTMLResponse(html)

def section_html(title, icon, desc, blocks):
    cards = "".join([
        f"""<div style="background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border:1px solid rgba(255,200,50,.12);border-radius:16px;padding:16px;margin-bottom:12px">
        <div style="font-weight:700;font-size:15px;margin-bottom:4px">{b[0]}</div>
        <div style="font-size:12px;color:#94a3b8;margin-bottom:8px">{b[1]}</div>
        <span style="font-size:11px;font-weight:600;background:rgba(251,191,36,.15);color:#fbbf24;padding:4px 10px;border-radius:20px">{b[2]}</span></div>"""
        for b in blocks
    ])
    return f"""<!DOCTYPE html><html lang="fa" dir="rtl"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>NEXA - {title}</title><script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Vazirmatn',sans-serif}}
body{{min-height:100vh;color:#fff;background:#05051a;position:relative}}
.nexa-wm{{position:fixed;inset:0;pointer-events:none;z-index:0;background:url('/static/nexa-logo.jpg') center 40%/min(70vw,280px) no-repeat;opacity:.07}}
.nexa-wm::after{{content:'NEXA';position:absolute;bottom:12%;left:0;right:0;text-align:center;font-size:40px;font-weight:800;letter-spacing:12px;color:#ffd700;opacity:.06}}
.wrap{{position:relative;z-index:1;padding:14px;background-image:radial-gradient(ellipse 80% 45% at 50% -8%,rgba(255,200,50,.1),transparent 50%),linear-gradient(180deg,#0a0a2e,#05051a)}}
.top{{display:flex;align-items:center;gap:12px;margin-bottom:18px}}
.back{{width:42px;height:42px;border-radius:14px;background:rgba(255,255,255,.08);border:1px solid rgba(255,200,50,.25);display:flex;align-items:center;justify-content:center;color:#fbbf24;text-decoration:none;font-size:18px}}
h1{{font-size:21px;font-weight:800}}.desc{{color:#94a3b8;font-size:13px;line-height:1.7;margin-bottom:18px}}
.footer{{text-align:center;margin-top:24px;font-size:11px;color:#475569;letter-spacing:2px}}.footer strong{{color:#fbbf24}}
</style></head><body>
<div class="nexa-wm"></div>
<div class="wrap">
<div class="top"><a class="back" href="/app">→</a><span style="font-size:24px">{icon}</span><h1>{title}</h1></div>
<p class="desc">{desc}</p>{cards}
<div class="footer"><strong>NEXA</strong></div>
</div>
<script>const tg=window.Telegram.WebApp;tg.ready();tg.expand();try{{tg.setHeaderColor('#05051a')}}catch(e){{}}</script>
</body></html>"""

@app.get("/app/groups", response_class=HTMLResponse)
async def page_groups():
    return HTMLResponse(section_html("گروه‌ها", "👥", "موتور گروه + رشد ویروسی.", [
        ("ساخت / عضویت", "Badge و پروفایل گروه", "مرحله بعد"),
        ("دعوت", "صندوق و پاداش دعوت", "مرحله بعد"),
        ("جنگ گروهی", "حمله و دفاع جمعی", "مرحله بعد"),
        ("ارتقا گروه", "ظرفیت و پاداش", "مرحله بعد"),
    ]))

@app.get("/app/seasons", response_class=HTMLResponse)
async def page_seasons():
    return HTMLResponse(section_html("فصل‌ها", "🏆", "موتور فصل.", [
        ("فصل جاری", "تایمر و پاداش شروع", "مرحله بعد"),
        ("مأموریت فصل", "امتیاز و صندوق", "مرحله بعد"),
        ("جنگ فصل", "توکن فصل", "مرحله بعد"),
        ("رتبه فصل", "پاداش برترین‌ها", "مرحله بعد"),
    ]))

@app.get("/app/economy", response_class=HTMLResponse)
async def page_economy():
    return HTMLResponse(section_html("اقتصاد", "💰", "موتور اقتصاد حرفه‌ای.", [
        ("Boost", "+قدرت موقت", "مرحله بعد"),
        ("Season Pass", "پاداش ویژه فصل", "مرحله بعد"),
        ("Mystery Box", "جعبه شانس", "مرحله بعد"),
        ("ارتقا", "مزایای دائمی", "مرحله بعد"),
    ]))

@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"NEXA webhook → {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
