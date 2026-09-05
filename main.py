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
BOT_USERNAME = os.getenv("BOT_USERNAME", "YOUR_BOT")
WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://telegram-game-bot-production-09c2.up.railway.app"
).rstrip("/")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBAPP_URL}{WEBHOOK_PATH}"
MINIAPP_URL = f"{WEBAPP_URL}/app"
USERS_FILE = "nexa_users.json"
GROUPS_FILE = "nexa_groups.json"

# اواتار پیش‌فرض ساده (خورشید پایه NEXA)
DEFAULT_AVATAR = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 128 128'%3E"
    "%3Ccircle cx='64' cy='64' r='42' fill='%23F5A623'/%3E"
    "%3Ccircle cx='50' cy='56' r='5' fill='%230A0A2E'/%3E"
    "%3Ccircle cx='78' cy='56' r='5' fill='%230A0A2E'/%3E"
    "%3Cpath d='M48 78 Q64 92 80 78' fill='none' stroke='%230A0A2E' stroke-width='4' stroke-linecap='round'/%3E"
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
        "last_active_day": None, "last_pass_day": None, "last_token_day": None,
        "invites": 0, "invited_by": None, "token_points": 0,
    }
    if uid not in users:
        users[uid] = defaults.copy()
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
        "level": u.get("level", 1),
        "score": u.get("score", 0),
        "badge": u.get("badge") or badge_for_level(u.get("level", 1)),
        "wars_joined": u.get("wars_joined", 0),
        "attacks": u.get("attacks", 0),
        "defenses": u.get("defenses", 0),
        "in_war": u.get("in_war", False),
        "groups": u.get("groups", []),
        "boosts": u.get("boosts", 0),
        "boxes": u.get("boxes", 0),
        "season_points": u.get("season_points", 0),
        "invites": u.get("invites", 0),
        "token_points": u.get("token_points", 0),
    }

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    args = (message.text or "").split(maxsplit=1)
    inviter = None
    if len(args) > 1 and args[1].startswith("inv_"):
        try:
            inviter = int(args[1].replace("inv_", ""))
        except ValueError:
            inviter = None

    user = message.from_user
    get_or_create_pro(user.id, user.first_name or "", user.username)
    users = load_users()
    uid = str(user.id)

    if inviter and inviter != user.id and not users[uid].get("invited_by"):
        inv_uid = str(inviter)
        if inv_uid in users:
            users[uid]["invited_by"] = inviter
            users[inv_uid]["invites"] = users[inv_uid].get("invites", 0) + 1
            apply_score(inv_uid, 50, users)
            apply_score(uid, 20, users)
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
        return {**public_user(users[uid]), "msg": "فعالیت روزانه ثبت شد! +۱۰"}
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
        return {**public_user(users[uid]), "msg": "وارد جنگ شدی! +۱۰"}
    except Exception as e:
        logger.exception("join")
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
        if not users[uid].get("in_war"):
            return {"ok": False, "msg": "اول وارد جنگ شو"}
        users[uid]["attacks"] = users[uid].get("attacks", 0) + 1
        apply_score(uid, 20, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "حمله موفق! +۲۰"}
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
        if not users[uid].get("in_war"):
            return {"ok": False, "msg": "اول وارد جنگ شو"}
        users[uid]["defenses"] = users[uid].get("defenses", 0) + 1
        apply_score(uid, 15, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "دفاع موفق! +۱۵"}
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
        if not users[uid].get("in_war"):
            return {"ok": False, "msg": "داخل جنگ نیستی"}
        users[uid]["in_war"] = False
        save_users(users)
        return {**public_user(users[uid]), "msg": "از جنگ خارج شدی"}
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
        if len(name) < 2:
            return {"ok": False, "msg": "نام گروه کوتاه است"}
        users = load_users()
        uid = str(user_id)
        if uid not in users:
            get_or_create_pro(int(user_id))
            users = load_users()
        groups = load_groups()
        for g in groups.values():
            if g.get("name", "").lower() == name.lower():
                return {"ok": False, "msg": "نام تکراری است"}
        gid = f"g{int(datetime.now().timestamp())}"
        groups[gid] = {
            "id": gid, "name": name, "owner": int(user_id),
            "members": [int(user_id)], "created_at": datetime.now().isoformat(),
            "score": 0, "level": 1,
        }
        save_groups(groups)
        users[uid].setdefault("groups", []).append(gid)
        apply_score(uid, 25, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"گروه «{name}» ساخته شد! +۲۵"}
    except Exception as e:
        logger.exception("gcreate")
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
            return {"ok": False, "msg": "قبلاً عضو هستی"}
        g.setdefault("members", []).append(int(user_id))
        save_groups(groups)
        if group_id not in users[uid].get("groups", []):
            users[uid].setdefault("groups", []).append(group_id)
        apply_score(uid, 15, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"عضو «{g['name']}» شدی! +۱۵"}
    except Exception as e:
        logger.exception("gjoin")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/group/upgrade")
async def api_group_upgrade(request: Request):
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
            return {"ok": False, "msg": "فقط سازنده می‌تواند ارتقا دهد"}
        if users[uid].get("score", 0) < 20:
            return {"ok": False, "msg": "حداقل ۲۰ امتیاز لازم است"}
        apply_score(uid, -20, users)
        g["level"] = g.get("level", 1) + 1
        g["score"] = g.get("score", 0) + 30
        save_groups(groups)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"گروه به سطح {g['level']} ارتقا یافت"}
    except Exception as e:
        logger.exception("gup")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/group/help")
async def api_group_help(request: Request):
    """کمک گروهی: کاربر عضو حداقل یک گروه باشد — +30"""
    try:
        body = await request.json()
        user_id = body.get("id")
        if not user_id:
            return JSONResponse({"ok": False, "msg": "no user"}, status_code=400)
        users = load_users()
        uid = str(user_id)
        if uid not in users:
            return {"ok": False, "msg": "اول وارد شو"}
        if not users[uid].get("groups"):
            return {"ok": False, "msg": "اول عضو یک گروه شو"}
        apply_score(uid, 30, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "کمک گروهی ثبت شد! +۳۰"}
    except Exception as e:
        logger.exception("ghelp")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.get("/api/group/list")
async def api_group_list():
    groups = load_groups()
    items = [{
        "id": g["id"], "name": g["name"],
        "members": len(g.get("members", [])),
        "score": g.get("score", 0), "level": g.get("level", 1),
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
        today = date.today().isoformat()
        if users[uid].get("last_boost_day") == today:
            return {"ok": False, "msg": "امروز Boost گرفتی"}
        users[uid]["last_boost_day"] = today
        users[uid]["boosts"] = users[uid].get("boosts", 0) + 1
        apply_score(uid, 30, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "Boost! +۳۰"}
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
        today = date.today().isoformat()
        if users[uid].get("last_box_day") == today:
            return {"ok": False, "msg": "جعبه امروز باز شده"}
        prize = random.randint(20, 80)
        users[uid]["last_box_day"] = today
        users[uid]["boxes"] = users[uid].get("boxes", 0) + 1
        apply_score(uid, prize, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"Mystery Box! +{prize}"}
    except Exception as e:
        logger.exception("box")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/economy/pass")
async def api_economy_pass(request: Request):
    """Season Pass روزانه: +100"""
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
        today = date.today().isoformat()
        if users[uid].get("last_pass_day") == today:
            return {"ok": False, "msg": "امروز Season Pass گرفتی"}
        users[uid]["last_pass_day"] = today
        apply_score(uid, 100, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "Season Pass! +۱۰۰"}
    except Exception as e:
        logger.exception("pass")
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
        today = date.today().isoformat()
        if users[uid].get("last_mission_day") == today:
            return {"ok": False, "msg": "مأموریت امروز انجام شده"}
        users[uid]["last_mission_day"] = today
        users[uid]["season_points"] = users[uid].get("season_points", 0) + 40
        apply_score(uid, 40, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "مأموریت فصل! +۴۰"}
    except Exception as e:
        logger.exception("mission")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/future/token")
async def api_future_token(request: Request):
    """مأموریت توکن آینده: +40 امتیاز + امتیاز توکن"""
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
        today = date.today().isoformat()
        if users[uid].get("last_token_day") == today:
            return {"ok": False, "msg": "مأموریت توکن امروز انجام شده"}
        users[uid]["last_token_day"] = today
        users[uid]["token_points"] = users[uid].get("token_points", 0) + 40
        apply_score(uid, 40, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "مأموریت توکن آینده! +۴۰"}
    except Exception as e:
        logger.exception("token")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.get("/api/rank/top")
async def api_rank_top():
    users = load_users()
    rows = [{
        "name": u.get("first_name") or u.get("username") or "بازیکن",
        "score": u.get("score", 0),
        "level": u.get("level", 1),
    } for u in users.values()]
    rows.sort(key=lambda x: x["score"], reverse=True)
    return {"ok": True, "ranks": rows[:20]}

BRAND_HEADER_CSS = """
.brand-bar{display:flex;align-items:center;gap:10px}
.brand-logo{width:36px;height:36px;border-radius:50%;overflow:hidden;flex-shrink:0;box-shadow:0 0 0 2px rgba(255,215,0,.45)}
.brand-logo img{width:100%;height:100%;object-fit:cover;display:block}
.brand-logo.fb{display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#ffd700,#ff8c00);font-size:18px}
.brand-name{font-size:18px;font-weight:800;letter-spacing:3px;background:linear-gradient(90deg,#ffe566,#ffb800);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
"""
BRAND_HEADER_HTML = """
<div class="brand-bar"><div class="brand-logo"><img src="/static/nexa-logo.jpg" alt="NEXA" onerror="this.parentElement.classList.add('fb');this.parentElement.innerHTML='☀️';"></div><div class="brand-name">NEXA</div></div>
"""

@app.get("/app", response_class=HTMLResponse)
async def mini_app():
    # اواتار داخل HTML به صورت ثابت تا خطای JS ندهد
    avatar = DEFAULT_AVATAR
    bot_user = BOT_USERNAME
    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>NEXA</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Vazirmatn',sans-serif;-webkit-tap-highlight-color:transparent}}
body{{min-height:100vh;background:#05051a;color:#fff;overflow-x:hidden}}
.nexa-wm{{position:fixed;inset:0;pointer-events:none;z-index:0;background:url('/static/nexa-logo.jpg') center 38%/min(72vw,300px) no-repeat;opacity:.08}}
.nexa-wm::after{{content:'NEXA';position:absolute;bottom:10%;left:0;right:0;text-align:center;font-size:42px;font-weight:800;letter-spacing:14px;color:#ffd700;opacity:.07}}
#splash{{position:fixed;inset:0;z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;
background:#05051a url('/static/nexa-logo.jpg') center center / cover no-repeat;padding-bottom:18%;transition:opacity .4s,visibility .4s}}
#splash.hide{{opacity:0;visibility:hidden;pointer-events:none}}
.splash-slogan{{font-size:15px;color:rgba(255,255,255,.78);font-weight:600;text-align:center;padding:0 28px;margin-bottom:18px;text-shadow:0 2px 14px rgba(0,0,0,.55)}}
.loader{{width:56px;height:4px;background:rgba(255,255,255,.22);border-radius:4px;overflow:hidden;opacity:.7;margin-bottom:8px}}
.loader-bar{{height:100%;width:0;background:linear-gradient(90deg,#ff8c00,#ffd700);transition:width linear}}
#main{{display:none;position:relative;z-index:1;padding:14px 14px 36px;background-image:radial-gradient(ellipse 90% 45% at 50% -8%,rgba(255,200,50,.1),transparent 50%),linear-gradient(180deg,#0a0a2e,#05051a 55%,#020210 100%)}}
#main.show{{display:block}}
.top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}}
{BRAND_HEADER_CSS}
.chip{{font-size:11px;background:rgba(251,191,36,.15);color:#fbbf24;padding:5px 11px;border-radius:20px;font-weight:600}}
.profile{{background:linear-gradient(165deg,rgba(255,255,255,.09),rgba(255,255,255,.03));border:1px solid rgba(255,200,50,.16);border-radius:18px;padding:14px 16px;display:flex;align-items:center;gap:12px;margin-bottom:14px}}
.profile img{{width:52px;height:52px;border-radius:50%;border:2px solid #fbbf24;object-fit:cover;background:#1a1635}}
.profile .meta{{flex:1}}
.profile .name{{font-weight:700;font-size:15px}}
.profile .user{{font-size:12px;color:#94a3b8;margin-top:2px}}
.stats{{display:flex;gap:10px;margin-top:8px}}
.stat{{flex:1;text-align:center;background:rgba(0,0,0,.25);border-radius:12px;padding:8px 4px}}
.stat b{{display:block;font-size:15px;color:#fbbf24}}
.stat span{{font-size:10px;color:#94a3b8}}
.daily button{{width:100%;border:none;border-radius:14px;padding:12px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;background:rgba(251,191,36,.12);color:#fbbf24;border:1px solid rgba(251,191,36,.25);margin-bottom:14px}}
.label{{font-size:11px;color:#64748b;font-weight:600;margin-bottom:10px}}
.menu{{display:grid;grid-template-columns:1fr 1fr;gap:11px}}
.menu a{{text-decoration:none;color:#fff;background:linear-gradient(160deg,rgba(255,255,255,.08),rgba(255,255,255,.02));border:1px solid rgba(255,200,50,.14);border-radius:16px;padding:18px 10px;text-align:center;font-size:13px;font-weight:700}}
.menu a .ic{{display:block;font-size:26px;margin-bottom:8px}}
.menu a .sub{{display:block;margin-top:5px;font-size:10px;font-weight:500;color:#94a3b8}}
.invite{{margin-top:16px;font-size:12px;color:#94a3b8;text-align:center;line-height:1.6}}
.invite code{{display:block;margin-top:6px;padding:10px;background:rgba(0,0,0,.3);border-radius:10px;color:#fbbf24;font-size:11px;word-break:break-all}}
.footer{{text-align:center;margin-top:22px;font-size:11px;color:#475569;letter-spacing:2px}}
.footer strong{{color:#fbbf24}}
.toast{{position:fixed;bottom:24px;left:16px;right:16px;background:rgba(15,15,40,.95);border:1px solid rgba(251,191,36,.4);border-radius:14px;padding:12px 16px;text-align:center;font-size:13px;font-weight:600;color:#fbbf24;display:none;z-index:50}}
</style>
</head>
<body>
<div class="nexa-wm"></div>
<div id="splash">
  <div class="splash-slogan">قدرتت را بیدار کن • آینده از آنِ توست</div>
  <div class="loader"><div class="loader-bar" id="loaderBar"></div></div>
</div>
<div id="main">
  <div class="top">{BRAND_HEADER_HTML}<div class="chip" id="badge">تازه‌وارد</div></div>
  <div class="profile">
    <img id="avatar" src="{avatar}" alt="">
    <div class="meta">
      <div class="name" id="name">...</div>
      <div class="user" id="username"></div>
      <div class="stats">
        <div class="stat"><b id="level">1</b><span>سطح</span></div>
        <div class="stat"><b id="score">10</b><span>امتیاز</span></div>
      </div>
    </div>
  </div>
  <div class="daily"><button type="button" id="btnActive">ثبت فعالیت روزانه (+۱۰)</button></div>
  <div class="label">موتورهای NEXA</div>
  <div class="menu">
    <a href="/app/wars"><span class="ic">⚔️</span>جنگ‌ها<span class="sub">حمله • دفاع</span></a>
    <a href="/app/groups"><span class="ic">👥</span>گروه‌ها<span class="sub">ساخت • کمک</span></a>
    <a href="/app/seasons"><span class="ic">🏆</span>فصل‌ها<span class="sub">مأموریت • توکن</span></a>
    <a href="/app/economy"><span class="ic">💰</span>اقتصاد<span class="sub">Boost • Pass</span></a>
  </div>
  <div class="invite">لینک دعوت:<code id="invLink">—</code></div>
  <div class="footer"><strong>NEXA</strong></div>
</div>
<div class="toast" id="toast"></div>
<script>
(function(){{
  var DEFAULT_AVATAR = "{avatar}";
  var BOT_USER = "{bot_user}";
  function toast(msg){{
    var t = document.getElementById('toast');
    if(!t) return;
    t.innerText = msg;
    t.style.display = 'block';
    setTimeout(function(){{ t.style.display = 'none'; }}, 2200);
  }}
  function hideSplash(){{
    var s = document.getElementById('splash');
    var m = document.getElementById('main');
    if(s) s.classList.add('hide');
    if(m) m.classList.add('show');
    try {{ sessionStorage.setItem('nexa_splash_seen', '1'); }} catch(e) {{}}
  }}
  // لودینگ: اول ۵ثانیه، برگشت ۱ثانیه — همیشه تمام می‌شود
  var seen = false;
  try {{ seen = sessionStorage.getItem('nexa_splash_seen') === '1'; }} catch(e) {{}}
  var delay = seen ? 1000 : 5000;
  var bar = document.getElementById('loaderBar');
  if(bar){{
    bar.style.transitionDuration = (delay/1000) + 's';
    setTimeout(function(){{ bar.style.width = '100%'; }}, 30);
  }}
  setTimeout(hideSplash, delay);
  // پشتیبان: اگر چیزی خطا داد حداکثر ۶ ثانیه بعد اسپلش بسته شود
  setTimeout(hideSplash, 6000);

  var tg = null;
  try {{ tg = window.Telegram.WebApp; tg.ready(); tg.expand(); }} catch(e) {{}}
  try {{ tg.setHeaderColor('#05051a'); }} catch(e) {{}}
  try {{ tg.setBackgroundColor('#05051a'); }} catch(e) {{}}

  var user = null;
  try {{ user = tg && tg.initDataUnsafe && tg.initDataUnsafe.user; }} catch(e) {{}}

  if(user){{
    document.getElementById('name').innerText = (user.first_name||'') + (user.last_name ? (' ' + user.last_name) : '');
    document.getElementById('username').innerText = user.username ? ('@' + user.username) : '';
    document.getElementById('avatar').src = user.photo_url || DEFAULT_AVATAR;
    document.getElementById('invLink').innerText = 'https://t.me/' + BOT_USER + '?start=inv_' + user.id;
    fetch('/api/user/sync', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{id:user.id, first_name:user.first_name, username:user.username}})
    }}).then(function(r){{ return r.json(); }}).then(function(d){{
      if(d && d.ok){{
        document.getElementById('level').innerText = d.level;
        document.getElementById('score').innerText = d.score;
        document.getElementById('badge').innerText = d.badge || 'تازه‌وارد';
      }}
    }}).catch(function(){{}});
  }} else {{
    document.getElementById('name').innerText = 'کاربر مهمان';
    document.getElementById('avatar').src = DEFAULT_AVATAR;
  }}

  document.getElementById('btnActive').onclick = function(){{
    if(!user){{ toast('از تلگرام وارد شو'); return; }}
    fetch('/api/pro/active', {{
      method:'POST', headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{id:user.id}})
    }}).then(function(r){{ return r.json(); }}).then(function(d){{
      toast(d.msg || '');
      if(d.ok){{
        document.getElementById('score').innerText = d.score;
        document.getElementById('level').innerText = d.level;
        document.getElementById('badge').innerText = d.badge;
      }}
    }}).catch(function(){{ toast('خطا در ارتباط'); }});
  }};
}})();
</script>
</body>
</html>"""
    return HTMLResponse(html)

def page_shell(title_icon, title, body_html, extra_js=""):
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>NEXA - {title}</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Vazirmatn',sans-serif}}
body{{min-height:100vh;color:#fff;background:#05051a;position:relative}}
.nexa-wm{{position:fixed;inset:0;pointer-events:none;z-index:0;background:url('/static/nexa-logo.jpg') center 40%/min(70vw,280px) no-repeat;opacity:.07}}
.wrap{{position:relative;z-index:1;padding:14px 14px 40px;background:linear-gradient(180deg,#0a0a2e,#05051a)}}
.top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;gap:10px}}
.top-right{{display:flex;align-items:center;gap:10px}}
.back{{width:40px;height:40px;border-radius:12px;background:rgba(255,255,255,.08);border:1px solid rgba(255,200,50,.25);display:flex;align-items:center;justify-content:center;color:#fbbf24;text-decoration:none;font-size:17px}}
.page-title{{font-size:15px;font-weight:700;color:#e2e8f0}}
{BRAND_HEADER_CSS}
.footer{{text-align:center;margin-top:22px;font-size:11px;color:#475569;letter-spacing:2px}}
.footer strong{{color:#fbbf24}}
.btn{{display:block;width:100%;border:none;border-radius:14px;padding:14px;font-size:15px;font-weight:700;margin-bottom:10px;cursor:pointer;font-family:inherit}}
.toast{{position:fixed;bottom:24px;left:16px;right:16px;background:rgba(15,15,40,.95);border:1px solid rgba(251,191,36,.4);border-radius:14px;padding:12px;text-align:center;font-size:13px;font-weight:600;color:#fbbf24;display:none;z-index:50}}
</style></head><body>
<div class="nexa-wm"></div>
<div class="wrap">
<div class="top"><div class="top-right"><a class="back" href="/app">→</a>{BRAND_HEADER_HTML}</div>
<div class="page-title">{title_icon} {title}</div></div>
{body_html}
<div class="footer"><strong>NEXA</strong></div>
</div>
<script>
var tg=window.Telegram.WebApp;try{{tg.ready();tg.expand();}}catch(e){{}}
function toast(msg){{var t=document.getElementById('toast');if(!t)return;t.innerText=msg;t.style.display='block';setTimeout(function(){{t.style.display='none'}},2200)}}
{extra_js}
</script></body></html>"""

@app.get("/app/wars", response_class=HTMLResponse)
async def page_wars():
    body = """
<p style="color:#94a3b8;font-size:13px;margin-bottom:14px">ورود، حمله، دفاع، خروج</p>
<div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,200,50,.15);border-radius:18px;padding:16px;margin-bottom:14px">
<div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px"><span>وضعیت</span><b id="warStatus" style="color:#fbbf24">—</b></div>
<div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px"><span>امتیاز</span><b id="score" style="color:#fbbf24">—</b></div>
<div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px"><span>حمله</span><b id="attacks" style="color:#fbbf24">0</b></div>
<div style="display:flex;justify-content:space-between;font-size:13px"><span>دفاع</span><b id="defenses" style="color:#fbbf24">0</b></div>
</div>
<button class="btn" id="btnJoin" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">ورود (+۱۰)</button>
<button class="btn" id="btnAttack" disabled style="background:linear-gradient(90deg,#dc2626,#f97316);color:#fff;opacity:.45">حمله (+۲۰)</button>
<button class="btn" id="btnDefend" disabled style="background:linear-gradient(90deg,#1d4ed8,#3b82f6);color:#fff;opacity:.45">دفاع (+۱۵)</button>
<button class="btn" id="btnLeave" disabled style="background:rgba(255,255,255,.08);color:#94a3b8;opacity:.45">خروج</button>
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function apply(d){if(!d||!d.ok)return;document.getElementById('score').innerText=d.score;document.getElementById('attacks').innerText=d.attacks||0;document.getElementById('defenses').innerText=d.defenses||0;
if(d.in_war){document.getElementById('warStatus').innerText='در جنگ';['btnAttack','btnDefend','btnLeave'].forEach(function(id){var b=document.getElementById(id);b.disabled=false;b.style.opacity='1'});document.getElementById('btnJoin').disabled=true;document.getElementById('btnJoin').style.opacity='.45'}
else{document.getElementById('warStatus').innerText='خارج';['btnAttack','btnDefend','btnLeave'].forEach(function(id){var b=document.getElementById(id);b.disabled=true;b.style.opacity='.45'});document.getElementById('btnJoin').disabled=false;document.getElementById('btnJoin').style.opacity='1'}}
function call(url){if(!uid){toast('وارد شو');return}fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)apply(d)})}
document.getElementById('btnJoin').onclick=function(){call('/api/war/join')};
document.getElementById('btnAttack').onclick=function(){call('/api/war/attack')};
document.getElementById('btnDefend').onclick=function(){call('/api/war/defend')};
document.getElementById('btnLeave').onclick=function(){call('/api/war/leave')};
if(uid)fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})}).then(function(r){return r.json()}).then(apply);
"""
    return HTMLResponse(page_shell("⚔️", "جنگ‌ها", body, js))

@app.get("/app/groups", response_class=HTMLResponse)
async def page_groups():
    body = """
<p style="color:#94a3b8;font-size:13px;margin-bottom:12px">ساخت، عضویت، ارتقا، کمک گروهی</p>
<input id="gname" maxlength="24" placeholder="نام گروه..." style="width:100%;padding:12px;border-radius:12px;border:1px solid rgba(255,200,50,.25);background:rgba(0,0,0,.3);color:#fff;margin-bottom:10px;font-family:inherit">
<button class="btn" id="btnCreate" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">ساخت (+۲۵)</button>
<button class="btn" id="btnHelp" style="background:rgba(59,130,246,.25);color:#93c5fd">کمک گروهی (+۳۰)</button>
<div id="list"></div>
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function loadList(){fetch('/api/group/list').then(function(r){return r.json()}).then(function(d){
var el=document.getElementById('list');if(!d.ok||!d.groups.length){el.innerHTML='<div style="color:#64748b;font-size:12px">گروهی نیست</div>';return}
el.innerHTML=d.groups.map(function(g){var own=uid&&g.owner===uid;
return '<div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,200,50,.12);border-radius:14px;padding:12px;margin-bottom:8px"><div style="display:flex;justify-content:space-between;align-items:center"><div><b>'+g.name+'</b><div style="font-size:11px;color:#94a3b8">'+g.members+' عضو • لول '+(g.level||1)+'</div></div><button data-join="'+g.id+'" style="border:none;border-radius:10px;padding:8px 12px;background:rgba(59,130,246,.35);color:#93c5fd;font-weight:700;cursor:pointer">عضویت</button></div>'+(own?'<button data-up="'+g.id+'" style="width:100%;margin-top:8px;border:none;border-radius:10px;padding:8px;background:rgba(251,191,36,.15);color:#fbbf24;font-weight:700;cursor:pointer">ارتقا (−۲۰)</button>':'')+'</div>'}).join('');
el.querySelectorAll('[data-join]').forEach(function(b){b.onclick=function(){join(b.getAttribute('data-join'))}});
el.querySelectorAll('[data-up]').forEach(function(b){b.onclick=function(){up(b.getAttribute('data-up'))}});
})}
function join(gid){if(!uid){toast('وارد شو');return}fetch('/api/group/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,group_id:gid})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)loadList()})}
function up(gid){if(!uid)return;fetch('/api/group/upgrade',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,group_id:gid})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)loadList()})}
document.getElementById('btnCreate').onclick=function(){if(!uid){toast('وارد شو');return}var name=document.getElementById('gname').value.trim();if(name.length<2){toast('نام کوتاه');return}fetch('/api/group/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,name:name})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok){document.getElementById('gname').value='';loadList()}})};
document.getElementById('btnHelp').onclick=function(){if(!uid){toast('وارد شو');return}fetch('/api/group/help',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'')})};
loadList();
"""
    return HTMLResponse(page_shell("👥", "گروه‌ها", body, js))

@app.get("/app/seasons", response_class=HTMLResponse)
async def page_seasons():
    body = """
<p style="color:#94a3b8;font-size:13px;margin-bottom:14px">مأموریت فصل و توکن آینده</p>
<div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,200,50,.15);border-radius:18px;padding:16px;margin-bottom:14px">
<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:8px"><span>امتیاز فصل</span><b id="sp" style="color:#fbbf24">0</b></div>
<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:8px"><span>امتیاز توکن</span><b id="tp" style="color:#fbbf24">0</b></div>
<div style="display:flex;justify-content:space-between;font-size:13px"><span>امتیاز کل</span><b id="score" style="color:#fbbf24">—</b></div>
</div>
<button class="btn" id="btnMission" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">مأموریت فصل (+۴۰)</button>
<button class="btn" id="btnToken" style="background:linear-gradient(90deg,#0ea5e9,#38bdf8);color:#0a0a2e">مأموریت توکن آینده (+۴۰)</button>
<div style="margin-top:16px;font-size:12px;color:#64748b;margin-bottom:8px">رتبه برتر</div>
<div id="ranks"></div>
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function fill(d){if(!d||!d.ok)return;document.getElementById('score').innerText=d.score;document.getElementById('sp').innerText=d.season_points||0;document.getElementById('tp').innerText=d.token_points||0}
function sync(){if(!uid)return;fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})}).then(function(r){return r.json()}).then(fill)}
document.getElementById('btnMission').onclick=function(){if(!uid){toast('وارد شو');return}fetch('/api/season/mission',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok){fill(d);ranks()}})};
document.getElementById('btnToken').onclick=function(){if(!uid){toast('وارد شو');return}fetch('/api/future/token',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)fill(d)})};
function ranks(){fetch('/api/rank/top').then(function(r){return r.json()}).then(function(d){var el=document.getElementById('ranks');if(!d.ok||!d.ranks.length){el.innerHTML='—';return}el.innerHTML=d.ranks.map(function(x,i){return '<div style="display:flex;justify-content:space-between;padding:10px;background:rgba(255,255,255,.05);border-radius:12px;margin-bottom:6px;font-size:13px"><span><b style="color:#fbbf24">'+(i+1)+'.</b> '+x.name+'</span><span style="color:#94a3b8">'+x.score+'</span></div>'}).join('')})}
sync();ranks();
"""
    return HTMLResponse(page_shell("🏆", "فصل‌ها", body, js))

@app.get("/app/economy", response_class=HTMLResponse)
async def page_economy():
    body = """
<p style="color:#94a3b8;font-size:13px;margin-bottom:14px">Boost، Season Pass، Mystery Box</p>
<div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,200,50,.15);border-radius:18px;padding:16px;margin-bottom:14px">
<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:8px"><span>Boost</span><b id="boosts" style="color:#fbbf24">0</b></div>
<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:8px"><span>جعبه</span><b id="boxes" style="color:#fbbf24">0</b></div>
<div style="display:flex;justify-content:space-between;font-size:13px"><span>امتیاز</span><b id="score" style="color:#fbbf24">—</b></div>
</div>
<button class="btn" id="btnBoost" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">Boost (+۳۰)</button>
<button class="btn" id="btnPass" style="background:linear-gradient(90deg,#059669,#34d399);color:#0a0a2e">Season Pass (+۱۰۰)</button>
<button class="btn" id="btnBox" style="background:linear-gradient(90deg,#7c3aed,#a78bfa);color:#fff">Mystery Box</button>
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function fill(d){if(!d||!d.ok)return;document.getElementById('score').innerText=d.score;document.getElementById('boosts').innerText=d.boosts||0;document.getElementById('boxes').innerText=d.boxes||0}
function sync(){if(!uid)return;fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})}).then(function(r){return r.json()}).then(fill)}
function call(url){if(!uid){toast('وارد شو');return}fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)fill(d)})}
document.getElementById('btnBoost').onclick=function(){call('/api/economy/boost')};
document.getElementById('btnPass').onclick=function(){call('/api/economy/pass')};
document.getElementById('btnBox').onclick=function(){call('/api/economy/box')};
sync();
"""
    return HTMLResponse(page_shell("💰", "اقتصاد", body, js))

@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("NEXA started")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
