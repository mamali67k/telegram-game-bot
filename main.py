# ============================================================
# NEXA — main.py
# نسخه پایدار + اسپلش حرفه‌ای + ذخیره امن + محافظت استارتاپ
# ============================================================

import os
import json
import logging
import random
import tempfile
import shutil
from datetime import datetime, date
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "YOUR_BOT").lstrip("@")
WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://telegram-game-bot-production-09c2.up.railway.app",
).rstrip("/")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBAPP_URL}{WEBHOOK_PATH}"
MINIAPP_URL = f"{WEBAPP_URL}/app"
USERS_FILE = "nexa_users.json"
GROUPS_FILE = "nexa_groups.json"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("nexa")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ====================== STORAGE (امن‌تر) ======================
def _load(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("load %s", path)
        return default

def _save(path, data):
    """ذخیره اتمیک برای جلوگیری از خراب شدن فایل"""
    try:
        dir_name = os.path.dirname(path) or "."
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=dir_name, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp_path = tmp.name
        shutil.move(tmp_path, path)
    except Exception as e:
        logger.exception("save %s failed: %s", path, e)

def load_users(): return _load(USERS_FILE, {})
def save_users(d): _save(USERS_FILE, d)
def load_groups(): return _load(GROUPS_FILE, {})
def save_groups(d): _save(GROUPS_FILE, d)

USER_DEFAULTS = {
    "level": 1, "score": 10, "badge": "تازه‌وارد", "title": "Novice",
    "wars_joined": 0, "attacks": 0, "defenses": 0, "groups": [],
    "season_points": 0, "token_points": 0, "in_war": False,
    "boosts": 0, "boxes": 0, "invites": 0, "invited_by": None,
    "achievements": [], "inventory": [], "combo": 0, "streak": 0,
    "heals": 0, "shop_buys": 0, "rallies": 0, "war_records": 0, "recovers": 0,
    "missions_done": [],
    "last_boost_day": None, "last_mission_day": None, "last_box_day": None,
    "last_active_day": None, "last_pass_day": None, "last_token_day": None,
    "last_challenge_day": None, "last_chest_day": None, "last_power_day": None,
    "last_rank_reward_day": None, "last_combo_day": None, "last_item_day": None,
    "last_heal_day": None, "last_streak_day": None, "last_rally_day": None,
    "last_record_day": None, "last_recover_day": None, "last_daily_missions": None,
    "last_mission_claim": None,
}
ALLOWED_TITLES = {"Novice", "Hunter", "Warrior", "Elite", "Legend"}
SHOP_ITEMS = {
    "badge_gold": {"name": "نشان طلا", "cost": 40, "bonus": 5},
    "badge_fire": {"name": "نشان آتش", "cost": 60, "bonus": 10},
    "badge_crown": {"name": "نشان تاج", "cost": 100, "bonus": 20},
}

# ====================== CSS ======================
WEALTH_CSS = """
.btn,.rowbtns button,.menu a,.titles button{
  position:relative;overflow:hidden;isolation:isolate;
  background-color:rgba(12,14,28,.88)!important;
  background-image:
    radial-gradient(ellipse 120% 80% at 20% 0%, rgba(255,215,0,.22), transparent 55%),
    radial-gradient(ellipse 90% 70% at 90% 100%, rgba(212,175,55,.18), transparent 50%),
    linear-gradient(145deg, rgba(40,32,12,.35), rgba(8,12,24,.5)),
    repeating-linear-gradient(-18deg,transparent,transparent 6px,rgba(255,215,0,.03) 6px,rgba(255,215,0,.03) 7px)!important;
  background-blend-mode:screen,normal,normal,normal;
  border:1px solid rgba(255,200,80,.22)!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.12),0 2px 10px rgba(0,0,0,.25);
  color:#f8fafc!important;text-shadow:0 1px 2px rgba(0,0,0,.35);
}
.btn::before,.rowbtns button::before,.menu a::before{
  content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;
  background:radial-gradient(circle at 50% -20%, rgba(255,230,150,.2), transparent 60%);opacity:.7;
}
@media (hover:hover) and (pointer:fine){
  .btn:hover:not(:disabled),.rowbtns button:hover:not(:disabled){
    filter:brightness(1.18) saturate(1.08);transform:translateY(-2px);
    border-color:rgba(255,220,100,.5)!important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.28),0 0 0 1px rgba(255,200,80,.15),0 8px 22px rgba(255,180,40,.18),0 4px 14px rgba(0,0,0,.3);
    background-image:
      radial-gradient(ellipse 130% 90% at 25% 0%, rgba(255,230,100,.38), transparent 55%),
      radial-gradient(ellipse 100% 80% at 85% 100%, rgba(255,200,60,.28), transparent 50%),
      linear-gradient(145deg, rgba(70,55,15,.45), rgba(20,24,40,.4)),
      repeating-linear-gradient(-18deg,transparent,transparent 6px,rgba(255,215,0,.06) 6px,rgba(255,215,0,.06) 7px)!important;
  }
  .menu a:hover{
    filter:brightness(1.2) saturate(1.1);transform:translateY(-3px);
    border-color:rgba(255,220,100,.55)!important;
    box-shadow:0 10px 28px rgba(255,180,40,.2),0 4px 16px rgba(0,0,0,.3);
    background-image:
      radial-gradient(ellipse 120% 80% at 30% 0%, rgba(255,230,100,.4), transparent 55%),
      radial-gradient(ellipse 90% 70% at 80% 110%, rgba(255,200,60,.3), transparent 50%),
      linear-gradient(160deg, rgba(50,40,10,.5), rgba(12,16,32,.55))!important;
  }
}
button:active:not(:disabled),.btn:active:not(:disabled),.menu a:active{transform:scale(.97)!important;filter:brightness(.96)!important;}
button:disabled,.btn:disabled{cursor:not-allowed;filter:grayscale(.3) brightness(.75)!important;transform:none!important;opacity:.55;}
button,.btn,.menu a{transition:transform .16s ease,filter .16s ease,box-shadow .18s ease,border-color .16s ease;cursor:pointer;-webkit-tap-highlight-color:transparent;}
"""

ICON_CSS = """
.gi{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:9px;margin-left:8px;vertical-align:middle;
background:linear-gradient(145deg,rgba(255,255,255,.28),rgba(255,215,0,.12));border:1px solid rgba(255,255,255,.28);
box-shadow:inset 0 1px 0 rgba(255,255,255,.35),0 2px 8px rgba(0,0,0,.18);backdrop-filter:blur(8px);font-size:14px;line-height:1;flex-shrink:0;}
.btn .gi{margin-left:6px;width:22px;height:22px;border-radius:7px;font-size:12px}
.menu a .gi-lg{display:flex;align-items:center;justify-content:center;margin:0 auto 8px;width:44px;height:44px;border-radius:14px;font-size:22px;
background:linear-gradient(145deg,rgba(255,255,255,.22),rgba(255,200,60,.12));border:1px solid rgba(255,255,255,.25);
box-shadow:inset 0 1px 0 rgba(255,255,255,.3),0 4px 14px rgba(0,0,0,.22);backdrop-filter:blur(10px);}
.btn{display:flex!important;align-items:center;justify-content:center;gap:2px}
"""

HAPTIC_JS = """
function nexaTap(){try{if(window.Telegram&&Telegram.WebApp&&Telegram.WebApp.HapticFeedback){Telegram.WebApp.HapticFeedback.impactOccurred('light')}}catch(e){}}
document.addEventListener('click',function(e){var t=e.target;if(t&&(t.tagName==='BUTTON'||t.closest('button')||t.closest('.menu a'))){nexaTap()}},true);
"""

def badge_for_level(level: int) -> str:
    if level >= 10: return "افسانه‌ای"
    if level >= 5: return "حرفه‌ای"
    if level >= 3: return "مبارز"
    return "تازه‌وارد"

def recalc_level(score: int) -> int:
    return max(1, int(score) // 100 + 1)

def apply_score(uid, delta, users):
    u = users[uid]
    u["score"] = max(0, int(u.get("score", 0)) + int(delta))
    u["level"] = recalc_level(u["score"])
    u["badge"] = badge_for_level(u["level"])
    return u

def today(): return date.today().isoformat()

def days_since(iso_day):
    if not iso_day: return 999
    try: return (date.today() - date.fromisoformat(iso_day[:10])).days
    except Exception: return 999

def get_or_create_pro(user_id, first_name="", username=None):
    users = load_users()
    uid = str(user_id)
    now = datetime.now().isoformat()
    if uid not in users:
        users[uid] = {
            "user_id": user_id, "first_name": first_name, "username": username,
            "joined_at": now, "last_seen": now,
            **{k: (list(v) if isinstance(v, list) else v) for k, v in USER_DEFAULTS.items()},
        }
        save_users(users)
        return users[uid]
    u = users[uid]
    u["last_seen"] = now
    if first_name: u["first_name"] = first_name
    if username is not None: u["username"] = username
    for k, v in USER_DEFAULTS.items():
        if k not in u: u[k] = list(v) if isinstance(v, list) else v
    save_users(users)
    return u

def public_user(u):
    inactive = days_since(u.get("last_active_day") or u.get("last_seen"))
    sp = int(u.get("season_points") or 0)
    return {
        "ok": True, "level": u.get("level", 1), "score": u.get("score", 0),
        "badge": u.get("badge") or badge_for_level(u.get("level", 1)),
        "title": u.get("title") or "Novice",
        "wars_joined": u.get("wars_joined", 0), "attacks": u.get("attacks", 0),
        "defenses": u.get("defenses", 0), "in_war": bool(u.get("in_war")),
        "groups": u.get("groups") or [], "boosts": u.get("boosts", 0), "boxes": u.get("boxes", 0),
        "season_points": sp, "season_progress": min(100, int(sp / 3)),
        "token_points": u.get("token_points", 0), "invites": u.get("invites", 0),
        "achievements": u.get("achievements") or [], "inventory": u.get("inventory") or [],
        "combo": u.get("combo", 0), "streak": u.get("streak", 0),
        "heals": u.get("heals", 0), "shop_buys": u.get("shop_buys", 0),
        "rallies": u.get("rallies", 0), "war_records": u.get("war_records", 0),
        "missions_done": u.get("missions_done") or [],
        "inactive_days": inactive,
        "can_recover": inactive >= 2 and u.get("last_recover_day") != today(),
    }

def require_user(body):
    user_id = body.get("id")
    if not user_id:
        return None, JSONResponse({"ok": False, "msg": "no user"}, status_code=400)
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        get_or_create_pro(int(user_id))
        users = load_users()
    return (users, uid), None

def unlock_achievement(uid, users, code, bonus=15):
    ach = users[uid].setdefault("achievements", [])
    if code in ach: return None
    ach.append(code)
    apply_score(uid, bonus, users)
    return f"دستاورد {code} +{bonus}"

def reset_missions_if_needed(u):
    if u.get("last_daily_missions") != today():
        u["missions_done"] = []
        u["last_daily_missions"] = today()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    args = (message.text or "").split(maxsplit=1)
    inviter = None
    if len(args) > 1 and args[1].startswith("inv_"):
        try: inviter = int(args[1].replace("inv_", ""))
        except ValueError: inviter = None
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
            unlock_achievement(inv_uid, users, "INVITER", 20)
            save_users(users)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☀️ ورود به NEXA", web_app=WebAppInfo(url=MINIAPP_URL))]
    ])
    await message.answer(
        "به <b>NEXA</b> خوش آمدید ☀️\n\n"
        "قدرتت را بیدار کن.\nآینده از آنِ توست.",
        reply_markup=kb
    )

app = FastAPI(title="NEXA")

# محافظت استارتاپ
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    logger.warning("static folder not found – skipped")

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception:
        logger.exception("webhook")
        return {"ok": False}

@app.api_route("/", methods=["GET", "HEAD"])
async def health():
    return {"status": "NEXA is alive ✅", "version": "stable-2"}

# ====================== APIها (بدون تغییر منطقی) ======================
@app.post("/api/user/sync")
async def api_user_sync(request: Request):
    try:
        body = await request.json()
        if not body.get("id"):
            return JSONResponse({"ok": False}, status_code=400)
        return public_user(get_or_create_pro(int(body["id"]), body.get("first_name") or "", body.get("username")))
    except Exception as e:
        logger.exception("sync")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/api/pro/active")
async def api_pro_active(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        reset_missions_if_needed(u)
        if u.get("last_active_day") == today():
            return {"ok": False, "msg": "امروز ثبت شده"}
        if u.get("last_streak_day"):
            try:
                last = date.fromisoformat(u["last_streak_day"])
                u["streak"] = u.get("streak", 0) + 1 if (date.today() - last).days == 1 else 1
            except Exception:
                u["streak"] = 1
        else:
            u["streak"] = 1
        u["last_streak_day"] = today()
        u["last_active_day"] = today()
        bonus = 10 + min(u.get("streak", 1), 7)
        apply_score(uid, bonus, users)
        done = u.setdefault("missions_done", [])
        if "m_active" not in done:
            done.append("m_active")
            apply_score(uid, 15, users)
            bonus += 15
        extra = unlock_achievement(uid, users, "DAILY", 10)
        save_users(users)
        msg = f"فعالیت! +{bonus} (استریک {u.get('streak', 1)})"
        if extra: msg += " | " + extra
        return {**public_user(users[uid]), "msg": msg}
    except Exception as e:
        logger.exception("active")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/pro/recover")
async def api_pro_recover(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        inactive = days_since(u.get("last_active_day") or u.get("last_seen"))
        if inactive < 2: return {"ok": False, "msg": "هنوز نیاز به بازیابی نیست"}
        if u.get("last_recover_day") == today(): return {"ok": False, "msg": "امروز بازیابی کردی"}
        reward = min(20 + inactive * 5, 60)
        u["last_recover_day"] = today()
        u["last_active_day"] = today()
        u["recovers"] = u.get("recovers", 0) + 1
        apply_score(uid, reward, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"بازیابی! +{reward}"}
    except Exception as e:
        logger.exception("recover")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/pro/title")
async def api_pro_title(request: Request):
    try:
        body = await request.json()
        title = (body.get("title") or "").strip()
        if title not in ALLOWED_TITLES: return {"ok": False, "msg": "عنوان مجاز نیست"}
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        users[uid]["title"] = title
        save_users(users)
        return {**public_user(users[uid]), "msg": f"عنوان «{title}»"}
    except Exception as e:
        logger.exception("title")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/pro/achieve")
async def api_pro_achieve(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        gained = []
        for ok, code, bonus in [
            (u.get("attacks", 0) >= 5, "ATK5", 25),
            (u.get("defenses", 0) >= 5, "DEF5", 25),
            (u.get("wars_joined", 0) >= 3, "WAR3", 30),
            (u.get("streak", 0) >= 3, "STREAK3", 20),
            (u.get("invites", 0) >= 3, "INV3", 30),
            (u.get("shop_buys", 0) >= 2, "SHOP2", 20),
        ]:
            if ok:
                msg = unlock_achievement(uid, users, code, bonus)
                if msg: gained.append(msg)
        save_users(users)
        return {**public_user(users[uid]), "msg": " | ".join(gained) if gained else "دستاورد جدیدی نیست"}
    except Exception as e:
        logger.exception("achieve")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/pro/missions/claim")
async def api_pro_missions_claim(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        reset_missions_if_needed(u)
        if u.get("last_mission_claim") == today():
            return {"ok": False, "msg": "امروز مأموریت‌ها رو گرفتی"}
        done = u.get("missions_done") or []
        reward = 20 + len(done) * 8
        u["last_mission_claim"] = today()
        apply_score(uid, reward, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"مأموریت‌ها دریافت شد! +{reward}"}
    except Exception as e:
        logger.exception("missions")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

# ====================== WAR ======================
@app.post("/api/war/join")
async def api_war_join(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if u.get("in_war"): return {"ok": False, "msg": "قبلاً در جنگی"}
        u["in_war"] = True
        u["wars_joined"] = u.get("wars_joined", 0) + 1
        apply_score(uid, 10, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "وارد جنگ شدی! +۱۰"}
    except Exception as e:
        logger.exception("war join")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/war/leave")
async def api_war_leave(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if not u.get("in_war"): return {"ok": False, "msg": "در جنگی نیستی"}
        u["in_war"] = False
        save_users(users)
        return {**public_user(users[uid]), "msg": "از جنگ خارج شدی"}
    except Exception as e:
        logger.exception("war leave")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/war/attack")
async def api_war_attack(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if not u.get("in_war"): return {"ok": False, "msg": "اول وارد جنگ شو"}
        u["attacks"] = u.get("attacks", 0) + 1
        u["combo"] = u.get("combo", 0) + 1
        bonus = 20 + min(u["combo"], 5) * 3
        apply_score(uid, bonus, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"حمله موفق! +{bonus}"}
    except Exception as e:
        logger.exception("attack")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/war/defend")
async def api_war_defend(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if not u.get("in_war"): return {"ok": False, "msg": "اول وارد جنگ شو"}
        u["defenses"] = u.get("defenses", 0) + 1
        apply_score(uid, 15, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "دفاع موفق! +۱۵"}
    except Exception as e:
        logger.exception("defend")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/war/challenge")
async def api_war_challenge(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if not u.get("in_war"): return {"ok": False, "msg": "اول وارد جنگ شو"}
        if u.get("last_challenge_day") == today(): return {"ok": False, "msg": "امروز چالش کردی"}
        u["last_challenge_day"] = today()
        apply_score(uid, 25, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "چالش انجام شد! +۲۵"}
    except Exception as e:
        logger.exception("challenge")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/war/power")
async def api_war_power(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if not u.get("in_war"): return {"ok": False, "msg": "اول وارد جنگ شو"}
        if u.get("last_power_day") == today(): return {"ok": False, "msg": "امروز قدرت زدی"}
        u["last_power_day"] = today()
        apply_score(uid, 18, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "قدرت فعال شد! +۱۸"}
    except Exception as e:
        logger.exception("power")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/war/heal")
async def api_war_heal(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if not u.get("in_war"): return {"ok": False, "msg": "اول وارد جنگ شو"}
        if u.get("last_heal_day") == today(): return {"ok": False, "msg": "امروز شفا گرفتی"}
        u["last_heal_day"] = today()
        u["heals"] = u.get("heals", 0) + 1
        apply_score(uid, 12, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "شفا دریافت شد! +۱۲"}
    except Exception as e:
        logger.exception("heal")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/war/record")
async def api_war_record(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if u.get("last_record_day") == today(): return {"ok": False, "msg": "امروز ثبت کردی"}
        u["last_record_day"] = today()
        u["war_records"] = u.get("war_records", 0) + 1
        apply_score(uid, 15, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "رکورد ثبت شد! +۱۵"}
    except Exception as e:
        logger.exception("record")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.get("/api/war/leaderboard")
async def api_war_leaderboard():
    users = load_users()
    ranks = sorted(
        [{"name": u.get("first_name") or "بازیکن", "attacks": u.get("attacks", 0), "defenses": u.get("defenses", 0)} for u in users.values()],
        key=lambda x: x["attacks"] + x["defenses"], reverse=True
    )[:10]
    return {"ok": True, "ranks": ranks}

# ====================== GROUP + SEASON + ECONOMY (بدون تغییر) ======================
@app.post("/api/group/create")
async def api_group_create(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        name = (body.get("name") or "").strip()[:24]
        if len(name) < 2: return {"ok": False, "msg": "نام کوتاه است"}
        groups = load_groups()
        gid = f"g{len(groups)+1}_{random.randint(1000,9999)}"
        groups[gid] = {"id": gid, "name": name, "owner": int(uid), "members": [int(uid)], "score": 0, "level": 1}
        users[uid].setdefault("groups", []).append(gid)
        apply_score(uid, 25, users)
        save_groups(groups)
        save_users(users)
        return {"ok": True, "msg": f"گروه «{name}» ساخته شد! +۲۵"}
    except Exception as e:
        logger.exception("group create")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/group/join")
async def api_group_join(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        gid = body.get("group_id")
        groups = load_groups()
        if gid not in groups: return {"ok": False, "msg": "گروه پیدا نشد"}
        g = groups[gid]
        if int(uid) in g["members"]: return {"ok": False, "msg": "قبلاً عضوی"}
        g["members"].append(int(uid))
        users[uid].setdefault("groups", []).append(gid)
        apply_score(uid, 10, users)
        save_groups(groups)
        save_users(users)
        return {"ok": True, "msg": "عضو شدی! +۱۰"}
    except Exception as e:
        logger.exception("group join")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/group/leave")
async def api_group_leave(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        gid = body.get("group_id")
        groups = load_groups()
        if gid not in groups: return {"ok": False, "msg": "گروه پیدا نشد"}
        g = groups[gid]
        if int(uid) not in g["members"]: return {"ok": False, "msg": "عضو نیستی"}
        g["members"] = [m for m in g["members"] if m != int(uid)]
        users[uid]["groups"] = [x for x in users[uid].get("groups", []) if x != gid]
        save_groups(groups)
        save_users(users)
        return {"ok": True, "msg": "از گروه خارج شدی"}
    except Exception as e:
        logger.exception("group leave")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/group/donate")
async def api_group_donate(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        gid = body.get("group_id")
        amount = int(body.get("amount") or 10)
        groups = load_groups()
        if gid not in groups: return {"ok": False, "msg": "گروه پیدا نشد"}
        groups[gid]["score"] = groups[gid].get("score", 0) + amount
        apply_score(uid, amount // 2, users)
        save_groups(groups)
        save_users(users)
        return {"ok": True, "msg": f"اهدا شد! گروه +{amount}"}
    except Exception as e:
        logger.exception
