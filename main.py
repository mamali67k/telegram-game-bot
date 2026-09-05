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
GROUPS_FILE = "nexa_groups.json"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def load_json(path, default=None):
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default if not isinstance(default, list) else []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if not isinstance(default, list) else []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users():
    return load_json(USERS_FILE, {})

def save_users(data):
    save_json(USERS_FILE, data)

def load_groups():
    return load_json(GROUPS_FILE, {})

def save_groups(data):
    save_json(GROUPS_FILE, data)

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
        for k, v in [("attacks", 0), ("defenses", 0), ("in_war", False), ("groups", [])]:
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

def apply_score(uid: str, delta: int, users: dict):
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
            "defenses": pro.get("defenses", 0),
            "in_war": pro.get("in_war", False),
            "groups": pro.get("groups", []),
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
            return {"ok": True, "msg": "قبلاً در جنگ هستی", "score": u["score"], "level": u["level"], "badge": u["badge"], "in_war": True, "attacks": u.get("attacks", 0), "defenses": u.get("defenses", 0)}
        u["in_war"] = True
        u["wars_joined"] = u.get("wars_joined", 0) + 1
        apply_score(uid, 10, users)
        save_users(users)
        u = users[uid]
        return {"ok": True, "msg": "وارد جنگ شدی! +۱۰ امتیاز", "score": u["score"], "level": u["level"], "badge": u["badge"], "in_war": True, "attacks": u.get("attacks", 0), "defenses": u.get("defenses", 0)}
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
        return {"ok": True, "msg": "حمله موفق! +۲۰ امتیاز", "score": u["score"], "level": u["level"], "badge": u["badge"], "attacks": u["attacks"], "defenses": u.get("defenses", 0), "in_war": True}
    except Exception as e:
        logger.exception("attack")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/war/defend")
async def api_war_defend(request: Request):
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
        u["defenses"] = u.get("defenses", 0) + 1
        apply_score(uid, 15, users)
        save_users(users)
        u = users[uid]
        return {"ok": True, "msg": "دفاع موفق! +۱۵ امتیاز", "score": u["score"], "level": u["level"], "badge": u["badge"], "attacks": u.get("attacks", 0), "defenses": u["defenses"], "in_war": True}
    except Exception as e:
        logger.exception("defend")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/group/create")
async def api_group_create(request: Request):
    try:
        body = await request.json()
        user_id = body.get("id")
        name = (body.get("name") or "").strip()
        if not user_id:
            return JSONResponse({"ok": False, "msg": "no user"}, status_code=400)
        if not name or len(name) < 2:
            return {"ok": False, "msg": "نام گروه حداقل ۲ حرف باشد"}
        if len(name) > 24:
            return {"ok": False, "msg": "نام گروه حداکثر ۲۴ حرف"}
        users = load_users()
        uid = str(user_id)
        if uid not in users:
            get_or_create_pro(int(user_id))
            users = load_users()
        groups = load_groups()
        for g in groups.values():
            if g.get("name", "").lower() == name.lower():
                return {"ok": False, "msg": "این نام گروه قبلاً گرفته شده"}
        gid = f"g{int(datetime.now().timestamp())}"
        groups[gid] = {
            "id": gid,
            "name": name,
            "owner": int(user_id),
            "members": [int(user_id)],
            "created_at": datetime.now().isoformat(),
            "score": 0,
        }
        save_groups(groups)
        if gid not in users[uid].get("groups", []):
            users[uid].setdefault("groups", []).append(gid)
        apply_score(uid, 25, users)
        save_users(users)
        u = users[uid]
        return {
            "ok": True,
            "msg": f"گروه «{name}» ساخته شد! +۲۵ امتیاز",
            "group_id": gid,
            "group_name": name,
            "score": u["score"],
            "level": u["level"],
            "badge": u["badge"],
            "groups": u.get("groups", []),
        }
    except Exception as e:
        logger.exception("group create")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.get("/api/group/list")
async def api_group_list():
    groups = load_groups()
    items = [{"id": g["id"], "name": g["name"], "members": len(g.get("members", [])), "score": g.get("score", 0)} for g in groups.values()]
    items.sort(key=lambda x: x["score"], reverse=True)
    return {"ok": True, "groups": items[:30]}

# استایل مشترک هدر برند (لوگو + نام) — در همه صفحات غیر از اسپلش
BRAND_HEADER_CSS = """
.brand-bar{display:flex;align-items:center;gap:10px}
.brand-logo{width:36px;height:36px;border-radius:50%;overflow:hidden;flex-shrink:0;
box-shadow:0 0 0 2px rgba(255,215,0,.45),0 0 16px rgba(255,200,0,.25)}
.brand-logo img{width:100%;height:100%;object-fit:cover;display:block}
.brand-logo.fb{display:flex;align-items:center;justify-content:center;
background:linear-gradient(135deg,#ffd700,#ff8c00);font-size:18px}
.brand-name{font-size:18px;font-weight:800;letter-spacing:3px;
background:linear-gradient(90deg,#ffe566,#ffb800);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
"""

BRAND_HEADER_HTML = """
<div class="brand-bar">
  <div class="brand-logo" id="brandLogo">
    <img src="/static/nexa-logo.jpg" alt="NEXA" onerror="this.parentElement.classList.add('fb');this.parentElement.innerHTML='☀️';">
  </div>
  <div class="brand-name">NEXA</div>
</div>
"""

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
.nexa-wm{position:fixed;inset:0;pointer-events:none;z-index:0;background:url('/static/nexa-logo.jpg') center 38%/min(72vw,300px) no-repeat;opacity:.08}
.nexa-wm::after{content:'NEXA';position:absolute;bottom:10%;left:0;right:0;text-align:center;font-size:42px;font-weight:800;letter-spacing:14px;color:#ffd700;opacity:.07}

/* اسپلش: بدون لوگوی تصویری — فقط نام + شعار + لودینگ */
#splash{position:fixed;inset:0;z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:center;
background:#05051a url('/static/nexa-logo.jpg') center center / cover no-repeat;transition:opacity .55s,visibility .55s}
#splash::before{content:'';position:absolute;inset:0;z-index:0;background:linear-gradient(180deg,rgba(5,5,26,.35),rgba(5,5,26,.55))}
#splash>*{position:relative;z-index:1}
#splash.hide{opacity:0;visibility:hidden;pointer-events:none}
.splash-title{font-size:48px;font-weight:800;letter-spacing:12px;background:linear-gradient(90deg,#ffe566,#ffb800,#ff8c00);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-shadow:0 4px 30px rgba(0,0,0,.45)}
.splash-slogan{margin-top:16px;font-size:15px;color:#fff;font-weight:600;opacity:0;animation:up .7s ease .25s forwards;text-align:center;padding:0 24px;text-shadow:0 2px 12px rgba(0,0,0,.8)}
@keyframes up{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.loader{margin-top:36px;width:56px;height:4px;background:rgba(255,255,255,.25);border-radius:4px;overflow:hidden}
.loader-bar{height:100%;width:0;background:linear-gradient(90deg,#ff8c00,#ffd700);animation:load 1.9s ease forwards}
@keyframes load{to{width:100%}}

#main{display:none;position:relative;z-index:1;padding:14px 14px 36px;background-image:radial-gradient(ellipse 90% 45% at 50% -8%,rgba(255,200,50,.1),transparent 50%),linear-gradient(180deg,#0a0a2e 0%,#05051a 55%,#020210 100%)}
#main.show{display:block}
.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
""" + BRAND_HEADER_CSS + r"""
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
  <div class="splash-title">NEXA</div>
  <div class="splash-slogan">قدرتت را بیدار کن • آینده از آنِ توست</div>
  <div class="loader"><div class="loader-bar"></div></div>
</div>

<div id="main">
  <div class="top">
""" + BRAND_HEADER_HTML + r"""
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
    <a href="/app/wars"><span class="ic">⚔️</span>جنگ‌ها<span class="sub">حمله • دفاع</span></a>
    <a href="/app/groups"><span class="ic">👥</span>گروه‌ها<span class="sub">ساخت فعال شد</span></a>
    <a href="/app/seasons"><span class="ic">🏆</span>فصل‌ها<span class="sub">مأموریت • پاداش</span></a>
    <a href="/app/economy"><span class="ic">💰</span>اقتصاد<span class="sub">Boost • صندوق</span></a>
  </div>
  <div class="footer"><strong>NEXA</strong> • Pro Arena</div>
</div>

<script>
const tg=window.Telegram.WebApp;tg.ready();tg.expand();
try{tg.setHeaderColor('#05051a')}catch(e){}
try{tg.setBackgroundColor('#05051a')}catch(e){}
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

def page_shell(title_icon: str, title: str, body_html: str, extra_css: str = "", extra_js: str = "") -> str:
    """قالب مشترک صفحات داخلی با هدر برند استاندارد"""
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>NEXA - {title}</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Vazirmatn',sans-serif}}
body{{min-height:100vh;color:#fff;background:#05051a;position:relative}}
.nexa-wm{{position:fixed;inset:0;pointer-events:none;z-index:0;background:url('/static/nexa-logo.jpg') center 40%/min(70vw,280px) no-repeat;opacity:.07}}
.nexa-wm::after{{content:'NEXA';position:absolute;bottom:12%;left:0;right:0;text-align:center;font-size:40px;font-weight:800;letter-spacing:12px;color:#ffd700;opacity:.06}}
.wrap{{position:relative;z-index:1;padding:14px 14px 40px;background-image:radial-gradient(ellipse 80% 45% at 50% -8%,rgba(255,200,50,.1),transparent 50%),linear-gradient(180deg,#0a0a2e,#05051a)}}
.top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;gap:10px}}
.top-right{{display:flex;align-items:center;gap:10px}}
.back{{width:40px;height:40px;border-radius:12px;background:rgba(255,255,255,.08);border:1px solid rgba(255,200,50,.25);display:flex;align-items:center;justify-content:center;color:#fbbf24;text-decoration:none;font-size:17px;flex-shrink:0}}
.page-title{{font-size:16px;font-weight:700;color:#e2e8f0}}
{BRAND_HEADER_CSS}
.footer{{text-align:center;margin-top:22px;font-size:11px;color:#475569;letter-spacing:2px}}
.footer strong{{color:#fbbf24}}
{extra_css}
</style>
</head>
<body>
<div class="nexa-wm"></div>
<div class="wrap">
  <div class="top">
    <div class="top-right">
      <a class="back" href="/app">→</a>
      {BRAND_HEADER_HTML}
    </div>
    <div class="page-title">{title_icon} {title}</div>
  </div>
  {body_html}
  <div class="footer"><strong>NEXA</strong></div>
</div>
<script>
const tg=window.Telegram.WebApp;tg.ready();tg.expand();
try{{tg.setHeaderColor('#05051a')}}catch(e){{}}
{extra_js}
</script>
</body>
</html>"""

@app.get("/app/wars", response_class=HTMLResponse)
async def page_wars():
    body = """
<p style="color:#94a3b8;font-size:13px;line-height:1.6;margin-bottom:14px">ورود، حمله و دفاع فعال است.</p>
<div style="background:linear-gradient(165deg,rgba(255,255,255,.08),rgba(255,255,255,.02));border:1px solid rgba(255,200,50,.15);border-radius:18px;padding:16px;margin-bottom:14px">
  <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px"><span>وضعیت</span><b id="warStatus" style="color:#fbbf24">خارج از جنگ</b></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px"><span>امتیاز</span><b id="score" style="color:#fbbf24">—</b></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px"><span>سطح</span><b id="level" style="color:#fbbf24">—</b></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px"><span>حمله</span><b id="attacks" style="color:#fbbf24">0</b></div>
  <div style="display:flex;justify-content:space-between;font-size:13px"><span>دفاع</span><b id="defenses" style="color:#fbbf24">0</b></div>
</div>
<button id="btnJoin" onclick="doJoin()" style="display:block;width:100%;border:none;border-radius:14px;padding:14px;font-size:15px;font-weight:700;margin-bottom:10px;cursor:pointer;font-family:inherit;background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">ورود به جنگ (+۱۰)</button>
<button id="btnAttack" onclick="doAttack()" disabled style="display:block;width:100%;border:none;border-radius:14px;padding:14px;font-size:15px;font-weight:700;margin-bottom:10px;cursor:pointer;font-family:inherit;background:linear-gradient(90deg,#dc2626,#f97316);color:#fff;opacity:.45">حمله (+۲۰)</button>
<button id="btnDefend" onclick="doDefend()" disabled style="display:block;width:100%;border:none;border-radius:14px;padding:14px;font-size:15px;font-weight:700;margin-bottom:10px;cursor:pointer;font-family:inherit;background:linear-gradient(90deg,#1d4ed8,#3b82f6);color:#fff;opacity:.45">دفاع (+۱۵)</button>
<div id="toast" style="position:fixed;bottom:24px;left:16px;right:16px;background:rgba(15,15,40,.95);border:1px solid rgba(251,191,36,.4);border-radius:14px;padding:12px 16px;text-align:center;font-size:13px;font-weight:600;color:#fbbf24;display:none;z-index:50"></div>
"""
    js = """
const user=tg.initDataUnsafe?.user;let uid=user?user.id:null;
function toast(msg){const t=document.getElementById('toast');t.innerText=msg;t.style.display='block';setTimeout(()=>t.style.display='none',2200)}
function apply(d){if(!d)return;if(d.score!=null)document.getElementById('score').innerText=d.score;if(d.level!=null)document.getElementById('level').innerText=d.level;if(d.attacks!=null)document.getElementById('attacks').innerText=d.attacks;if(d.defenses!=null)document.getElementById('defenses').innerText=d.defenses;if(d.in_war){document.getElementById('warStatus').innerText='در میدان جنگ';document.getElementById('btnAttack').disabled=false;document.getElementById('btnAttack').style.opacity='1';document.getElementById('btnDefend').disabled=false;document.getElementById('btnDefend').style.opacity='1';document.getElementById('btnJoin').disabled=true;document.getElementById('btnJoin').style.opacity='.45'}}
async function sync(){if(!uid)return;const r=await fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})});const d=await r.json();if(d.ok)apply(d)}
async function doJoin(){if(!uid){toast('از تلگرام وارد شو');return}const r=await fetch('/api/war/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})});const d=await r.json();toast(d.msg||'');if(d.ok)apply(d)}
async function doAttack(){if(!uid)return;const r=await fetch('/api/war/attack',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})});const d=await r.json();toast(d.msg||'');if(d.ok)apply(d)}
async function doDefend(){if(!uid)return;const r=await fetch('/api/war/defend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})});const d=await r.json();toast(d.msg||'');if(d.ok)apply(d)}
sync();
"""
    return HTMLResponse(page_shell("⚔️", "جنگ‌ها", body, "", js))

@app.get("/app/groups", response_class=HTMLResponse)
async def page_groups():
    body = """
<p style="color:#94a3b8;font-size:13px;line-height:1.6;margin-bottom:14px">گروه بساز و +۲۵ امتیاز بگیر.</p>
<input id="gname" maxlength="24" placeholder="نام گروه جدید..." style="width:100%;padding:12px 14px;border-radius:12px;border:1px solid rgba(255,200,50,.25);background:rgba(0,0,0,.3);color:#fff;font-size:14px;margin-bottom:10px;font-family:inherit">
<button onclick="createGroup()" style="display:block;width:100%;border:none;border-radius:14px;padding:14px;font-size:15px;font-weight:700;margin-bottom:16px;cursor:pointer;font-family:inherit;background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">ساخت گروه (+۲۵)</button>
<div id="list"></div>
<div id="toast" style="position:fixed;bottom:24px;left:16px;right:16px;background:rgba(15,15,40,.95);border:1px solid rgba(251,191,36,.4);border-radius:14px;padding:12px 16px;text-align:center;font-size:13px;font-weight:600;color:#fbbf24;display:none;z-index:50"></div>
"""
    js = """
const user=tg.initDataUnsafe?.user;let uid=user?user.id:null;
function toast(msg){const t=document.getElementById('toast');t.innerText=msg;t.style.display='block';setTimeout(()=>t.style.display='none',2200)}
async function loadList(){const r=await fetch('/api/group/list');const d=await r.json();const el=document.getElementById('list');if(!d.ok||!d.groups.length){el.innerHTML='<div style="color:#64748b;font-size:12px">هنوز گروهی نیست</div>';return}el.innerHTML=d.groups.map(g=>`<div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,200,50,.12);border-radius:14px;padding:12px 14px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center"><div><div style="font-weight:700;font-size:14px">${g.name}</div><div style="font-size:11px;color:#94a3b8">${g.members} عضو</div></div><div style="font-size:11px;color:#94a3b8">${g.score} امتیاز</div></div>`).join('')}
async function createGroup(){if(!uid){toast('از تلگرام وارد شو');return}const name=document.getElementById('gname').value.trim();if(name.length<2){toast('نام گروه کوتاه است');return}const r=await fetch('/api/group/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,name:name})});const d=await r.json();toast(d.msg||'');if(d.ok){document.getElementById('gname').value='';loadList()}}
loadList();
"""
    return HTMLResponse(page_shell("👥", "گروه‌ها", body, "", js))

@app.get("/app/seasons", response_class=HTMLResponse)
async def page_seasons():
    body = """
<p style="color:#94a3b8;font-size:13px;line-height:1.7;margin-bottom:18px">موتور فصل در مراحل بعد فعال می‌شود.</p>
<div style="background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border:1px solid rgba(255,200,50,.12);border-radius:16px;padding:16px;margin-bottom:12px"><div style="font-weight:700;font-size:15px;margin-bottom:4px">فصل جاری</div><div style="font-size:12px;color:#94a3b8;margin-bottom:8px">تایمر و پاداش شروع</div><span style="font-size:11px;font-weight:600;background:rgba(251,191,36,.15);color:#fbbf24;padding:4px 10px;border-radius:20px">مرحله بعد</span></div>
<div style="background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border:1px solid rgba(255,200,50,.12);border-radius:16px;padding:16px;margin-bottom:12px"><div style="font-weight:700;font-size:15px;margin-bottom:4px">مأموریت فصل</div><div style="font-size:12px;color:#94a3b8;margin-bottom:8px">امتیاز و صندوق</div><span style="font-size:11px;font-weight:600;background:rgba(251,191,36,.15);color:#fbbf24;padding:4px 10px;border-radius:20px">مرحله بعد</span></div>
"""
    return HTMLResponse(page_shell("🏆", "فصل‌ها", body))

@app.get("/app/economy", response_class=HTMLResponse)
async def page_economy():
    body = """
<p style="color:#94a3b8;font-size:13px;line-height:1.7;margin-bottom:18px">موتور اقتصاد حرفه‌ای در مراحل بعد فعال می‌شود.</p>
<div style="background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border:1px solid rgba(255,200,50,.12);border-radius:16px;padding:16px;margin-bottom:12px"><div style="font-weight:700;font-size:15px;margin-bottom:4px">Boost</div><div style="font-size:12px;color:#94a3b8;margin-bottom:8px">+قدرت موقت</div><span style="font-size:11px;font-weight:600;background:rgba(251,191,36,.15);color:#fbbf24;padding:4px 10px;border-radius:20px">مرحله بعد</span></div>
<div style="background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border:1px solid rgba(255,200,50,.12);border-radius:16px;padding:16px;margin-bottom:12px"><div style="font-weight:700;font-size:15px;margin-bottom:4px">Season Pass</div><div style="font-size:12px;color:#94a3b8;margin-bottom:8px">پاداش ویژه فصل</div><span style="font-size:11px;font-weight:600;background:rgba(251,191,36,.15);color:#fbbf24;padding:4px 10px;border-radius:20px">مرحله بعد</span></div>
"""
    return HTMLResponse(page_shell("💰", "اقتصاد", body))

@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"NEXA webhook → {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
