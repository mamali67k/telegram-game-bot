# ============================================================
# NEXA — main.py
# هاور روشن‌تر + پس‌زمینه ثروت نیمه‌محو روی کلیدها + ارتقا
# فیکس: محافظت در برابر نبودن پوشه static (جلوگیری از کرش استارتاپ)
# ============================================================

import os
import json
import logging
import random
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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

# پس‌زمینه ثروت نیمه‌محو + هاور روشن‌تر
WEALTH_CSS = """
/* لایه ثروت: طلای نرم + عمق تیره (نیمه‌محو تا متن خوانا بماند) */
.btn,.rowbtns button,.menu a,.titles button{
  position:relative;
  overflow:hidden;
  isolation:isolate;
  background-color:rgba(12,14,28,.88)!important;
  background-image:
    radial-gradient(ellipse 120% 80% at 20% 0%, rgba(255,215,0,.22), transparent 55%),
    radial-gradient(ellipse 90% 70% at 90% 100%, rgba(212,175,55,.18), transparent 50%),
    linear-gradient(145deg, rgba(40,32,12,.35), rgba(8,12,24,.5)),
    repeating-linear-gradient(
      -18deg,
      transparent,
      transparent 6px,
      rgba(255,215,0,.03) 6px,
      rgba(255,215,0,.03) 7px
    )!important;
  background-blend-mode:screen,normal,normal,normal;
  border:1px solid rgba(255,200,80,.22)!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.12),0 2px 10px rgba(0,0,0,.25);
  color:#f8fafc!important;
  text-shadow:0 1px 2px rgba(0,0,0,.35);
}
.btn::before,.rowbtns button::before,.menu a::before{
  content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;
  background:radial-gradient(circle at 50% -20%, rgba(255,230,150,.2), transparent 60%);
  opacity:.7;
}
/* هاور: محیط روشن‌تر + درخشش طلا */
@media (hover:hover) and (pointer:fine){
  .btn:hover:not(:disabled),.rowbtns button:hover:not(:disabled){
    filter:brightness(1.18) saturate(1.08);
    transform:translateY(-2px);
    border-color:rgba(255,220,100,.5)!important;
    box-shadow:
      inset 0 1px 0 rgba(255,255,255,.28),
      0 0 0 1px rgba(255,200,80,.15),
      0 8px 22px rgba(255,180,40,.18),
      0 4px 14px rgba(0,0,0,.3);
    background-image:
      radial-gradient(ellipse 130% 90% at 25% 0%, rgba(255,230,100,.38), transparent 55%),
      radial-gradient(ellipse 100% 80% at 85% 100%, rgba(255,200,60,.28), transparent 50%),
      linear-gradient(145deg, rgba(70,55,15,.45), rgba(20,24,40,.4)),
      repeating-linear-gradient(-18deg,transparent,transparent 6px,rgba(255,215,0,.06) 6px,rgba(255,215,0,.06) 7px)!important;
  }
  .menu a:hover{
    filter:brightness(1.2) saturate(1.1);
    transform:translateY(-3px);
    border-color:rgba(255,220,100,.55)!important;
    box-shadow:0 10px 28px rgba(255,180,40,.2),0 4px 16px rgba(0,0,0,.3);
    background-image:
      radial-gradient(ellipse 120% 80% at 30% 0%, rgba(255,230,100,.4), transparent 55%),
      radial-gradient(ellipse 90% 70% at 80% 110%, rgba(255,200,60,.3), transparent 50%),
      linear-gradient(160deg, rgba(50,40,10,.5), rgba(12,16,32,.55))!important;
  }
  .titles button:hover{
    filter:brightness(1.15);
    border-color:rgba(255,220,100,.55)!important;
    background-image:
      radial-gradient(ellipse at 50% 0%, rgba(255,220,100,.35), transparent 70%),
      linear-gradient(145deg, rgba(50,40,12,.5), rgba(15,18,30,.6))!important;
    color:#fef3c7!important;
  }
  a.back:hover{
    background:rgba(255,220,100,.18)!important;
    border-color:rgba(255,200,80,.5)!important;
    box-shadow:0 0 16px rgba(255,180,40,.2);
  }
}
button:active:not(:disabled),.btn:active:not(:disabled),.menu a:active,.titles button:active{
  transform:scale(.97)!important;
  filter:brightness(.96)!important;
}
button:disabled,.btn:disabled{
  cursor:not-allowed;filter:grayscale(.3) brightness(.75)!important;
  transform:none!important;box-shadow:none!important;opacity:.55;
}
@media (prefers-reduced-motion:reduce){
  button,.btn,.menu a,.titles button,a.back{transition:none!important}
}
button,.btn,.menu a,.titles button,a.back{
  transition:transform .16s ease,filter .16s ease,box-shadow .18s ease,border-color .16s ease,background .2s ease;
  -webkit-tap-highlight-color:transparent;cursor:pointer;
}
"""

ICON_CSS = """
.gi{
  display:inline-flex;align-items:center;justify-content:center;
  width:26px;height:26px;border-radius:9px;margin-left:8px;vertical-align:middle;
  background:linear-gradient(145deg,rgba(255,255,255,.28),rgba(255,215,0,.12));
  border:1px solid rgba(255,255,255,.28);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.35),0 2px 8px rgba(0,0,0,.18);
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  font-size:14px;line-height:1;flex-shrink:0;
}
.btn .gi,.rowbtns button .gi{margin-left:6px;width:22px;height:22px;border-radius:7px;font-size:12px}
.menu a .gi-lg{
  display:flex;align-items:center;justify-content:center;margin:0 auto 8px;
  width:44px;height:44px;border-radius:14px;font-size:22px;
  background:linear-gradient(145deg,rgba(255,255,255,.22),rgba(255,200,60,.12));
  border:1px solid rgba(255,255,255,.25);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.3),0 4px 14px rgba(0,0,0,.22);
  backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
}
.btn{display:flex!important;align-items:center;justify-content:center;gap:2px}
.rowbtns button{display:inline-flex;align-items:center;justify-content:center}
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
    await message.answer("به NEXA خوش آمدید ☀️\n\nقدرتت را بیدار کن.\nآینده از آنِ توست.", reply_markup=kb)

app = FastAPI(title="NEXA")

# ===== فیکس حیاتی: جلوگیری از کرش وقتی پوشه static وجود ندارد =====
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    logger.warning("static folder not found – mounting skipped (app will still run)")

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
    return {"status": "NEXA is alive ✅"}

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
        return {**public_user(users[uid]), "msg": f"بازیابی فشار! +{reward}"}
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

# ====================== GROUP ======================
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
        logger.exception("donate")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/group/upgrade")
async def api_group_upgrade(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        gid = body.get("group_id")
        groups = load_groups()
        if gid not in groups: return {"ok": False, "msg": "گروه پیدا نشد"}
        g = groups[gid]
        if g["owner"] != int(uid): return {"ok": False, "msg": "فقط صاحب گروه"}
        g["level"] = g.get("level", 1) + 1
        apply_score(uid, 20, users)
        save_groups(groups)
        save_users(users)
        return {"ok": True, "msg": f"گروه ارتقا یافت به سطح {g['level']}"}
    except Exception as e:
        logger.exception("upgrade")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/group/rally")
async def api_group_rally(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if u.get("last_rally_day") == today(): return {"ok": False, "msg": "امروز رالی زدی"}
        u["last_rally_day"] = today()
        u["rallies"] = u.get("rallies", 0) + 1
        apply_score(uid, 15, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "رالی گروه! +۱۵"}
    except Exception as e:
        logger.exception("rally")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/group/help")
async def api_group_help(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        apply_score(uid, 30, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "کمک گروهی انجام شد! +۳۰"}
    except Exception as e:
        logger.exception("help")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.get("/api/group/list")
async def api_group_list():
    groups = load_groups()
    lst = []
    for g in groups.values():
        lst.append({
            "id": g["id"], "name": g["name"], "owner": g["owner"],
            "members": len(g.get("members", [])), "score": g.get("score", 0), "level": g.get("level", 1)
        })
    return {"ok": True, "groups": lst}

# ====================== SEASON ======================
@app.post("/api/season/mission")
async def api_season_mission(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if u.get("last_mission_day") == today(): return {"ok": False, "msg": "امروز مأموریت فصلی زدی"}
        u["last_mission_day"] = today()
        u["season_points"] = u.get("season_points", 0) + 40
        apply_score(uid, 40, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "مأموریت فصل! +۴۰"}
    except Exception as e:
        logger.exception("season mission")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/season/chest")
async def api_season_chest(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if u.get("last_chest_day") == today(): return {"ok": False, "msg": "امروز صندوق باز کردی"}
        u["last_chest_day"] = today()
        u["season_points"] = u.get("season_points", 0) + 60
        apply_score(uid, 60, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "صندوق فصل! +۶۰"}
    except Exception as e:
        logger.exception("chest")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/season/rank_reward")
async def api_season_rank_reward(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if u.get("last_rank_reward_day") == today(): return {"ok": False, "msg": "امروز پاداش رتبه گرفتی"}
        u["last_rank_reward_day"] = today()
        apply_score(uid, 80, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "پاداش Top10! +۸۰"}
    except Exception as e:
        logger.exception("rank reward")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/future/token")
async def api_future_token(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if u.get("last_token_day") == today(): return {"ok": False, "msg": "امروز توکن گرفتی"}
        u["last_token_day"] = today()
        u["token_points"] = u.get("token_points", 0) + 40
        apply_score(uid, 20, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "توکن آینده! +۴۰"}
    except Exception as e:
        logger.exception("token")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.get("/api/rank/top")
async def api_rank_top():
    users = load_users()
    ranks = sorted(
        [{"name": u.get("first_name") or "بازیکن", "score": u.get("score", 0)} for u in users.values()],
        key=lambda x: x["score"], reverse=True
    )[:10]
    return {"ok": True, "ranks": ranks}

# ====================== ECONOMY ======================
@app.post("/api/economy/boost")
async def api_economy_boost(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if u.get("last_boost_day") == today(): return {"ok": False, "msg": "امروز Boost زدی"}
        u["last_boost_day"] = today()
        u["boosts"] = u.get("boosts", 0) + 1
        apply_score(uid, 30, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "Boost فعال! +۳۰"}
    except Exception as e:
        logger.exception("boost")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/economy/pass")
async def api_economy_pass(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if u.get("last_pass_day") == today(): return {"ok": False, "msg": "امروز Pass گرفتی"}
        u["last_pass_day"] = today()
        apply_score(uid, 100, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "Season Pass! +۱۰۰"}
    except Exception as e:
        logger.exception("pass")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/economy/box")
async def api_economy_box(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if u.get("last_box_day") == today(): return {"ok": False, "msg": "امروز جعبه باز کردی"}
        u["last_box_day"] = today()
        u["boxes"] = u.get("boxes", 0) + 1
        reward = random.randint(15, 45)
        apply_score(uid, reward, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"جعبه مرموز! +{reward}"}
    except Exception as e:
        logger.exception("box")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/economy/item")
async def api_economy_item(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        if u.get("last_item_day") == today(): return {"ok": False, "msg": "امروز آیتم گرفتی"}
        u["last_item_day"] = today()
        apply_score(uid, 25, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "آیتم روزانه! +۲۵"}
    except Exception as e:
        logger.exception("item")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.post("/api/shop/buy")
async def api_shop_buy(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err: return err
        users, uid = ctx
        u = users[uid]
        item_id = body.get("item_id")
        if item_id not in SHOP_ITEMS: return {"ok": False, "msg": "آیتم نامعتبر"}
        item = SHOP_ITEMS[item_id]
        if u.get("score", 0) < item["cost"]: return {"ok": False, "msg": "امتیاز کافی نیست"}
        apply_score(uid, -item["cost"], users)
        apply_score(uid, item["bonus"], users)
        u["shop_buys"] = u.get("shop_buys", 0) + 1
        inv = u.setdefault("inventory", [])
        inv.append({"item": item_id, "name": item["name"]})
        save_users(users)
        return {**public_user(users[uid]), "msg": f"خرید {item['name']} موفق!"}
    except Exception as e:
        logger.exception("shop")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

# ====================== PAGES ======================
def page_shell(icon: str, title: str, body: str, extra_js: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>{title} • NEXA</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Vazirmatn',sans-serif;background:linear-gradient(165deg,#0a0c18 0%,#12182b 50%,#0d1220 100%);color:#e2e8f0;min-height:100vh;padding:16px;padding-bottom:40px}}
.header{{text-align:center;margin-bottom:18px}}
.header h1{{font-size:1.5rem;font-weight:800;color:#fbbf24;text-shadow:0 0 20px rgba(251,191,36,.3)}}
.btn{{display:flex;align-items:center;justify-content:center;width:100%;padding:14px;margin-bottom:10px;border-radius:14px;font-size:15px;font-weight:700;border:none;color:#f8fafc;cursor:pointer}}
{WEALTH_CSS}
{ICON_CSS}
.toast{{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:rgba(15,20,35,.95);border:1px solid rgba(255,200,80,.3);color:#fbbf24;padding:12px 20px;border-radius:12px;font-size:14px;opacity:0;transition:opacity .3s;z-index:99;pointer-events:none}}
.toast.show{{opacity:1}}
.bar{{height:8px;background:rgba(255,255,255,.08);border-radius:99px;overflow:hidden;margin:8px 0}}
.bar i{{display:block;height:100%;background:linear-gradient(90deg,#f59e0b,#fbbf24);border-radius:99px;width:0;transition:width .4s}}
a.back{{display:inline-block;margin-top:16px;padding:10px 18px;border-radius:12px;background:rgba(255,255,255,.06);border:1px solid rgba(255,200,80,.2);color:#94a3b8;text-decoration:none;font-size:13px}}
</style>
</head>
<body>
<div class="header"><h1>{icon} {title}</h1></div>
{body}
<a class="back" href="/app">← بازگشت به خانه</a>
<div class="toast" id="toast"></div>
<script>
const tg = window.Telegram?.WebApp;
if(tg){{tg.ready();tg.expand();tg.setHeaderColor('#0a0c18');tg.setBackgroundColor('#0a0c18');}}
function toast(m){{var el=document.getElementById('toast');el.innerText=m;el.classList.add('show');setTimeout(function(){{el.classList.remove('show')}},2500)}}
{HAPTIC_JS}
{extra_js}
</script>
</body></html>"""

@app.get("/app", response_class=HTMLResponse)
async def page_home():
    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>NEXA</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Vazirmatn',sans-serif;background:linear-gradient(165deg,#0a0c18,#12182b);color:#e2e8f0;min-height:100vh;padding:16px}}
.header{{text-align:center;margin-bottom:20px}}
.header h1{{font-size:1.8rem;font-weight:800;background:linear-gradient(90deg,#fbbf24,#f59e0b);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.stats{{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin:12px 0;font-size:13px}}
.stats span{{background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.25);padding:6px 12px;border-radius:99px}}
.menu{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:20px 0}}
.menu a{{display:flex;flex-direction:column;align-items:center;padding:18px 10px;border-radius:16px;text-decoration:none;color:#f8fafc;font-weight:700;font-size:14px}}
{WEALTH_CSS}
{ICON_CSS}
.card{{background:rgba(255,255,255,.05);border-radius:16px;padding:14px;margin-bottom:12px;font-size:13px}}
.btn{{display:flex;align-items:center;justify-content:center;width:100%;padding:13px;margin-bottom:8px;border-radius:14px;font-size:14px;font-weight:700;border:none;color:#f8fafc;cursor:pointer}}
.toast{{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:rgba(15,20,35,.95);border:1px solid rgba(255,200,80,.3);color:#fbbf24;padding:12px 20px;border-radius:12px;font-size:14px;opacity:0;transition:opacity .3s;z-index:99}}
.toast.show{{opacity:1}}
</style>
</head>
<body>
<div class="header">
  <h1>☀️ NEXA</h1>
  <div class="stats">
    <span>سطح <b id="level">1</b></span>
    <span>امتیاز <b id="score">0</b></span>
    <span>استریک <b id="streak">0</b></span>
  </div>
</div>
<div class="menu">
  <a href="/app/wars"><span class="gi gi-lg">⚔️</span>جنگ‌ها</a>
  <a href="/app/groups"><span class="gi gi-lg">👥</span>گروه‌ها</a>
  <a href="/app/seasons"><span class="gi gi-lg">🏆</span>فصل‌ها</a>
  <a href="/app/economy"><span class="gi gi-lg">💰</span>اقتصاد</a>
</div>
<div class="card">
  <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>نشان</span><b id="badge">تازه‌وارد</b></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>عنوان</span><b id="title">Novice</b></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>دعوت‌ها</span><b id="invites">0</b></div>
  <div style="display:flex;justify-content:space-between"><span>دستاوردها</span><b id="achCount">0</b></div>
</div>
<button class="btn" id="btnActive"><span class="gi">✅</span>ثبت فعالیت روزانه</button>
<button class="btn" id="btnMissions"><span class="gi">🎯</span>دریافت مأموریت‌ها</button>
<button class="btn" id="btnAchieve"><span class="gi">🏅</span>بررسی دستاوردها</button>
<button class="btn" id="btnItem"><span class="gi">🎁</span>آیتم روزانه</button>
<button class="btn" id="btnRecover" style="display:none"><span class="gi">💊</span>بازیابی</button>
<div class="card" id="titleBox" style="margin-top:12px">
  <div style="margin-bottom:8px;font-size:13px;color:#94a3b8">انتخاب عنوان</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px">
    <button class="btn" data-t="Novice" style="width:auto;padding:8px 12px;margin:0;font-size:12px">Novice</button>
    <button class="btn" data-t="Hunter" style="width:auto;padding:8px 12px;margin:0;font-size:12px">Hunter</button>
    <button class="btn" data-t="Warrior" style="width:auto;padding:8px 12px;margin:0;font-size:12px">Warrior</button>
    <button class="btn" data-t="Elite" style="width:auto;padding:8px 12px;margin:0;font-size:12px">Elite</button>
    <button class="btn" data-t="Legend" style="width:auto;padding:8px 12px;margin:0;font-size:12px">Legend</button>
  </div>
</div>
<div class="card" style="margin-top:12px;font-size:12px;color:#64748b">
  لینک دعوت: <span id="invLink">—</span>
</div>
<div class="toast" id="toast"></div>
<script>
const tg=window.Telegram?.WebApp;
if(tg){{tg.ready();tg.expand();tg.setHeaderColor('#0a0c18');tg.setBackgroundColor('#0a0c18');}}
const BOT_USER="{BOT_USERNAME}";
function toast(m){{var el=document.getElementById('toast');el.innerText=m;el.classList.add('show');setTimeout(function(){{el.classList.remove('show')}},2500)}}
{HAPTIC_JS}
(function(){{
  var user=null;try{{user=tg.initDataUnsafe.user}}catch(e){{}}
  function setMissions(done){{}}
  function fill(d){{
    if(!d||!d.ok)return;
    document.getElementById('level').innerText=d.level||1;
    document.getElementById('score').innerText=d.score||0;
    document.getElementById('badge').innerText=d.badge||'تازه‌وارد';
    document.getElementById('title').innerText=d.title||'Novice';
    document.getElementById('streak').innerText=d.streak||0;
    document.getElementById('invites').innerText=d.invites||0;
    document.getElementById('achCount').innerText=(d.achievements||[]).length;
    document.getElementById('btnRecover').style.display=d.can_recover?'inline-flex':'none';
    setMissions(d.missions_done);
  }}
  if(user){{
    document.getElementById('name') && (document.getElementById('name').innerText=(user.first_name||'')+(user.last_name?(' '+user.last_name):''));
    document.getElementById('invLink').innerText='https://t.me/'+BOT_USER+'?start=inv_'+user.id;
    fetch('/api/user/sync',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:user.id,first_name:user.first_name,username:user.username}})}}).then(function(r){{return r.json()}}).then(fill);
  }}
  function post(url,extra){{
    if(!user){{toast('از تلگرام وارد شو');return}}
    fetch(url,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(Object.assign({{id:user.id}},extra||{{}}))}})
    .then(function(r){{return r.json()}}).then(function(d){{toast(d.msg||'');if(d&&d.ok)fill(d)}});
  }}
  document.getElementById('btnActive').onclick=function(){{post('/api/pro/active')}};
  document.getElementById('btnAchieve').onclick=function(){{post('/api/pro/achieve')}};
  document.getElementById('btnItem').onclick=function(){{post('/api/economy/item')}};
  document.getElementById('btnMissions').onclick=function(){{post('/api/pro/missions/claim')}};
  document.getElementById('btnRecover').onclick=function(){{post('/api/pro/recover')}};
  document.querySelectorAll('#titleBox button').forEach(function(b){{
    b.onclick=function(){{post('/api/pro/title',{{title:b.getAttribute('data-t')}})}};
  }});
}})();
</script></body></html>"""
    return HTMLResponse(html)

@app.get("/app/wars", response_class=HTMLResponse)
async def page_wars():
    body = """
<div style="background:rgba(255,255,255,.06);border-radius:16px;padding:14px;margin-bottom:12px;font-size:13px">
<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>وضعیت</span><b id="warStatus" style="color:#fbbf24">—</b></div>
<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>امتیاز</span><b id="score" style="color:#fbbf24">—</b></div>
<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>حمله/کمبو</span><b id="attacks" style="color:#fbbf24">0</b></div>
<div style="display:flex;justify-content:space-between"><span>دفاع</span><b id="defenses" style="color:#fbbf24">0</b></div>
</div>
<button class="btn" id="btnJoin"><span class="gi">🚪</span>ورود (+۱۰)</button>
<button class="btn" id="btnAttack" disabled style="opacity:.45"><span class="gi">⚔️</span>حمله (+۲۰)</button>
<button class="btn" id="btnDefend" disabled style="opacity:.45"><span class="gi">🛡️</span>دفاع (+۱۵)</button>
<button class="btn" id="btnCh" disabled style="opacity:.45"><span class="gi">🔥</span>چالش (+۲۵)</button>
<button class="btn" id="btnPower" disabled style="opacity:.45"><span class="gi">💥</span>قدرت (+۱۸)</button>
<button class="btn" id="btnHeal" disabled style="opacity:.45"><span class="gi">💚</span>شفا (+۱۲)</button>
<button class="btn" id="btnRecord"><span class="gi">📜</span>ثبت رکورد</button>
<button class="btn" id="btnLeave" disabled style="opacity:.45"><span class="gi">🚪</span>خروج</button>
<div style="margin-top:14px;font-size:12px;color:#64748b;margin-bottom:6px"><span class="gi" style="width:20px;height:20px;font-size:11px">📊</span> رتبه جنگ</div>
<div id="wrank"></div>
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function apply(d){if(!d||!d.ok)return;document.getElementById('score').innerText=d.score;document.getElementById('attacks').innerText=(d.attacks||0)+'/'+(d.combo||0);document.getElementById('defenses').innerText=d.defenses||0;
var on=!!d.in_war;document.getElementById('warStatus').innerText=on?'در جنگ':'خارج';
['btnAttack','btnDefend','btnCh','btnPower','btnHeal','btnLeave'].forEach(function(id){var b=document.getElementById(id);b.disabled=!on;b.style.opacity=on?'1':'.45'});
document.getElementById('btnJoin').disabled=on;document.getElementById('btnJoin').style.opacity=on?'.45':'1'}
function call(u){if(!uid){toast('وارد شو');return}fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)apply(d)})}
document.getElementById('btnJoin').onclick=function(){call('/api/war/join')};
document.getElementById('btnAttack').onclick=function(){call('/api/war/attack')};
document.getElementById('btnDefend').onclick=function(){call('/api/war/defend')};
document.getElementById('btnCh').onclick=function(){call('/api/war/challenge')};
document.getElementById('btnPower').onclick=function(){call('/api/war/power')};
document.getElementById('btnHeal').onclick=function(){call('/api/war/heal')};
document.getElementById('btnRecord').onclick=function(){call('/api/war/record')};
document.getElementById('btnLeave').onclick=function(){call('/api/war/leave')};
function wrank(){fetch('/api/war/leaderboard').then(function(r){return r.json()}).then(function(d){var el=document.getElementById('wrank');if(!d.ok||!d.ranks.length){el.innerHTML='';return}
el.innerHTML=d.ranks.map(function(x,i){return '<div style="display:flex;justify-content:space-between;padding:8px 10px;background:rgba(255,255,255,.05);border-radius:10px;margin-bottom:5px;font-size:13px"><span><b style="color:#fbbf24">'+(i+1)+'.</b> '+x.name+'</span><span style="color:#94a3b8">⚔'+(x.attacks||0)+' 🛡'+(x.defenses||0)+'</span></div>'}).join('')})}
if(uid)fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})}).then(function(r){return r.json()}).then(apply);
wrank();
"""
    return HTMLResponse(page_shell("⚔️", "جنگ‌ها", body, js))

@app.get("/app/groups", response_class=HTMLResponse)
async def page_groups():
    body = """
<input id="gname" maxlength="24" placeholder="نام گروه..." style="width:100%;padding:12px;border-radius:12px;border:1px solid rgba(255,200,50,.25);background:rgba(0,0,0,.3);color:#fff;margin-bottom:10px;font-family:inherit">
<button class="btn" id="btnCreate"><span class="gi">✨</span>ساخت (+۲۵)</button>
<button class="btn" id="btnHelp"><span class="gi">🤝</span>کمک گروهی (+۳۰)</button>
<button class="btn" id="btnRally"><span class="gi">📣</span>رالی گروه (+۱۵)</button>
<div id="list"></div>
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function loadList(){fetch('/api/group/list').then(function(r){return r.json()}).then(function(d){
var el=document.getElementById('list');if(!d.ok||!d.groups.length){el.innerHTML='<div style="color:#64748b;font-size:12px">گروهی نیست</div>';return}
el.innerHTML=d.groups.map(function(g){var own=uid&&g.owner===uid;
return '<div style="background:rgba(255,255,255,.06);border-radius:14px;padding:12px;margin-bottom:8px"><div style="display:flex;justify-content:space-between;align-items:center"><div><b>'+g.name+'</b><div style="font-size:11px;color:#94a3b8">'+g.members+' عضو • لول '+(g.level||1)+' • '+g.score+'</div></div><button class="btn" data-j="'+g.id+'" style="width:auto;padding:8px 12px;margin:0;font-size:12px"><span class="gi" style="width:18px;height:18px;font-size:10px">➕</span>عضویت</button></div><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px"><button class="btn" data-d="'+g.id+'" style="flex:1;padding:8px;margin:0;font-size:12px">💎 اهدا</button><button class="btn" data-r="'+g.id+'" style="flex:1;padding:8px;margin:0;font-size:12px">📣 رالی</button>'+(own?'<button class="btn" data-u="'+g.id+'" style="flex:1;padding:8px;margin:0;font-size:12px">⬆️ ارتقا</button>':'<button class="btn" data-l="'+g.id+'" style="flex:1;padding:8px;margin:0;font-size:12px">🚪 خروج</button>')+'</div></div>'}).join('');
el.querySelectorAll('[data-j]').forEach(function(b){b.onclick=function(){fetch('/api/group/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,group_id:b.getAttribute('data-j')})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)loadList()})}});
el.querySelectorAll('[data-u]').forEach(function(b){b.onclick=function(){fetch('/api/group/upgrade',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,group_id:b.getAttribute('data-u')})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)loadList()})}});
el.querySelectorAll('[data-d]').forEach(function(b){b.onclick=function(){fetch('/api/group/donate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,group_id:b.getAttribute('data-d'),amount:10})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)loadList()})}});
el.querySelectorAll('[data-r]').forEach(function(b){b.onclick=function(){fetch('/api/group/rally',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,group_id:b.getAttribute('data-r')})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)loadList()})}});
el.querySelectorAll('[data-l]').forEach(function(b){b.onclick=function(){fetch('/api/group/leave',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,group_id:b.getAttribute('data-l')})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)loadList()})}});
})}
document.getElementById('btnCreate').onclick=function(){if(!uid){toast('وارد شو');return}var n=document.getElementById('gname').value.trim();if(n.length<2){toast('نام کوتاه');return}fetch('/api/group/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,name:n})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok){document.getElementById('gname').value='';loadList()}})};
document.getElementById('btnHelp').onclick=function(){if(!uid){toast('وارد شو');return}fetch('/api/group/help',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'')})};
document.getElementById('btnRally').onclick=function(){if(!uid){toast('وارد شو');return}fetch('/api/group/rally',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)loadList()})};
loadList();
"""
    return HTMLResponse(page_shell("👥", "گروه‌ها", body, js))

@app.get("/app/seasons", response_class=HTMLResponse)
async def page_seasons():
    body = """
<div style="background:rgba(255,255,255,.06);border-radius:16px;padding:14px;margin-bottom:12px;font-size:13px">
<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>فصل فعال</span><b style="color:#fbbf24">فصل ۱</b></div>
<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>امتیاز فصل</span><b id="sp" style="color:#fbbf24">0</b></div>
<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>پیشرفت</span><b id="prog" style="color:#fbbf24">0%</b></div>
<div class="bar"><i id="pbar"></i></div>
<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>توکن</span><b id="tp" style="color:#fbbf24">0</b></div>
<div style="display:flex;justify-content:space-between"><span>کل</span><b id="score" style="color:#fbbf24">—</b></div>
</div>
<button class="btn" id="btnMission"><span class="gi">🎯</span>مأموریت (+۴۰)</button>
<button class="btn" id="btnChest"><span class="gi">📦</span>صندوق (+۶۰)</button>
<button class="btn" id="btnRank"><span class="gi">🥇</span>پاداش Top10 (+۸۰)</button>
<button class="btn" id="btnToken"><span class="gi">🪙</span>توکن (+۴۰)</button>
<div id="ranks" style="margin-top:12px"></div>
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function fill(d){if(!d||!d.ok)return;document.getElementById('score').innerText=d.score;document.getElementById('sp').innerText=d.season_points||0;document.getElementById('tp').innerText=d.token_points||0;
var p=d.season_progress||0;document.getElementById('prog').innerText=p+'%';document.getElementById('pbar').style.width=p+'%'}
function call(u){if(!uid){toast('وارد شو');return}fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok){fill(d);ranks()}})}
document.getElementById('btnMission').onclick=function(){call('/api/season/mission')};
document.getElementById('btnChest').onclick=function(){call('/api/season/chest')};
document.getElementById('btnRank').onclick=function(){call('/api/season/rank_reward')};
document.getElementById('btnToken').onclick=function(){call('/api/future/token')};
function ranks(){fetch('/api/rank/top').then(function(r){return r.json()}).then(function(d){var el=document.getElementById('ranks');if(!d.ok||!d.ranks.length){el.innerHTML='';return}el.innerHTML=d.ranks.map(function(x,i){return '<div style="display:flex;justify-content:space-between;padding:8px 10px;background:rgba(255,255,255,.05);border-radius:10px;margin-bottom:5px;font-size:13px"><span><b style="color:#fbbf24">'+(i+1)+'.</b> '+x.name+'</span><span style="color:#94a3b8">'+x.score+'</span></div>'}).join('')})}
if(uid)fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})}).then(function(r){return r.json()}).then(fill);
ranks();
"""
    return HTMLResponse(page_shell("🏆", "فصل‌ها", body, js))

@app.get("/app/economy", response_class=HTMLResponse)
async def page_economy():
    body = """
<div style="background:rgba(255,255,255,.06);border-radius:16px;padding:14px;margin-bottom:12px;font-size:13px">
<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>Boost</span><b id="boosts" style="color:#fbbf24">0</b></div>
<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>جعبه</span><b id="boxes" style="color:#fbbf24">0</b></div>
<div style="display:flex;justify-content:space-between"><span>امتیاز</span><b id="score" style="color:#fbbf24">—</b></div>
</div>
<button class="btn" id="btnBoost"><span class="gi">🚀</span>Boost (+۳۰)</button>
<button class="btn" id="btnPass"><span class="gi">🎫</span>Season Pass (+۱۰۰)</button>
<button class="btn" id="btnBox"><span class="gi">🎲</span>Mystery Box</button>
<button class="btn" id="btnItem"><span class="gi">🎁</span>آیتم روزانه</button>
<button class="btn" id="buy1"><span class="gi">🟡</span>نشان طلا (۴۰)</button>
<button class="btn" id="buy2"><span class="gi">🔥</span>نشان آتش (۶۰)</button>
<button class="btn" id="buy3"><span class="gi">👑</span>نشان تاج (۱۰۰)</button>
<div id="inv" style="margin-top:10px;font-size:12px;color:#94a3b8"></div>
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function fill(d){if(!d||!d.ok)return;document.getElementById('score').innerText=d.score;document.getElementById('boosts').innerText=d.boosts||0;document.getElementById('boxes').innerText=d.boxes||0;
var inv=d.inventory||[];document.getElementById('inv').innerText=inv.length?('موجودی: '+inv.map(function(x){return x.name||x.item}).join(', ')):''}
function call(u,extra){if(!uid){toast('وارد شو');return}fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({id:uid},extra||{}))}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)fill(d)})}
document.getElementById('btnBoost').onclick=function(){call('/api/economy/boost')};
document.getElementById('btnPass').onclick=function(){call('/api/economy/pass')};
document.getElementById('btnBox').onclick=function(){call('/api/economy/box')};
document.getElementById('btnItem').onclick=function(){call('/api/economy/item')};
document.getElementById('buy1').onclick=function(){call('/api/shop/buy',{item_id:'badge_gold'})};
document.getElementById('buy2').onclick=function(){call('/api/shop/buy',{item_id:'badge_fire'})};
document.getElementById('buy3').onclick=function(){call('/api/shop/buy',{item_id:'badge_crown'})};
if(uid)fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})}).then(function(r){return r.json()}).then(fill);
"""
    return HTMLResponse(page_shell("💰", "اقتصاد", body, js))

@app.on_event("startup")
async def on_startup():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(WEBHOOK_URL)
        logger.info("NEXA up | %s", WEBHOOK_URL)
    except Exception as e:
        logger.error("Webhook setup failed: %s", e)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
