# ============================================================
# NEXA — main.py
# ارتقا: Daily-Missions | War-Leaderboard | Group-Leave | Season-Progress
# ============================================================

import os
import json
import logging
import random
from datetime import datetime, date
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
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
USE_TELEGRAM_PHOTO = False

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("nexa")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ------------------------------------------------------------
# STORAGE
# ------------------------------------------------------------
def _load(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("load %s", path)
        return default


def _save(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_users() -> Dict[str, dict]:
    return _load(USERS_FILE, {})


def save_users(data: Dict[str, dict]) -> None:
    _save(USERS_FILE, data)


def load_groups() -> Dict[str, dict]:
    return _load(GROUPS_FILE, {})


def save_groups(data: Dict[str, dict]) -> None:
    _save(GROUPS_FILE, data)


# ------------------------------------------------------------
# DOMAIN
# ------------------------------------------------------------
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
}

ALLOWED_TITLES = {"Novice", "Hunter", "Warrior", "Elite", "Legend"}
SHOP_ITEMS = {
    "badge_gold": {"name": "نشان طلا", "cost": 40, "bonus": 5},
    "badge_fire": {"name": "نشان آتش", "cost": 60, "bonus": 10},
    "badge_crown": {"name": "نشان تاج", "cost": 100, "bonus": 20},
}
# مأموریت‌های روزانه ساده (پلن رقابت/هویت)
DAILY_MISSIONS = [
    {"id": "m_active", "title": "ثبت فعالیت", "need": "active", "reward": 15},
    {"id": "m_attack", "title": "۱ حمله در جنگ", "need": "attack", "reward": 20},
    {"id": "m_social", "title": "کمک یا رالی گروه", "need": "social", "reward": 20},
]


def badge_for_level(level: int) -> str:
    if level >= 10:
        return "افسانه‌ای"
    if level >= 5:
        return "حرفه‌ای"
    if level >= 3:
        return "مبارز"
    return "تازه‌وارد"


def recalc_level(score: int) -> int:
    return max(1, int(score) // 100 + 1)


def apply_score(uid: str, delta: int, users: dict) -> dict:
    u = users[uid]
    u["score"] = max(0, int(u.get("score", 0)) + int(delta))
    u["level"] = recalc_level(u["score"])
    u["badge"] = badge_for_level(u["level"])
    return u


def today() -> str:
    return date.today().isoformat()


def days_since(iso_day: Optional[str]) -> int:
    if not iso_day:
        return 999
    try:
        return (date.today() - date.fromisoformat(iso_day[:10])).days
    except Exception:
        return 999


def get_or_create_pro(user_id: int, first_name: str = "", username: Optional[str] = None) -> dict:
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
    if first_name:
        u["first_name"] = first_name
    if username is not None:
        u["username"] = username
    for k, v in USER_DEFAULTS.items():
        if k not in u:
            u[k] = list(v) if isinstance(v, list) else v
    save_users(users)
    return u


def public_user(u: dict) -> dict:
    inactive = days_since(u.get("last_active_day") or u.get("last_seen"))
    sp = int(u.get("season_points") or 0)
    return {
        "ok": True,
        "level": u.get("level", 1),
        "score": u.get("score", 0),
        "badge": u.get("badge") or badge_for_level(u.get("level", 1)),
        "title": u.get("title") or "Novice",
        "wars_joined": u.get("wars_joined", 0),
        "attacks": u.get("attacks", 0),
        "defenses": u.get("defenses", 0),
        "in_war": bool(u.get("in_war")),
        "groups": u.get("groups") or [],
        "boosts": u.get("boosts", 0),
        "boxes": u.get("boxes", 0),
        "season_points": sp,
        "season_progress": min(100, int(sp / 3)),  # هر ~300 امتیاز فصل = 100%
        "token_points": u.get("token_points", 0),
        "invites": u.get("invites", 0),
        "achievements": u.get("achievements") or [],
        "inventory": u.get("inventory") or [],
        "combo": u.get("combo", 0),
        "streak": u.get("streak", 0),
        "heals": u.get("heals", 0),
        "shop_buys": u.get("shop_buys", 0),
        "rallies": u.get("rallies", 0),
        "war_records": u.get("war_records", 0),
        "missions_done": u.get("missions_done") or [],
        "inactive_days": inactive,
        "can_recover": inactive >= 2 and u.get("last_recover_day") != today(),
    }


def require_user(body: dict) -> Tuple[Optional[Tuple[dict, str]], Optional[JSONResponse]]:
    user_id = body.get("id")
    if not user_id:
        return None, JSONResponse({"ok": False, "msg": "no user"}, status_code=400)
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        get_or_create_pro(int(user_id))
        users = load_users()
    return (users, uid), None


def unlock_achievement(uid: str, users: dict, code: str, bonus: int = 15) -> Optional[str]:
    ach = users[uid].setdefault("achievements", [])
    if code in ach:
        return None
    ach.append(code)
    apply_score(uid, bonus, users)
    return f"دستاورد {code} +{bonus}"


def reset_missions_if_needed(u: dict) -> None:
    if u.get("last_daily_missions") != today():
        u["missions_done"] = []
        u["last_daily_missions"] = today()


# ------------------------------------------------------------
# BOT
# ------------------------------------------------------------
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
            unlock_achievement(inv_uid, users, "INVITER", 20)
            save_users(users)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☀️ ورود به NEXA", web_app=WebAppInfo(url=MINIAPP_URL))]
    ])
    await message.answer("به NEXA خوش آمدید ☀️\n\nقدرتت را بیدار کن.\nآینده از آنِ توست.", reply_markup=kb)


# ------------------------------------------------------------
# APP
# ------------------------------------------------------------
app = FastAPI(title="NEXA")
app.mount("/static", StaticFiles(directory="static"), name="static")


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


# ------------------------------------------------------------
# API PRO
# ------------------------------------------------------------
@app.post("/api/user/sync")
async def api_user_sync(request: Request):
    try:
        body = await request.json()
        if not body.get("id"):
            return JSONResponse({"ok": False}, status_code=400)
        pro = get_or_create_pro(int(body["id"]), body.get("first_name") or "", body.get("username"))
        return public_user(pro)
    except Exception as e:
        logger.exception("sync")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/pro/active")
async def api_pro_active(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
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
        # مأموریت active
        done = u.setdefault("missions_done", [])
        if "m_active" not in done:
            done.append("m_active")
            apply_score(uid, 15, users)
            bonus += 15
        extra = unlock_achievement(uid, users, "DAILY", 10)
        save_users(users)
        msg = f"فعالیت! +{bonus} (استریک {u.get('streak', 1)})"
        if extra:
            msg += " | " + extra
        return {**public_user(users[uid]), "msg": msg}
    except Exception as e:
        logger.exception("active")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/pro/recover")
async def api_pro_recover(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        u = users[uid]
        inactive = days_since(u.get("last_active_day") or u.get("last_seen"))
        if inactive < 2:
            return {"ok": False, "msg": "هنوز نیاز به بازیابی نیست"}
        if u.get("last_recover_day") == today():
            return {"ok": False, "msg": "امروز بازیابی کردی"}
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
        if title not in ALLOWED_TITLES:
            return {"ok": False, "msg": "عنوان مجاز نیست"}
        ctx, err = require_user(body)
        if err:
            return err
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
        if err:
            return err
        users, uid = ctx
        u = users[uid]
        gained = []
        for ok, code, bonus in [
            (u.get("attacks", 0) >= 5, "ATK5", 25),
            (u.get("defenses", 0) >= 5, "DEF5", 25),
            (u.get("score", 0) >= 200, "SC200", 30),
            (bool(u.get("groups")), "GROUPED", 20),
            (u.get("streak", 0) >= 3, "STREAK3", 30),
            (u.get("shop_buys", 0) >= 1, "SHOPPER", 15),
            (u.get("invites", 0) >= 1, "INVITER", 20),
            (u.get("rallies", 0) >= 1, "RALLY", 15),
            (u.get("war_records", 0) >= 1, "RECORD", 20),
            (len(u.get("missions_done") or []) >= 3, "MISSIONS3", 25),
        ]:
            if ok:
                m = unlock_achievement(uid, users, code, bonus)
                if m:
                    gained.append(m)
        save_users(users)
        return {**public_user(users[uid]), "msg": " | ".join(gained) if gained else "دستاورد جدیدی نیست"}
    except Exception as e:
        logger.exception("achieve")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.get("/api/pro/missions")
async def api_pro_missions_list(request: Request):
    """وضعیت مأموریت‌های روزانه"""
    uid = request.query_params.get("id")
    if not uid:
        return {"ok": False, "missions": DAILY_MISSIONS}
    users = load_users()
    if uid not in users:
        return {"ok": True, "missions": DAILY_MISSIONS, "done": []}
    u = users[uid]
    reset_missions_if_needed(u)
    save_users(users)
    return {"ok": True, "missions": DAILY_MISSIONS, "done": u.get("missions_done") or []}


@app.post("/api/pro/missions/claim")
async def api_pro_missions_claim(request: Request):
    """جمع‌آوری پاداش مأموریت‌های کامل‌شده (اگر هر ۳ تا باشد بونوس)"""
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        u = users[uid]
        reset_missions_if_needed(u)
        done = u.get("missions_done") or []
        if len(done) < 3:
            return {"ok": False, "msg": f"هنوز {3-len(done)} مأموریت مانده", "done": done}
        if "CLAIM3" in (u.get("achievements") or []) and u.get("last_mission_claim") == today():
            return {"ok": False, "msg": "پاداش سه‌تایی امروز گرفته شده"}
        u["last_mission_claim"] = today()
        apply_score(uid, 40, users)
        unlock_achievement(uid, users, "MISSIONS3", 25)
        save_users(users)
        return {**public_user(users[uid]), "msg": "هر ۳ مأموریت کامل! +۴۰"}
    except Exception as e:
        logger.exception("missions.claim")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


# ------------------------------------------------------------
# API WAR
# ------------------------------------------------------------
@app.post("/api/war/join")
async def api_war_join(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if users[uid].get("in_war"):
            return {**public_user(users[uid]), "msg": "قبلاً در جنگ هستی"}
        users[uid]["in_war"] = True
        users[uid]["wars_joined"] = users[uid].get("wars_joined", 0) + 1
        users[uid]["combo"] = 0
        apply_score(uid, 10, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "وارد جنگ شدی! +۱۰"}
    except Exception as e:
        logger.exception("war.join")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/war/attack")
async def api_war_attack(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        u = users[uid]
        if not u.get("in_war"):
            return {"ok": False, "msg": "اول وارد جنگ شو"}
        reset_missions_if_needed(u)
        u["attacks"] = u.get("attacks", 0) + 1
        u["combo"] = u.get("combo", 0) + 1
        apply_score(uid, 20, users)
        extra = ""
        if u["combo"] >= 3 and u.get("last_combo_day") != today():
            u["last_combo_day"] = today()
            u["combo"] = 0
            apply_score(uid, 35, users)
            extra = " | کمبو ×۳ +۳۵"
        done = u.setdefault("missions_done", [])
        if "m_attack" not in done:
            done.append("m_attack")
            apply_score(uid, 20, users)
            extra += " | مأموریت حمله +۲۰"
        save_users(users)
        return {**public_user(users[uid]), "msg": "حمله! +۲۰" + extra}
    except Exception as e:
        logger.exception("war.attack")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/war/defend")
async def api_war_defend(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if not users[uid].get("in_war"):
            return {"ok": False, "msg": "اول وارد جنگ شو"}
        users[uid]["defenses"] = users[uid].get("defenses", 0) + 1
        users[uid]["combo"] = 0
        apply_score(uid, 15, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "دفاع! +۱۵"}
    except Exception as e:
        logger.exception("war.defend")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/war/challenge")
async def api_war_challenge(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if not users[uid].get("in_war"):
            return {"ok": False, "msg": "اول وارد جنگ شو"}
        if users[uid].get("last_challenge_day") == today():
            return {"ok": False, "msg": "چالش امروز انجام شده"}
        users[uid]["last_challenge_day"] = today()
        apply_score(uid, 25, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "چالش! +۲۵"}
    except Exception as e:
        logger.exception("war.challenge")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/war/power")
async def api_war_power(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if not users[uid].get("in_war"):
            return {"ok": False, "msg": "اول وارد جنگ شو"}
        if users[uid].get("last_power_day") == today():
            return {"ok": False, "msg": "قدرت امروز استفاده شده"}
        users[uid]["last_power_day"] = today()
        apply_score(uid, 18, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "قدرت جنگ! +۱۸"}
    except Exception as e:
        logger.exception("war.power")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/war/heal")
async def api_war_heal(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if not users[uid].get("in_war"):
            return {"ok": False, "msg": "اول وارد جنگ شو"}
        if users[uid].get("last_heal_day") == today():
            return {"ok": False, "msg": "شفا امروز استفاده شده"}
        users[uid]["last_heal_day"] = today()
        users[uid]["heals"] = users[uid].get("heals", 0) + 1
        apply_score(uid, 12, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "شفا! +۱۲"}
    except Exception as e:
        logger.exception("war.heal")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/war/record")
async def api_war_record(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        u = users[uid]
        if u.get("last_record_day") == today():
            return {"ok": False, "msg": "رکورد امروز ثبت شده"}
        total = u.get("attacks", 0) + u.get("defenses", 0)
        if total < 5:
            return {"ok": False, "msg": f"حداقل ۵ عملیات (الان {total})"}
        reward = 20 + min(total, 30)
        u["last_record_day"] = today()
        u["war_records"] = u.get("war_records", 0) + 1
        apply_score(uid, reward, users)
        unlock_achievement(uid, users, "RECORD", 20)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"رکورد جنگ! +{reward}"}
    except Exception as e:
        logger.exception("war.record")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/war/leave")
async def api_war_leave(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if not users[uid].get("in_war"):
            return {"ok": False, "msg": "داخل جنگ نیستی"}
        users[uid]["in_war"] = False
        users[uid]["combo"] = 0
        save_users(users)
        return {**public_user(users[uid]), "msg": "خارج شدی"}
    except Exception as e:
        logger.exception("war.leave")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.get("/api/war/leaderboard")
async def api_war_leaderboard():
    users = load_users()
    rows = [
        {
            "name": u.get("first_name") or u.get("username") or "بازیکن",
            "attacks": u.get("attacks", 0),
            "defenses": u.get("defenses", 0),
            "score": u.get("score", 0),
        }
        for u in users.values()
    ]
    rows.sort(key=lambda x: (x["attacks"] + x["defenses"], x["score"]), reverse=True)
    return {"ok": True, "ranks": rows[:15]}


# ------------------------------------------------------------
# API GROUP
# ------------------------------------------------------------
@app.post("/api/group/create")
async def api_group_create(request: Request):
    try:
        body = await request.json()
        name = (body.get("name") or "").strip()
        if len(name) < 2:
            return {"ok": False, "msg": "نام کوتاه است"}
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        groups = load_groups()
        for g in groups.values():
            if g.get("name", "").lower() == name.lower():
                return {"ok": False, "msg": "نام تکراری"}
        gid = f"g{int(datetime.now().timestamp())}"
        groups[gid] = {
            "id": gid, "name": name, "owner": int(body["id"]),
            "members": [int(body["id"])], "score": 0, "level": 1,
            "created_at": datetime.now().isoformat(),
        }
        save_groups(groups)
        users[uid].setdefault("groups", []).append(gid)
        apply_score(uid, 25, users)
        unlock_achievement(uid, users, "FOUNDER", 20)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"گروه «{name}» +۲۵"}
    except Exception as e:
        logger.exception("group.create")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/group/join")
async def api_group_join(request: Request):
    try:
        body = await request.json()
        group_id = body.get("group_id")
        if not group_id:
            return {"ok": False, "msg": "group_id لازم است"}
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        groups = load_groups()
        if group_id not in groups:
            return {"ok": False, "msg": "گروه نیست"}
        g = groups[group_id]
        mid = int(body["id"])
        if mid in g.get("members", []):
            return {"ok": False, "msg": "قبلاً عضو هستی"}
        g.setdefault("members", []).append(mid)
        save_groups(groups)
        if group_id not in users[uid].get("groups", []):
            users[uid].setdefault("groups", []).append(group_id)
        apply_score(uid, 15, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"عضو «{g['name']}» +۱۵"}
    except Exception as e:
        logger.exception("group.join")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/group/leave")
async def api_group_leave(request: Request):
    try:
        body = await request.json()
        group_id = body.get("group_id")
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        groups = load_groups()
        if group_id not in groups:
            return {"ok": False, "msg": "گروه نیست"}
        g = groups[group_id]
        mid = int(body["id"])
        if mid == g.get("owner"):
            return {"ok": False, "msg": "سازنده نمی‌تواند خارج شود"}
        if mid not in g.get("members", []):
            return {"ok": False, "msg": "عضو نیستی"}
        g["members"] = [m for m in g["members"] if m != mid]
        save_groups(groups)
        users[uid]["groups"] = [x for x in (users[uid].get("groups") or []) if x != group_id]
        save_users(users)
        return {**public_user(users[uid]), "msg": f"از «{g['name']}» خارج شدی"}
    except Exception as e:
        logger.exception("group.leave")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/group/upgrade")
async def api_group_upgrade(request: Request):
    try:
        body = await request.json()
        group_id = body.get("group_id")
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        groups = load_groups()
        if group_id not in groups:
            return {"ok": False, "msg": "گروه نیست"}
        g = groups[group_id]
        if int(body["id"]) != g.get("owner"):
            return {"ok": False, "msg": "فقط سازنده"}
        if users[uid].get("score", 0) < 20:
            return {"ok": False, "msg": "حداقل ۲۰ امتیاز"}
        apply_score(uid, -20, users)
        g["level"] = g.get("level", 1) + 1
        g["score"] = g.get("score", 0) + 30
        save_groups(groups)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"سطح گروه {g['level']}"}
    except Exception as e:
        logger.exception("group.upgrade")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/group/help")
async def api_group_help(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        u = users[uid]
        if not u.get("groups"):
            return {"ok": False, "msg": "اول عضو گروه شو"}
        reset_missions_if_needed(u)
        apply_score(uid, 30, users)
        done = u.setdefault("missions_done", [])
        extra = ""
        if "m_social" not in done:
            done.append("m_social")
            apply_score(uid, 20, users)
            extra = " | مأموریت اجتماعی +۲۰"
        save_users(users)
        return {**public_user(users[uid]), "msg": "کمک گروهی! +۳۰" + extra}
    except Exception as e:
        logger.exception("group.help")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/group/donate")
async def api_group_donate(request: Request):
    try:
        body = await request.json()
        group_id = body.get("group_id")
        amount = max(5, min(int(body.get("amount") or 10), 50))
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        groups = load_groups()
        if group_id not in groups:
            return {"ok": False, "msg": "گروه نیست"}
        if group_id not in (users[uid].get("groups") or []):
            return {"ok": False, "msg": "عضو نیستی"}
        if users[uid].get("score", 0) < amount:
            return {"ok": False, "msg": "امتیاز کافی نیست"}
        apply_score(uid, -amount, users)
        groups[group_id]["score"] = groups[group_id].get("score", 0) + amount
        save_groups(groups)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"اهدا {amount}"}
    except Exception as e:
        logger.exception("group.donate")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/group/rally")
async def api_group_rally(request: Request):
    try:
        body = await request.json()
        group_id = body.get("group_id")
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        u = users[uid]
        groups = load_groups()
        if not group_id:
            gs = u.get("groups") or []
            if not gs:
                return {"ok": False, "msg": "اول عضو گروه شو"}
            group_id = gs[0]
        if group_id not in groups:
            return {"ok": False, "msg": "گروه نیست"}
        if group_id not in (u.get("groups") or []):
            return {"ok": False, "msg": "عضو نیستی"}
        if u.get("last_rally_day") == today():
            return {"ok": False, "msg": "رالی امروز انجام شده"}
        reset_missions_if_needed(u)
        u["last_rally_day"] = today()
        u["rallies"] = u.get("rallies", 0) + 1
        groups[group_id]["score"] = groups[group_id].get("score", 0) + 25
        apply_score(uid, 15, users)
        extra = ""
        done = u.setdefault("missions_done", [])
        if "m_social" not in done:
            done.append("m_social")
            apply_score(uid, 20, users)
            extra = " | مأموریت اجتماعی +۲۰"
        unlock_achievement(uid, users, "RALLY", 15)
        save_groups(groups)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"رالی «{groups[group_id]['name']}»! +۱۵" + extra}
    except Exception as e:
        logger.exception("group.rally")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.get("/api/group/list")
async def api_group_list():
    groups = load_groups()
    items = [{
        "id": g["id"], "name": g["name"], "members": len(g.get("members") or []),
        "score": g.get("score", 0), "level": g.get("level", 1), "owner": g.get("owner"),
    } for g in groups.values()]
    items.sort(key=lambda x: x["score"], reverse=True)
    return {"ok": True, "groups": items[:30]}


# ------------------------------------------------------------
# API ECONOMY / SEASON
# ------------------------------------------------------------
@app.post("/api/economy/boost")
async def api_economy_boost(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if users[uid].get("last_boost_day") == today():
            return {"ok": False, "msg": "امروز Boost گرفتی"}
        users[uid]["last_boost_day"] = today()
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
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if users[uid].get("last_box_day") == today():
            return {"ok": False, "msg": "جعبه امروز باز شده"}
        prize = random.randint(20, 80)
        users[uid]["last_box_day"] = today()
        users[uid]["boxes"] = users[uid].get("boxes", 0) + 1
        apply_score(uid, prize, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"Mystery Box! +{prize}"}
    except Exception as e:
        logger.exception("box")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/economy/pass")
async def api_economy_pass(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if users[uid].get("last_pass_day") == today():
            return {"ok": False, "msg": "امروز Pass گرفتی"}
        users[uid]["last_pass_day"] = today()
        apply_score(uid, 100, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "Season Pass! +۱۰۰"}
    except Exception as e:
        logger.exception("pass")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/economy/item")
async def api_economy_item(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if users[uid].get("last_item_day") == today():
            return {"ok": False, "msg": "آیتم امروز گرفته شده"}
        item = random.choice(["Shield", "Blade", "Crystal", "Scroll"])
        users[uid]["last_item_day"] = today()
        users[uid].setdefault("inventory", []).append({"item": item, "at": datetime.now().isoformat()})
        apply_score(uid, 12, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"آیتم {item} +۱۲"}
    except Exception as e:
        logger.exception("item")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/shop/buy")
async def api_shop_buy(request: Request):
    try:
        body = await request.json()
        item_id = body.get("item_id")
        if item_id not in SHOP_ITEMS:
            return {"ok": False, "msg": "آیتم نامعتبر"}
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        item = SHOP_ITEMS[item_id]
        if users[uid].get("score", 0) < item["cost"]:
            return {"ok": False, "msg": f"حداقل {item['cost']} امتیاز"}
        inv = users[uid].setdefault("inventory", [])
        if any(x.get("item") == item_id for x in inv):
            return {"ok": False, "msg": "قبلاً خریدی"}
        apply_score(uid, -item["cost"], users)
        apply_score(uid, item["bonus"], users)
        inv.append({"item": item_id, "name": item["name"], "at": datetime.now().isoformat()})
        users[uid]["shop_buys"] = users[uid].get("shop_buys", 0) + 1
        save_users(users)
        return {**public_user(users[uid]), "msg": f"خرید {item['name']}!"}
    except Exception as e:
        logger.exception("shop.buy")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/season/mission")
async def api_season_mission(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if users[uid].get("last_mission_day") == today():
            return {"ok": False, "msg": "مأموریت امروز انجام شده"}
        users[uid]["last_mission_day"] = today()
        users[uid]["season_points"] = users[uid].get("season_points", 0) + 40
        apply_score(uid, 40, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "مأموریت فصل! +۴۰"}
    except Exception as e:
        logger.exception("mission")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/season/chest")
async def api_season_chest(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if users[uid].get("last_chest_day") == today():
            return {"ok": False, "msg": "صندوق امروز باز شده"}
        users[uid]["last_chest_day"] = today()
        users[uid]["season_points"] = users[uid].get("season_points", 0) + 60
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
        if err:
            return err
        users, uid = ctx
        if users[uid].get("last_rank_reward_day") == today():
            return {"ok": False, "msg": "پاداش رتبه امروز گرفته شده"}
        ranking = sorted(users.values(), key=lambda x: x.get("score", 0), reverse=True)
        top_ids = [str(u.get("user_id")) for u in ranking[:10]]
        if uid not in top_ids:
            return {"ok": False, "msg": "باید Top10 باشی"}
        users[uid]["last_rank_reward_day"] = today()
        apply_score(uid, 80, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"پاداش رتبه #{top_ids.index(uid)+1}! +۸۰"}
    except Exception as e:
        logger.exception("rank_reward")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/future/token")
async def api_future_token(request: Request):
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if users[uid].get("last_token_day") == today():
            return {"ok": False, "msg": "توکن امروز انجام شده"}
        users[uid]["last_token_day"] = today()
        users[uid]["token_points"] = users[uid].get("token_points", 0) + 40
        apply_score(uid, 40, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "مأموریت توکن! +۴۰"}
    except Exception as e:
        logger.exception("token")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.get("/api/rank/top")
async def api_rank_top():
    users = load_users()
    rows = [{
        "name": u.get("first_name") or u.get("username") or "بازیکن",
        "score": u.get("score", 0), "level": u.get("level", 1),
    } for u in users.values()]
    rows.sort(key=lambda x: x["score"], reverse=True)
    return {"ok": True, "ranks": rows[:20]}


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
BRAND_CSS = """
.brand-bar{display:flex;align-items:center;gap:10px}
.brand-logo{width:36px;height:36px;border-radius:50%;flex-shrink:0;box-shadow:0 0 0 2px rgba(255,215,0,.45);
background:radial-gradient(circle at 35% 30%,#ffe566,#f5a623 60%,#c77d00);display:flex;align-items:center;justify-content:center;font-size:18px}
.brand-name{font-size:18px;font-weight:800;letter-spacing:3px;background:linear-gradient(90deg,#ffe566,#ffb800);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
"""
BRAND_HTML = """<div class="brand-bar"><div class="brand-logo">☀️</div><div class="brand-name">NEXA</div></div>"""


def page_shell(icon: str, title: str, body: str, js: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>NEXA - {title}</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Vazirmatn',sans-serif}}
body{{min-height:100vh;color:#fff;background:#05051a}}
.wrap{{padding:14px 14px 40px;background:linear-gradient(180deg,#0a0a2e,#05051a)}}
.top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;gap:10px}}
.top-right{{display:flex;align-items:center;gap:10px}}
.back{{width:40px;height:40px;border-radius:12px;background:rgba(255,255,255,.08);border:1px solid rgba(255,200,50,.25);display:flex;align-items:center;justify-content:center;color:#fbbf24;text-decoration:none;font-size:17px}}
.page-title{{font-size:15px;font-weight:700}}
{BRAND_CSS}
.btn{{display:block;width:100%;border:none;border-radius:14px;padding:14px;font-size:15px;font-weight:700;margin-bottom:10px;cursor:pointer;font-family:inherit}}
.toast{{position:fixed;bottom:24px;left:16px;right:16px;background:rgba(15,15,40,.95);border:1px solid rgba(251,191,36,.4);border-radius:14px;padding:12px;text-align:center;font-size:13px;font-weight:600;color:#fbbf24;display:none;z-index:50}}
.footer{{text-align:center;margin-top:20px;font-size:11px;color:#475569}}.footer strong{{color:#fbbf24}}
.bar{{height:8px;background:rgba(255,255,255,.1);border-radius:8px;overflow:hidden;margin:8px 0 12px}}
.bar>i{{display:block;height:100%;background:linear-gradient(90deg,#f59e0b,#fbbf24);width:0}}
</style></head><body>
<div class="wrap">
<div class="top"><div class="top-right"><a class="back" href="/app">→</a>{BRAND_HTML}</div>
<div class="page-title">{icon} {title}</div></div>
{body}
<div class="footer"><strong>NEXA</strong></div>
</div>
<script>
var tg=window.Telegram.WebApp;try{{tg.ready();tg.expand()}}catch(e){{}}
function toast(m){{var t=document.getElementById('toast');if(!t)return;t.innerText=m;t.style.display='block';setTimeout(function(){{t.style.display='none'}},2000)}}
{js}
</script></body></html>"""


@app.get("/app", response_class=HTMLResponse)
async def mini_app():
    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>NEXA</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Vazirmatn',sans-serif;-webkit-tap-highlight-color:transparent}}
body{{min-height:100vh;background:#05051a;color:#fff;overflow-x:hidden}}
#splash{{position:fixed;inset:0;z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;
background:#05051a url('/static/nexa-logo.jpg') center/cover no-repeat;padding-bottom:18%;transition:opacity .35s,visibility .35s}}
#splash.hide{{opacity:0;visibility:hidden;pointer-events:none}}
.splash-slogan{{font-size:15px;color:rgba(255,255,255,.8);font-weight:600;text-align:center;padding:0 28px;margin-bottom:18px;text-shadow:0 2px 14px rgba(0,0,0,.55)}}
.loader{{width:56px;height:4px;background:rgba(255,255,255,.22);border-radius:4px;overflow:hidden;margin-bottom:8px}}
.loader-bar{{height:100%;width:0;background:linear-gradient(90deg,#ff8c00,#ffd700)}}
#main{{display:none;padding:14px 14px 36px;background:linear-gradient(180deg,#0a0a2e,#05051a)}}
#main.show{{display:block}}
.top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}}
{BRAND_CSS}
.chip{{font-size:11px;background:rgba(251,191,36,.15);color:#fbbf24;padding:5px 11px;border-radius:20px;font-weight:600}}
.profile{{background:rgba(255,255,255,.07);border:1px solid rgba(255,200,50,.16);border-radius:18px;padding:14px;display:flex;align-items:center;gap:12px;margin-bottom:10px}}
.avatar{{width:58px;height:58px;border-radius:50%;border:2px solid #fbbf24;flex-shrink:0;background:radial-gradient(circle at 32% 28%,#fff3a0,#ffd700 35%,#f5a623 70%,#c77d00);display:flex;align-items:center;justify-content:center;box-shadow:0 0 16px rgba(245,166,35,.45)}}
.avatar span{{font-size:30px;line-height:1}}
.meta{{flex:1;min-width:0}}.name{{font-weight:700;font-size:15px}}.user{{font-size:12px;color:#94a3b8;margin-top:2px}}
.stats{{display:flex;gap:6px;margin-top:8px}}
.stat{{flex:1;text-align:center;background:rgba(0,0,0,.25);border-radius:10px;padding:6px 2px}}
.stat b{{display:block;font-size:12px;color:#fbbf24}}.stat span{{font-size:9px;color:#94a3b8}}
.social{{display:flex;gap:8px;margin-bottom:10px;font-size:11px;color:#94a3b8}}
.social span{{flex:1;text-align:center;background:rgba(255,255,255,.05);border-radius:10px;padding:8px 4px}}
.social b{{color:#fbbf24}}
.missions{{background:rgba(255,255,255,.05);border-radius:14px;padding:12px;margin-bottom:12px;font-size:12px}}
.missions div{{display:flex;justify-content:space-between;margin-bottom:6px;color:#cbd5e1}}
.missions .ok{{color:#34d399}}
.rowbtns{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}}
.rowbtns button{{flex:1;min-width:30%;border:none;border-radius:12px;padding:10px 4px;font-size:11px;font-weight:700;cursor:pointer;font-family:inherit;background:rgba(251,191,36,.12);color:#fbbf24;border:1px solid rgba(251,191,36,.25)}}
.label{{font-size:11px;color:#64748b;font-weight:600;margin-bottom:8px}}
.titles{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}}
.titles button{{border:1px solid rgba(255,200,50,.2);background:rgba(0,0,0,.25);color:#e2e8f0;border-radius:20px;padding:6px 10px;font-size:11px;cursor:pointer;font-family:inherit}}
.menu{{display:grid;grid-template-columns:1fr 1fr;gap:11px}}
.menu a{{text-decoration:none;color:#fff;background:rgba(255,255,255,.06);border:1px solid rgba(255,200,50,.14);border-radius:16px;padding:16px 10px;text-align:center;font-size:13px;font-weight:700}}
.menu a .ic{{display:block;font-size:24px;margin-bottom:6px}}
.menu a .sub{{display:block;margin-top:4px;font-size:10px;color:#94a3b8;font-weight:500}}
.invite{{margin-top:14px;font-size:12px;color:#94a3b8;text-align:center}}
.invite code{{display:block;margin-top:6px;padding:10px;background:rgba(0,0,0,.3);border-radius:10px;color:#fbbf24;font-size:11px;word-break:break-all}}
.footer{{text-align:center;margin-top:20px;font-size:11px;color:#475569}}.footer strong{{color:#fbbf24}}
.toast{{position:fixed;bottom:24px;left:16px;right:16px;background:rgba(15,15,40,.95);border:1px solid rgba(251,191,36,.4);border-radius:14px;padding:12px;text-align:center;font-size:13px;font-weight:600;color:#fbbf24;display:none;z-index:50}}
#btnRecover{{display:none}}
</style></head><body>
<div id="splash">
  <div class="splash-slogan">قدرتت را بیدار کن • آینده از آنِ توست</div>
  <div class="loader"><div class="loader-bar" id="loaderBar"></div></div>
</div>
<div id="main">
  <div class="top">{BRAND_HTML}<div class="chip" id="badge">تازه‌وارد</div></div>
  <div class="profile">
    <div class="avatar"><span>☀️</span></div>
    <div class="meta">
      <div class="name" id="name">...</div>
      <div class="user" id="username"></div>
      <div class="stats">
        <div class="stat"><b id="level">1</b><span>سطح</span></div>
        <div class="stat"><b id="score">10</b><span>امتیاز</span></div>
        <div class="stat"><b id="streak">0</b><span>استریک</span></div>
        <div class="stat"><b id="title">Novice</b><span>عنوان</span></div>
      </div>
    </div>
  </div>
  <div class="social">
    <span>دعوت <b id="invites">0</b></span>
    <span>دستاورد <b id="achCount">0</b></span>
    <span>فصل ۱</span>
  </div>
  <div class="missions" id="missionBox">
    <div>مأموریت‌های امروز</div>
    <div id="m1">ثبت فعالیت — …</div>
    <div id="m2">۱ حمله — …</div>
    <div id="m3">کمک/رالی گروه — …</div>
  </div>
  <div class="rowbtns">
    <button type="button" id="btnActive">فعالیت</button>
    <button type="button" id="btnAchieve">دستاورد</button>
    <button type="button" id="btnItem">آیتم</button>
    <button type="button" id="btnMissions">پاداش ۳ مأموریت</button>
    <button type="button" id="btnRecover">بازیابی فشار</button>
  </div>
  <div class="label">عنوان</div>
  <div class="titles" id="titleBox">
    <button type="button" data-t="Novice">Novice</button>
    <button type="button" data-t="Hunter">Hunter</button>
    <button type="button" data-t="Warrior">Warrior</button>
    <button type="button" data-t="Elite">Elite</button>
    <button type="button" data-t="Legend">Legend</button>
  </div>
  <div class="label">موتورهای NEXA</div>
  <div class="menu">
    <a href="/app/wars"><span class="ic">⚔️</span>جنگ‌ها<span class="sub">رتبه جنگ</span></a>
    <a href="/app/groups"><span class="ic">👥</span>گروه‌ها<span class="sub">خروج • رالی</span></a>
    <a href="/app/seasons"><span class="ic">🏆</span>فصل‌ها<span class="sub">پیشرفت</span></a>
    <a href="/app/economy"><span class="ic">💰</span>اقتصاد<span class="sub">فروشگاه</span></a>
  </div>
  <div class="invite">لینک دعوت:<code id="invLink">—</code></div>
  <div class="footer"><strong>NEXA</strong></div>
</div>
<div class="toast" id="toast"></div>
<script>
(function(){{
  var BOT_USER="{BOT_USERNAME}";
  function toast(m){{var t=document.getElementById('toast');t.innerText=m;t.style.display='block';setTimeout(function(){{t.style.display='none'}},2200)}}
  function hideSplash(){{document.getElementById('splash').classList.add('hide');document.getElementById('main').classList.add('show');try{{sessionStorage.setItem('nexa_splash_seen','1')}}catch(e){{}}}}
  var seen=false;try{{seen=sessionStorage.getItem('nexa_splash_seen')==='1'}}catch(e){{}}
  var delay=seen?500:5000;
  var bar=document.getElementById('loaderBar');
  if(bar){{bar.style.transition='width '+(delay/1000)+'s linear';setTimeout(function(){{bar.style.width='100%'}},20)}}
  setTimeout(hideSplash,delay);setTimeout(hideSplash,delay+1000);
  var tg=null,user=null;
  try{{tg=window.Telegram.WebApp;tg.ready();tg.expand()}}catch(e){{}}
  try{{user=tg.initDataUnsafe&&tg.initDataUnsafe.user}}catch(e){{}}
  function setMissions(done){{
    done=done||[];
    document.getElementById('m1').innerHTML=(done.indexOf('m_active')>=0?'<span class="ok">✓</span> ':'○ ')+'ثبت فعالیت';
    document.getElementById('m2').innerHTML=(done.indexOf('m_attack')>=0?'<span class="ok">✓</span> ':'○ ')+'۱ حمله در جنگ';
    document.getElementById('m3').innerHTML=(done.indexOf('m_social')>=0?'<span class="ok">✓</span> ':'○ ')+'کمک یا رالی گروه';
  }}
  function fill(d){{
    if(!d||!d.ok)return;
    document.getElementById('level').innerText=d.level;
    document.getElementById('score').innerText=d.score;
    document.getElementById('badge').innerText=d.badge||'تازه‌وارد';
    document.getElementById('title').innerText=d.title||'Novice';
    document.getElementById('streak').innerText=d.streak||0;
    document.getElementById('invites').innerText=d.invites||0;
    document.getElementById('achCount').innerText=(d.achievements||[]).length;
    document.getElementById('btnRecover').style.display=d.can_recover?'block':'none';
    setMissions(d.missions_done);
  }}
  if(user){{
    document.getElementById('name').innerText=(user.first_name||'')+(user.last_name?(' '+user.last_name):'');
    document.getElementById('username').innerText=user.username?('@'+user.username):'';
    document.getElementById('invLink').innerText='https://t.me/'+BOT_USER+'?start=inv_'+user.id;
    fetch('/api/user/sync',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:user.id,first_name:user.first_name,username:user.username}})}})
    .then(function(r){{return r.json()}}).then(fill);
  }} else document.getElementById('name').innerText='کاربر مهمان';
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
<button class="btn" id="btnJoin" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">ورود (+۱۰)</button>
<button class="btn" id="btnAttack" disabled style="background:linear-gradient(90deg,#dc2626,#f97316);color:#fff;opacity:.45">حمله (+۲۰)</button>
<button class="btn" id="btnDefend" disabled style="background:linear-gradient(90deg,#1d4ed8,#3b82f6);color:#fff;opacity:.45">دفاع (+۱۵)</button>
<button class="btn" id="btnCh" disabled style="background:linear-gradient(90deg,#7c3aed,#a78bfa);color:#fff;opacity:.45">چالش (+۲۵)</button>
<button class="btn" id="btnPower" disabled style="background:linear-gradient(90deg,#ea580c,#fb923c);color:#fff;opacity:.45">قدرت (+۱۸)</button>
<button class="btn" id="btnHeal" disabled style="background:linear-gradient(90deg,#059669,#34d399);color:#0a0a2e;opacity:.45">شفا (+۱۲)</button>
<button class="btn" id="btnRecord" style="background:linear-gradient(90deg,#a21caf,#e879f9);color:#fff">ثبت رکورد</button>
<button class="btn" id="btnLeave" disabled style="background:rgba(255,255,255,.08);color:#94a3b8;opacity:.45">خروج</button>
<div style="margin-top:14px;font-size:12px;color:#64748b;margin-bottom:6px">رتبه جنگ (حمله+دفاع)</div>
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
<button class="btn" id="btnCreate" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">ساخت (+۲۵)</button>
<button class="btn" id="btnHelp" style="background:rgba(59,130,246,.3);color:#93c5fd">کمک گروهی (+۳۰)</button>
<button class="btn" id="btnRally" style="background:linear-gradient(90deg,#0d9488,#2dd4bf);color:#0a0a2e">رالی گروه (+۱۵)</button>
<div id="list"></div>
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function loadList(){fetch('/api/group/list').then(function(r){return r.json()}).then(function(d){
var el=document.getElementById('list');if(!d.ok||!d.groups.length){el.innerHTML='<div style="color:#64748b;font-size:12px">گروهی نیست</div>';return}
el.innerHTML=d.groups.map(function(g){var own=uid&&g.owner===uid;
return '<div style="background:rgba(255,255,255,.06);border-radius:14px;padding:12px;margin-bottom:8px"><div style="display:flex;justify-content:space-between;align-items:center"><div><b>'+g.name+'</b><div style="font-size:11px;color:#94a3b8">'+g.members+' عضو • لول '+(g.level||1)+' • '+g.score+'</div></div><button data-j="'+g.id+'" style="border:none;border-radius:10px;padding:8px 12px;background:rgba(59,130,246,.35);color:#93c5fd;font-weight:700;cursor:pointer">عضویت</button></div><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px"><button data-d="'+g.id+'" style="flex:1;border:none;border-radius:10px;padding:8px;background:rgba(16,185,129,.2);color:#6ee7b7;font-weight:700;cursor:pointer">اهدا</button><button data-r="'+g.id+'" style="flex:1;border:none;border-radius:10px;padding:8px;background:rgba(13,148,136,.25);color:#5eead4;font-weight:700;cursor:pointer">رالی</button>'+(own?'<button data-u="'+g.id+'" style="flex:1;border:none;border-radius:10px;padding:8px;background:rgba(251,191,36,.15);color:#fbbf24;font-weight:700;cursor:pointer">ارتقا</button>':'<button data-l="'+g.id+'" style="flex:1;border:none;border-radius:10px;padding:8px;background:rgba(239,68,68,.15);color:#fca5a5;font-weight:700;cursor:pointer">خروج</button>')+'</div></div>'}).join('');
function act(sel,url,extra){el.querySelectorAll(sel).forEach(function(b){b.onclick=function(){var body=Object.assign({id:uid,group_id:b.getAttribute(sel.replace('[','').replace(']','').split('=')[0].replace('data-',''))},extra||{});var gid=b.getAttribute('data-j')||b.getAttribute('data-d')||b.getAttribute('data-r')||b.getAttribute('data-u')||b.getAttribute('data-l');fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({id:uid,group_id:gid},extra||{}))}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)loadList()})}})}
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
<button class="btn" id="btnMission" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">مأموریت (+۴۰)</button>
<button class="btn" id="btnChest" style="background:linear-gradient(90deg,#d97706,#fbbf24);color:#0a0a2e">صندوق (+۶۰)</button>
<button class="btn" id="btnRank" style="background:linear-gradient(90deg,#be123c,#fb7185);color:#fff">پاداش Top10 (+۸۰)</button>
<button class="btn" id="btnToken" style="background:linear-gradient(90deg,#0ea5e9,#38bdf8);color:#0a0a2e">توکن (+۴۰)</button>
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
<button class="btn" id="btnBoost" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">Boost (+۳۰)</button>
<button class="btn" id="btnPass" style="background:linear-gradient(90deg,#059669,#34d399);color:#0a0a2e">Season Pass (+۱۰۰)</button>
<button class="btn" id="btnBox" style="background:linear-gradient(90deg,#7c3aed,#a78bfa);color:#fff">Mystery Box</button>
<button class="btn" id="btnItem" style="background:linear-gradient(90deg,#4f46e5,#818cf8);color:#fff">آیتم روزانه</button>
<button class="btn" id="buy1" style="background:rgba(251,191,36,.15);color:#fbbf24">نشان طلا (۴۰)</button>
<button class="btn" id="buy2" style="background:rgba(251,191,36,.15);color:#fbbf24">نشان آتش (۶۰)</button>
<button class="btn" id="buy3" style="background:rgba(251,191,36,.15);color:#fbbf24">نشان تاج (۱۰۰)</button>
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
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("NEXA up | %s", WEBHOOK_URL)


@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
