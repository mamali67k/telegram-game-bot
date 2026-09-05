import os
import json
import logging
import random
from datetime import datetime, date
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

# اواتار پیش‌فرض ساده — شخصیت خورشید NEXA (پایه برای فرم‌های بعدی)
DEFAULT_AVATAR = (
    "data:image/svg+xml;utf8,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 128 128'%3E"
    "%3Cdefs%3E%3CradialGradient id='g' cx='35%25' cy='35%25'%3E"
    "%3Cstop offset='0%25' stop-color='%23FFE566'/%3E"
    "%3Cstop offset='70%25' stop-color='%23F5A623'/%3E"
    "%3Cstop offset='100%25' stop-color='%23C77D00'/%3E"
    "%3C/radialGradient%3E%3C/defs%3E"
    "%3Ccircle cx='64' cy='64' r='40' fill='url(%23g)'/%3E"
    "%3Cg stroke='%23F5A623' stroke-width='4' stroke-linecap='round'%3E"
    "%3Cline x1='64' y1='8' x2='64' y2='20'/%3E"
    "%3Cline x1='64' y1='108' x2='64' y2='120'/%3E"
    "%3Cline x1='8' y1='64' x2='20' y2='64'/%3E"
    "%3Cline x1='108' y1='64' x2='120' y2='64'/%3E"
    "%3Cline x1='22' y1='22' x2='30' y2='30'/%3E"
    "%3Cline x1='98' y1='98' x2='106' y2='106'/%3E"
    "%3Cline x1='106' y1='22' x2='98' y2='30'/%3E"
    "%3Cline x1='30' y1='98' x2='22' y2='106'/%3E"
    "%3C/g%3E"
    "%3Ccircle cx='50' cy='56' r='5' fill='%230A0A2E'/%3E"
    "%3Ccircle cx='78' cy='56' r='5' fill='%230A0A2E'/%3E"
    "%3Cpath d='M48 76 Q64 90 80 76' fill='none' stroke='%230A0A2E' stroke-width='4' stroke-linecap='round'/%3E"
    "%3C/svg%3E"
)

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
    defaults = {
        "user_id": user_id, "first_name": first_name, "username": username,
        "level": 1, "score": 10, "badge": "تازه‌وارد",
        "joined_at": datetime.now().isoformat(), "last_seen": datetime.now().isoformat(),
        "wars_joined": 0, "attacks": 0, "defenses": 0, "groups": [],
        "season_points": 0, "in_war": False, "boosts": 0, "boxes": 0,
        "last_boost_day": None, "last_mission_day": None, "last_box_day": None,
        "last_active_day": None, "invites": 0, "invited_by": None,
    }
    if uid not in users:
        users[uid] = defaults
        save_users(users)
    else:
        users[uid]["last_seen"] = datetime.now().isoformat()
        if first_name:
            users[uid]["first_name"] = first_name
        if username is not None:
            users[uid]["username"] = username
        for k, v in defaults.items():
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

def public_user(u):
    return {
        "ok": True,
        "level": u["level"],
        "score": u["score"],
        "badge": u.get("badge") or badge_for_level(u["level"]),
        "wars_joined": u.get("wars_joined", 0),
        "attacks": u.get("attacks", 0),
        "defenses": u.get("defenses", 0),
        "in_war": u.get("in_war", False),
        "groups": u.get("groups", []),
        "boosts": u.get("boosts", 0),
        "boxes": u.get("boxes", 0),
        "season_points": u.get("season_points", 0),
        "invites": u.get("invites", 0),
    }

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # پشتیبانی از لینک دعوت: /start inv_USERID
    args = (message.text or "").split(maxsplit=1)
    inviter = None
    if len(args) > 1 and args[1].startswith("inv_"):
        try:
            inviter = int(args[1].replace("inv_", ""))
        except ValueError:
            inviter = None

    user = message.from_user
    pro = get_or_create_pro(user.id, user.first_name or "", user.username)
    users = load_users()
    uid = str(user.id)

    if inviter and inviter != user.id and not users[uid].get("invited_by"):
        inv_uid = str(inviter)
        if inv_uid in users:
            users[uid]["invited_by"] = inviter
            users[inv_uid]["invites"] = users[inv_uid].get("invites", 0) + 1
            apply_score(inv_uid, 50, users)  # پاداش دعوت طبق پلن
            apply_score(uid, 20, users)      # پاداش عضو جدید
            save_users(users)

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
        return public_user(pro)
    except Exception as e:
        logger.exception("sync")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/api/pro/active")
async def api_pro_active(request: Request):
    """فعالیت روزانه هویت: +10"""
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
        today = date.today().isoformat()
        if u.get("last_active_day") == today:
            return {"ok": False, "msg": "امروز فعالیتت ثبت شده."}
        u["last_active_day"] = today
        apply_score(uid, 10, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "فعالیت روزانه ثبت شد! +۱۰ امتیاز"}
    except Exception as e:
        logger.exception("active")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

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
            return {**public_user(u), "msg": "قبلاً در جنگ هستی"}
        u["in_war"] = True
        u["wars_joined"] = u.get("wars_joined", 0) + 1
        apply_score(uid, 10, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "وارد جنگ شدی! +۱۰ امتیاز"}
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
        return {**public_user(users[uid]), "msg": "حمله موفق! +۲۰ امتیاز"}
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
        return {**public_user(users[uid]), "msg": "دفاع موفق! +۱۵ امتیاز"}
    except Exception as e:
        logger.exception("defend")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/war/leave")
async def api_war_leave(request: Request):
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
            return {"ok": False, "msg": "داخل جنگ نیستی"}
        u["in_war"] = False
        save_users(users)
        return {**public_user(users[uid]), "msg": "از جنگ خارج شدی."}
    except Exception as e:
        logger.exception("leave")
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
            "id": gid, "name": name, "owner": int(user_id),
            "members": [int(user_id)], "created_at": datetime.now().isoformat(),
            "score": 0, "level": 1,
        }
        save_groups(groups)
        if gid not in users[uid].get("groups", []):
            users[uid].setdefault("groups", []).append(gid)
        apply_score(uid, 25, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"گروه «{name}» ساخته شد! +۲۵ امتیاز"}
    except Exception as e:
        logger.exception("group create")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/group/join")
async def api_group_join(request: Request):
    try:
        body = await request.json()
        user_id = body.get("id")
        group_id = body.get("group_id")
        if not user_id or not group_id:
            return JSONResponse({"ok": False, "msg": "داده ناقص"}, status_code=400)
        users = load_users()
        uid = str(user_id)
        if uid not in users:
            get_or_create_pro(int(user_id))
            users = load_users()
        groups = load_groups()
        if group_id not in groups:
            return {"ok": False, "msg": "گروه پیدا نشد"}
        g = groups[group_id]
        if int(user_id) in g.get("members", []):
            return {"ok": False, "msg": "قبلاً عضو این گروه هستی"}
        g.setdefault("members", []).append(int(user_id))
        save_groups(groups)
        if group_id not in users[uid].get("groups", []):
            users[uid].setdefault("groups", []).append(group_id)
        apply_score(uid, 15, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"عضو «{g['name']}» شدی! +۱۵ امتیاز"}
    except Exception as e:
        logger.exception("group join")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/group/upgrade")
async def api_group_upgrade(request: Request):
    """ارتقا گروه توسط مالک — هزینه ۲۰ امتیاز شخصی، +سطح گروه"""
    try:
        body = await request.json()
        user_id = body.get("id")
        group_id = body.get("group_id")
        if not user_id or not group_id:
            return JSONResponse({"ok": False, "msg": "داده ناقص"}, status_code=400)
        users = load_users()
        uid = str(user_id)
        if uid not in users:
            return {"ok": False, "msg": "اول وارد شو"}
        groups = load_groups()
        if group_id not in groups:
            return {"ok": False, "msg": "گروه پیدا نشد"}
        g = groups[group_id]
        if int(user_id) != g.get("owner"):
            return {"ok": False, "msg": "فقط سازنده گروه می‌تواند ارتقا دهد"}
        if users[uid].get("score", 0) < 20:
            return {"ok": False, "msg": "حداقل ۲۰ امتیاز برای ارتقا لازم است"}
        apply_score(uid, -20, users)
        g["level"] = g.get("level", 1) + 1
        g["score"] = g.get("score", 0) + 30
        save_groups(groups)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"گروه «{g['name']}» به سطح {g['level']} ارتقا یافت!", "group_level": g["level"]}
    except Exception as e:
        logger.exception("group upgrade")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.get("/api/group/list")
async def api_group_list():
    groups = load_groups()
    items = [{
        "id": g["id"], "name": g["name"],
        "members": len(g.get("members", [])),
        "score": g.get("score", 0),
        "level": g.get("level", 1),
        "owner": g.get("owner"),
    } for g in groups.values()]
    items.sort(key=lambda x: x["score"], reverse=True)
    return {"ok": True, "groups": items[:30]}

@app.post("/api/economy/boost")
async def api_economy_boost(request: Request):
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
        today = date.today().isoformat()
        if u.get("last_boost_day") == today:
            return {"ok": False, "msg": "امروز Boost گرفتی."}
        u["last_boost_day"] = today
        u["boosts"] = u.get("boosts", 0) + 1
        apply_score(uid, 30, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "Boost فعال شد! +۳۰ امتیاز"}
    except Exception as e:
        logger.exception("boost")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/economy/box")
async def api_economy_box(request: Request):
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
        today = date.today().isoformat()
        if u.get("last_box_day") == today:
            return {"ok": False, "msg": "جعبه امروز باز شده."}
        prize = random.randint(20, 80)
        u["last_box_day"] = today
        u["boxes"] = u.get("boxes", 0) + 1
        apply_score(uid, prize, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"Mystery Box! +{prize} امتیاز", "prize": prize}
    except Exception as e:
        logger.exception("box")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/season/mission")
async def api_season_mission(request: Request):
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
        today = date.today().isoformat()
        if u.get("last_mission_day") == today:
            return {"ok": False, "msg": "مأموریت امروز انجام شده."}
        u["last_mission_day"] = today
        u["season_points"] = u.get("season_points", 0) + 40
        apply_score(uid, 40, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "مأموریت فصل انجام شد! +۴۰ امتیاز"}
    except Exception as e:
        logger.exception("mission")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.get("/api/rank/top")
async def api_rank_top():
    users = load_users()
    rows = []
    for u in users.values():
        rows.append({
            "name": u.get("first_name") or u.get("username") or "بازیکن",
            "score": u.get("score", 0),
            "level": u.get("level", 1),
            "badge": u.get("badge") or badge_for_level(u.get("level", 1)),
        })
    rows.sort(key=lambda x: x["score"], reverse=True)
    return {"ok": True, "ranks": rows[:20]}

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
  <div class="brand-logo">
    <img src="/static/nexa-logo.jpg" alt="NEXA" onerror="this.parentElement.classList.add('fb');this.parentElement.innerHTML='☀️';">
  </div>
  <div class="brand-name">NEXA</div>
</div>
"""

DEFAULT_AVATAR_JS = DEFAULT_AVATAR.replace("'", "\\'")

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
#splash{position:fixed;inset:0;z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;
background:#05051a url('/static/nexa-logo.jpg') center center / cover no-repeat;padding-bottom:18%;transition:opacity .4s,visibility .4s}
#splash.hide{opacity:0;visibility:hidden;pointer-events:none}
.splash-slogan{font-size:15px;color:rgba(255,255,255,.78);font-weight:600;text-align:center;padding:0 28px;margin-bottom:18px;
text-shadow:0 2px 14px rgba(0,0,0,.55);opacity:0;animation:up .8s ease .2s forwards}
@keyframes up{from{opacity:0;transform:translateY(10px)}to{opacity:.85;transform:translateY(0)}}
.loader{width:56px;height:4px;background:rgba(255,255,255,.22);border-radius:4px;overflow:hidden;opacity:.7;margin-bottom:8px}
.loader-bar{height:100%;width:0;background:linear-gradient(90deg,rgba(255,140,0,.9),rgba(255,215,0,.9))}
.loader-bar.slow{animation:load5 5s linear forwards}
.loader-bar.fast{animation:load1 1s linear forwards}
@keyframes load5{to{width:100%}}
@keyframes load1{to{width:100%}}
#main{display:none;position:relative;z-index:1;padding:14px 14px 36px;background-image:radial-gradient(ellipse 90% 45% at 50% -8%,rgba(255,200,50,.1),transparent 50%),linear-gradient(180deg,#0a0a2e 0%,#05051a 55%,#020210 100%)}
#main.show{display:block}
.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
""" + BRAND_HEADER_CSS + r"""
.chip{font-size:11px;background:rgba(251,191,36,.15);color:#fbbf24;padding:5px 11px;border-radius:20px;font-weight:600}
.profile{background:linear-gradient(165deg,rgba(255,255,255,.09),rgba(255,255,255,.03));border:1px solid rgba(255,200,50,.16);border-radius:18px;padding:14px 16px;display:flex;align-items:center;gap:12px;margin-bottom:14px}
.profile img{width:52px;height:52px;border-radius:50%;border:2px solid #fbbf24;object-fit:cover;background:#1a1635}
.profile .meta{flex:1}
.profile .name{font-weight:700;font-size:15px}
.profile .user{font-size:12px;color:#94a3b8;margin-top:2px}
.stats{display:flex;gap:10px;margin-top:8px}
.stat{flex:1;text-align:center;background:rgba(0,0,0,.25);border-radius:12px;padding:8px 4px}
.stat b{display:block;font-size:15px;color:#fbbf24}
.stat span{font-size:10px;color:#94a3b8}
.daily{margin-bottom:16px}
.daily button{width:100%;border:none;border-radius:14px;padding:12px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;
background:rgba(251,191,36,.12);color:#fbbf24;border:1px solid rgba(251,191,36,.25)}
.label{font-size:11px;color:#64748b;font-weight:600;margin-bottom:10px;letter-spacing:1px}
.menu{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.menu a{text-decoration:none;color:#fff;background:linear-gradient(160deg,rgba(255,255,255,.08),rgba(255,255,255,.02));border:1px solid rgba(255,200,50,.14);border-radius:16px;padding:18px 10px;text-align:center;font-size:13px;font-weight:700}
.menu a:active{transform:scale(.97);border-color:rgba(255,200,50,.4)}
.menu a .ic{display:block;font-size:26px;margin-bottom:8px}
.menu a .sub{display:block;margin-top:5px;font-size:10px;font-weight:500;color:#94a3b8}
.invite{margin-top:16px;font-size:12px;color:#94a3b8;text-align:center;line-height:1.6}
.invite code{display:block;margin-top:6px;padding:10px;background:rgba(0,0,0,.3);border-radius:10px;color:#fbbf24;font-size:11px;word-break:break-all}
.footer{text-align:center;margin-top:22px;font-size:11px;color:#475569;letter-spacing:2px}
.footer strong{color:#fbbf24}
.toast{position:fixed;bottom:24px;left:16px;right:16px;background:rgba(15,15,40,.95);border:1px solid rgba(251,191,36,.4);border-radius:14px;padding:12px 16px;text-align:center;font-size:13px;font-weight:600;color:#fbbf24;display:none;z-index:50}
</style>
</head>
<body>
<div class="nexa-wm"></div>
<div id="splash">
  <div class="splash-slogan">قدرتت را بیدار کن • آینده از آنِ توست</div>
  <div class="loader"><div class="loader-bar" id="loaderBar"></div></div>
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
  <div class="daily"><button onclick="doActive()">ثبت فعالیت روزانه (+۱۰)</button></div>
  <div class="label">موتورهای NEXA</div>
  <div class="menu">
    <a href="/app/wars"><span class="ic">⚔️</span>جنگ‌ها<span class="sub">حمله • دفاع</span></a>
    <a href="/app/groups"><span class="ic">👥</span>گروه‌ها<span class="sub">ساخت • ارتقا</span></a>
    <a href="/app/seasons"><span class="ic">🏆</span>فصل‌ها<span class="sub">مأموریت • رتبه</span></a>
    <a href="/app/economy"><span class="ic">💰</span>اقتصاد<span class="sub">Boost • جعبه</span></a>
  </div>
  <div class="invite">لینک دعوت تو (پاداش ۵۰ برای تو، ۲۰ برای دوست):
    <code id="invLink">—</code>
  </div>
  <div class="footer"><strong>NEXA</strong> • Pro Arena</div>
</div>
<div class="toast" id="toast"></div>
<script>
const DEFAULT_AVATAR = loc_DEFAULT;
const tg=window.Telegram.WebApp;tg.ready();tg.expand();
try{tg.setHeaderColor('#05051a')}catch(e){}
try{tg.setBackgroundColor('#05051a')}catch(e){}
function toast(msg){const t=document.getElementById('toast');t.innerText=msg;t.style.display='block';setTimeout(()=>t.style.display='none',2200)}
const seen=sessionStorage.getItem('nexa_splash_seen');
const bar=document.getElementById('loaderBar');
const delay=seen?1000:5000;
bar.classList.add(seen?'fast':'slow');
setTimeout(()=>{document.getElementById('splash').classList.add('hide');document.getElementById('main').classList.add('show');sessionStorage.setItem('nexa_splash_seen','1')},delay);
const user=tg.initDataUnsafe?.user;
if(user){
  document.getElementById('name').innerText=(user.first_name||'')+(user.last_name?(' '+user.last_name):'');
  document.getElementById('username').innerText=user.username?'@'+user.username:'';
  document.getElementById('avatar').src=user.photo_url||DEFAULT_AVATAR;
  document.getElementById('invLink').innerText='https://t.me/'+(tg.initDataUnsafe?.start_param!==undefined?'':'') + (window.BotUsername||'YourBot') + '?start=inv_'+user.id;
  // اگر یوزرنیم ربات را در env نداریم، لینک نسبی نمایش می‌دهیم
  document.getElementById('invLink').innerText='t.me/YOUR_BOT?start=inv_'+user.id;
  fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:user.id,first_name:user.first_name,username:user.username})})
  .then(r=>r.json()).then(d=>{if(d&&d.ok){document.getElementById('level').innerText=d.level;document.getElementById('score').innerText=d.score;document.getElementById('badge').innerText=d.badge||'تازه‌وارد'}}).catch(()=>{});
}else{
  document.getElementById('name').innerText='کاربر مهمان';
  document.getElementById('avatar').src=DEFAULT_AVATAR;
}
async function doActive(){
  if(!user){toast('از تلگرام وارد شو');return}
  const r=await fetch('/api/pro/active',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:user.id})});
  const d=await r.json();toast(d.msg||'');
  if(d.ok){document.getElementById('score').innerText=d.score;document.getElementById('level').innerText=d.level;document.getElementById('badge').innerText=d.badge}
}
</script>
</body>
</html>
""".replace("loc_DEFAULT", f"'{DEFAULT_AVATAR}'")
    return HTMLResponse(html)

def page_shell(title_icon, title, body_html, extra_js=""):
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
.page-title{{font-size:15px;font-weight:700;color:#e2e8f0}}
{BRAND_HEADER_CSS}
.footer{{text-align:center;margin-top:22px;font-size:11px;color:#475569;letter-spacing:2px}}
.footer strong{{color:#fbbf24}}
.btn{{display:block;width:100%;border:none;border-radius:14px;padding:14px;font-size:15px;font-weight:700;margin-bottom:10px;cursor:pointer;font-family:inherit}}
.toast{{position:fixed;bottom:24px;left:16px;right:16px;background:rgba(15,15,40,.95);border:1px solid rgba(251,191,36,.4);border-radius:14px;padding:12px 16px;text-align:center;font-size:13px;font-weight:600;color:#fbbf24;display:none;z-index:50}}
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
function toast(msg){{const t=document.getElementById('toast');if(!t)return;t.innerText=msg;t.style.display='block';setTimeout(()=>t.style.display='none',2200)}}
{extra_js}
</script>
</body>
</html>"""

@app.get("/app/wars", response_class=HTMLResponse)
async def page_wars():
    body = """
<p style="color:#94a3b8;font-size:13px;margin-bottom:14px">ورود، حمله، دفاع و خروج.</p>
<div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,200,50,.15);border-radius:18px;padding:16px;margin-bottom:14px">
  <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px"><span>وضعیت</span><b id="warStatus" style="color:#fbbf24">خارج از جنگ</b></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px"><span>امتیاز</span><b id="score" style="color:#fbbf24">—</b></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px"><span>سطح</span><b id="level" style="color:#fbbf24">—</b></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px"><span>حمله</span><b id="attacks" style="color:#fbbf24">0</b></div>
  <div style="display:flex;justify-content:space-between;font-size:13px"><span>دفاع</span><b id="defenses" style="color:#fbbf24">0</b></div>
</div>
<button class="btn" id="btnJoin" onclick="doJoin()" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">ورود به جنگ (+۱۰)</button>
<button class="btn" id="btnAttack" onclick="doAttack()" disabled style="background:linear-gradient(90deg,#dc2626,#f97316);color:#fff;opacity:.45">حمله (+۲۰)</button>
<button class="btn" id="btnDefend" onclick="doDefend()" disabled style="background:linear-gradient(90deg,#1d4ed8,#3b82f6);color:#fff;opacity:.45">دفاع (+۱۵)</button>
<button class="btn" id="btnLeave" onclick="doLeave()" disabled style="background:rgba(255,255,255,.08);color:#94a3b8;opacity:.45">خروج از جنگ</button>
<div class="toast" id="toast"></div>
"""
    js = """
const user=tg.initDataUnsafe?.user;let uid=user?user.id:null;
function apply(d){if(!d||!d.ok)return;document.getElementById('score').innerText=d.score;document.getElementById('level').innerText=d.level;document.getElementById('attacks').innerText=d.attacks||0;document.getElementById('defenses').innerText=d.defenses||0;
if(d.in_war){document.getElementById('warStatus').innerText='در میدان جنگ';['btnAttack','btnDefend','btnLeave'].forEach(id=>{const b=document.getElementById(id);b.disabled=false;b.style.opacity='1'});document.getElementById('btnJoin').disabled=true;document.getElementById('btnJoin').style.opacity='.45'}
else{document.getElementById('warStatus').innerText='خارج از جنگ';['btnAttack','btnDefend','btnLeave'].forEach(id=>{const b=document.getElementById(id);b.disabled=true;b.style.opacity='.45'});document.getElementById('btnJoin').disabled=false;document.getElementById('btnJoin').style.opacity='1'}}
async function sync(){if(!uid)return;const r=await fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})});apply(await r.json())}
async function call(url){if(!uid){toast('از تلگرام وارد شو');return}const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})});const d=await r.json();toast(d.msg||'');if(d.ok)apply(d)}
function doJoin(){call('/api/war/join')}
function doAttack(){call('/api/war/attack')}
function doDefend(){call('/api/war/defend')}
function doLeave(){call('/api/war/leave')}
sync();
"""
    return HTMLResponse(page_shell("⚔️", "جنگ‌ها", body, js))

@app.get("/app/groups", response_class=HTMLResponse)
async def page_groups():
    body = """
<p style="color:#94a3b8;font-size:13px;margin-bottom:12px">ساخت، عضویت و ارتقا گروه (فقط مالک).</p>
<input id="gname" maxlength="24" placeholder="نام گروه جدید..." style="width:100%;padding:12px 14px;border-radius:12px;border:1px solid rgba(255,200,50,.25);background:rgba(0,0,0,.3);color:#fff;font-size:14px;margin-bottom:10px;font-family:inherit">
<button class="btn" onclick="createGroup()" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">ساخت گروه (+۲۵)</button>
<div id="list" style="margin-top:8px"></div>
<div class="toast" id="toast"></div>
"""
    js = """
const user=tg.initDataUnsafe?.user;let uid=user?user.id:null;
async function loadList(){const r=await fetch('/api/group/list');const d=await r.json();const el=document.getElementById('list');if(!d.ok||!d.groups.length){el.innerHTML='<div style="color:#64748b;font-size:12px">هنوز گروهی نیست</div>';return}
el.innerHTML=d.groups.map(g=>{
  const isOwner=uid&&g.owner===uid;
  return `<div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,200,50,.12);border-radius:14px;padding:12px;margin-bottom:8px">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px">
      <div><div style="font-weight:700;font-size:14px">${g.name}</div>
      <div style="font-size:11px;color:#94a3b8">${g.members} عضو • سطح ${g.level||1}</div></div>
      <button onclick="joinGroup('${g.id}')" style="border:none;border-radius:10px;padding:8px 12px;font-size:12px;font-weight:700;background:rgba(59,130,246,.35);color:#93c5fd;cursor:pointer;font-family:inherit">عضویت</button>
    </div>
    ${isOwner?`<button onclick="upgradeGroup('${g.id}')" style="width:100%;border:none;border-radius:10px;padding:8px;font-size:12px;font-weight:700;background:rgba(251,191,36,.15);color:#fbbf24;cursor:pointer;font-family:inherit">ارتقا گروه (−۲۰ امتیاز)</button>`:''}
  </div>`}).join('')}
async function createGroup(){if(!uid){toast('از تلگرام وارد شو');return}const name=document.getElementById('gname').value.trim();if(name.length<2){toast('نام کوتاه است');return}const r=await fetch('/api/group/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,name})});const d=await r.json();toast(d.msg||'');if(d.ok){document.getElementById('gname').value='';loadList()}}
async function joinGroup(gid){if(!uid){toast('از تلگرام وارد شو');return}const r=await fetch('/api/group/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,group_id:gid})});const d=await r.json();toast(d.msg||'');if(d.ok)loadList()}
async function upgradeGroup(gid){if(!uid)return;const r=await fetch('/api/group/upgrade',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,group_id:gid})});const d=await r.json();toast(d.msg||'');if(d.ok)loadList()}
loadList();
"""
    return HTMLResponse(page_shell("👥", "گروه‌ها", body, js))

@app.get("/app/seasons", response_class=HTMLResponse)
async def page_seasons():
    body = """
<p style="color:#94a3b8;font-size:13px;margin-bottom:14px">مأموریت فصل و رتبه‌بندی.</p>
<div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,200,50,.15);border-radius:18px;padding:16px;margin-bottom:14px">
  <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:8px"><span>امتیاز فصل</span><b id="sp" style="color:#fbbf24">0</b></div>
  <div style="display:flex;justify-content:space-between;font-size:13px"><span>امتیاز کل</span><b id="score" style="color:#fbbf24">—</b></div>
</div>
<button class="btn" onclick="doMission()" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">مأموریت فصل (+۴۰)</button>
<div style="margin-top:18px;font-size:12px;color:#64748b;margin-bottom:8px;font-weight:600">رتبه برتر</div>
<div id="ranks"></div>
<div class="toast" id="toast"></div>
"""
    js = """
const user=tg.initDataUnsafe?.user;let uid=user?user.id:null;
async function sync(){if(!uid)return;const r=await fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})});const d=await r.json();if(d.ok){document.getElementById('score').innerText=d.score;document.getElementById('sp').innerText=d.season_points||0}}
async function doMission(){if(!uid){toast('از تلگرام وارد شو');return}const r=await fetch('/api/season/mission',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})});const d=await r.json();toast(d.msg||'');if(d.ok){document.getElementById('score').innerText=d.score;document.getElementById('sp').innerText=d.season_points;loadRanks()}}
async function loadRanks(){const r=await fetch('/api/rank/top');const d=await r.json();const el=document.getElementById('ranks');if(!d.ok||!d.ranks.length){el.innerHTML='<div style="color:#64748b;font-size:12px">هنوز رتبه‌ای نیست</div>';return}el.innerHTML=d.ranks.map((x,i)=>`<div style="display:flex;justify-content:space-between;padding:10px 12px;background:rgba(255,255,255,.05);border-radius:12px;margin-bottom:6px;font-size:13px"><span><b style="color:#fbbf24">${i+1}.</b> ${x.name}</span><span style="color:#94a3b8">${x.score}</span></div>`).join('')}
sync();loadRanks();
"""
    return HTMLResponse(page_shell("🏆", "فصل‌ها", body, js))

@app.get("/app/economy", response_class=HTMLResponse)
async def page_economy():
    body = """
<p style="color:#94a3b8;font-size:13px;margin-bottom:14px">Boost و Mystery Box روزانه.</p>
<div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,200,50,.15);border-radius:18px;padding:16px;margin-bottom:14px">
  <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:8px"><span>Boostها</span><b id="boosts" style="color:#fbbf24">0</b></div>
  <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:8px"><span>جعبه‌ها</span><b id="boxes" style="color:#fbbf24">0</b></div>
  <div style="display:flex;justify-content:space-between;font-size:13px"><span>امتیاز کل</span><b id="score" style="color:#fbbf24">—</b></div>
</div>
<button class="btn" onclick="doBoost()" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">Boost (+۳۰)</button>
<button class="btn" onclick="doBox()" style="background:linear-gradient(90deg,#7c3aed,#a78bfa);color:#fff">Mystery Box</button>
<div class="toast" id="toast"></div>
"""
    js = """
const user=tg.initDataUnsafe?.user;let uid=user?user.id:null;
function fill(d){if(!d||!d.ok)return;document.getElementById('score').innerText=d.score;document.getElementById('boosts').innerText=d.boosts||0;document.getElementById('boxes').innerText=d.boxes||0}
async function sync(){if(!uid)return;const r=await fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})});fill(await r.json())}
async function doBoost(){if(!uid){toast('از تلگرام وارد شو');return}const r=await fetch('/api/economy/boost',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})});const d=await r.json();toast(d.msg||'');if(d.ok)fill(d)}
async function doBox(){if(!uid){toast('از تلگرام وارد شو');return}const r=await fetch('/api/economy/box',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})});const d=await r.json();toast(d.msg||'');if(d.ok)fill(d)}
sync();
"""
    return HTMLResponse(page_shell("💰", "اقتصاد", body, js))

@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"NEXA webhook → {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
