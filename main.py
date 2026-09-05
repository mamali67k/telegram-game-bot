# ============================================================
# NEXA Mini App — main.py
# ساختار: Config → Storage → Domain → Bot → API → UI → Lifecycle
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

# ============================================================
# 1) CONFIG
# ============================================================
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

# اواتار پیش‌فرض: فایل لوکال (بدون CDN / بدون حرف نام کاربر)
DEFAULT_AVATAR_PATH = "/static/nexa-logo.jpg"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("nexa")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ============================================================
# 2) STORAGE (JSON)
# ============================================================
def _load(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("load failed: %s", path)
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


# ============================================================
# 3) DOMAIN — Pro / Score / Badge
# ============================================================
USER_DEFAULTS = {
    "level": 1,
    "score": 10,
    "badge": "تازه‌وارد",
    "title": "Novice",
    "wars_joined": 0,
    "attacks": 0,
    "defenses": 0,
    "groups": [],
    "season_points": 0,
    "token_points": 0,
    "in_war": False,
    "boosts": 0,
    "boxes": 0,
    "invites": 0,
    "invited_by": None,
    "last_boost_day": None,
    "last_mission_day": None,
    "last_box_day": None,
    "last_active_day": None,
    "last_pass_day": None,
    "last_token_day": None,
    "last_challenge_day": None,
    "last_chest_day": None,
    "last_power_day": None,
    "last_rank_reward_day": None,
}


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
    u["score"] = max(0, int(u.get("score", 0)) + delta)
    u["level"] = recalc_level(u["score"])
    u["badge"] = badge_for_level(u["level"])
    return u


def get_or_create_pro(
    user_id: int,
    first_name: str = "",
    username: Optional[str] = None,
) -> dict:
    users = load_users()
    uid = str(user_id)
    now = datetime.now().isoformat()

    if uid not in users:
        row = {
            "user_id": user_id,
            "first_name": first_name,
            "username": username,
            "joined_at": now,
            "last_seen": now,
            **USER_DEFAULTS,
        }
        users[uid] = row
        save_users(users)
        return row

    u = users[uid]
    u["last_seen"] = now
    if first_name:
        u["first_name"] = first_name
    if username is not None:
        u["username"] = username
    for k, v in USER_DEFAULTS.items():
        if k not in u:
            u[k] = v
    save_users(users)
    return u


def public_user(u: dict) -> dict:
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
        "season_points": u.get("season_points", 0),
        "token_points": u.get("token_points", 0),
        "invites": u.get("invites", 0),
    }


def today() -> str:
    return date.today().isoformat()


def require_user(body: dict):
    user_id = body.get("id")
    if not user_id:
        return None, JSONResponse({"ok": False, "msg": "no user"}, status_code=400)
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        get_or_create_pro(int(user_id))
        users = load_users()
    return (users, uid), None


# ============================================================
# 4) BOT HANDLERS
# ============================================================
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

    # دعوت: فقط یک‌بار
    if inviter and inviter != user.id and not users[uid].get("invited_by"):
        inv_uid = str(inviter)
        if inv_uid in users:
            users[uid]["invited_by"] = inviter
            users[inv_uid]["invites"] = users[inv_uid].get("invites", 0) + 1
            apply_score(inv_uid, 50, users)
            apply_score(uid, 20, users)
            save_users(users)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="☀️ ورود به NEXA", web_app=WebAppInfo(url=MINIAPP_URL))]
        ]
    )
    await message.answer(
        "به NEXA خوش آمدید ☀️\n\nقدرتت را بیدار کن.\nآینده از آنِ توست.",
        reply_markup=kb,
    )


# ============================================================
# 5) APP + WEBHOOK + HEALTH
# ============================================================
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
        logger.exception("webhook error")
        return {"ok": False}


@app.api_route("/", methods=["GET", "HEAD"])
async def health():
    return {"status": "NEXA is alive ✅"}


# ============================================================
# 6) API — USER / PRO
# ============================================================
@app.post("/api/user/sync")
async def api_user_sync(request: Request):
    try:
        body = await request.json()
        user_id = body.get("id")
        if not user_id:
            return JSONResponse({"ok": False}, status_code=400)
        pro = get_or_create_pro(
            int(user_id),
            body.get("first_name") or "",
            body.get("username"),
        )
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
        if users[uid].get("last_active_day") == today():
            return {"ok": False, "msg": "امروز فعالیتت ثبت شده"}
        users[uid]["last_active_day"] = today()
        apply_score(uid, 10, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "فعالیت روزانه! +۱۰"}
    except Exception as e:
        logger.exception("active")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/pro/title")
async def api_pro_title(request: Request):
    allowed = {"Novice", "Hunter", "Warrior", "Elite", "Legend"}
    try:
        body = await request.json()
        title = (body.get("title") or "").strip()
        if title not in allowed:
            return {"ok": False, "msg": "عنوان مجاز نیست"}
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        users[uid]["title"] = title
        save_users(users)
        return {**public_user(users[uid]), "msg": f"عنوان «{title}» تنظیم شد"}
    except Exception as e:
        logger.exception("title")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


# ============================================================
# 7) API — WAR
# ============================================================
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
        if not users[uid].get("in_war"):
            return {"ok": False, "msg": "اول وارد جنگ شو"}
        users[uid]["attacks"] = users[uid].get("attacks", 0) + 1
        apply_score(uid, 20, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "حمله! +۲۰"}
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
        return {**public_user(users[uid]), "msg": "چالش کامل شد! +۲۵"}
    except Exception as e:
        logger.exception("war.challenge")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/war/power")
async def api_war_power(request: Request):
    """قدرت جنگ — مرحله جدید پلن (+۱۸ روزانه)"""
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
        return {**public_user(users[uid]), "msg": "قدرت جنگ فعال شد! +۱۸"}
    except Exception as e:
        logger.exception("war.power")
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
        save_users(users)
        return {**public_user(users[uid]), "msg": "از جنگ خارج شدی"}
    except Exception as e:
        logger.exception("war.leave")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


# ============================================================
# 8) API — GROUP
# ============================================================
@app.post("/api/group/create")
async def api_group_create(request: Request):
    try:
        body = await request.json()
        name = (body.get("name") or "").strip()
        if len(name) < 2:
            return {"ok": False, "msg": "نام گروه کوتاه است"}
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        groups = load_groups()
        for g in groups.values():
            if g.get("name", "").lower() == name.lower():
                return {"ok": False, "msg": "نام تکراری است"}
        gid = f"g{int(datetime.now().timestamp())}"
        groups[gid] = {
            "id": gid,
            "name": name,
            "owner": int(body["id"]),
            "members": [int(body["id"])],
            "score": 0,
            "level": 1,
            "created_at": datetime.now().isoformat(),
        }
        save_groups(groups)
        users[uid].setdefault("groups", []).append(gid)
        apply_score(uid, 25, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": f"گروه «{name}» ساخته شد! +۲۵"}
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
            return {"ok": False, "msg": "گروه پیدا نشد"}
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
        return {**public_user(users[uid]), "msg": f"عضو «{g['name']}» شدی! +۱۵"}
    except Exception as e:
        logger.exception("group.join")
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
            return {"ok": False, "msg": "گروه پیدا نشد"}
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
        return {**public_user(users[uid]), "msg": f"سطح گروه: {g['level']}"}
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
        if not users[uid].get("groups"):
            return {"ok": False, "msg": "اول عضو گروه شو"}
        apply_score(uid, 30, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "کمک گروهی! +۳۰"}
    except Exception as e:
        logger.exception("group.help")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/group/donate")
async def api_group_donate(request: Request):
    """اهدای امتیاز به گروه — مرحله جدید پلن"""
    try:
        body = await request.json()
        group_id = body.get("group_id")
        amount = int(body.get("amount") or 10)
        amount = max(5, min(amount, 50))
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        groups = load_groups()
        if group_id not in groups:
            return {"ok": False, "msg": "گروه پیدا نشد"}
        if group_id not in (users[uid].get("groups") or []):
            return {"ok": False, "msg": "عضو این گروه نیستی"}
        if users[uid].get("score", 0) < amount:
            return {"ok": False, "msg": "امتیاز کافی نیست"}
        apply_score(uid, -amount, users)
        groups[group_id]["score"] = groups[group_id].get("score", 0) + amount
        save_groups(groups)
        save_users(users)
        return {
            **public_user(users[uid]),
            "msg": f"{amount} امتیاز به گروه اهدا شد",
            "group_score": groups[group_id]["score"],
        }
    except Exception as e:
        logger.exception("group.donate")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.get("/api/group/list")
async def api_group_list():
    groups = load_groups()
    items = [
        {
            "id": g["id"],
            "name": g["name"],
            "members": len(g.get("members") or []),
            "score": g.get("score", 0),
            "level": g.get("level", 1),
            "owner": g.get("owner"),
        }
        for g in groups.values()
    ]
    items.sort(key=lambda x: x["score"], reverse=True)
    return {"ok": True, "groups": items[:30]}


# ============================================================
# 9) API — ECONOMY / SEASON / FUTURE
# ============================================================
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
        logger.exception("economy.boost")
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
        logger.exception("economy.box")
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
        logger.exception("economy.pass")
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
        logger.exception("season.mission")
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
        logger.exception("season.chest")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.post("/api/season/rank_reward")
async def api_season_rank_reward(request: Request):
    """پاداش رتبه — اگر جزو ۱۰ نفر برتر باشی (+80 روزانه یک‌بار)"""
    try:
        body = await request.json()
        ctx, err = require_user(body)
        if err:
            return err
        users, uid = ctx
        if users[uid].get("last_rank_reward_day") == today():
            return {"ok": False, "msg": "پاداش رتبه امروز گرفته شده"}

        ranking = sorted(
            users.values(),
            key=lambda x: x.get("score", 0),
            reverse=True,
        )
        top_ids = [str(u.get("user_id")) for u in ranking[:10]]
        if uid not in top_ids:
            return {"ok": False, "msg": "باید جزو ۱۰ نفر برتر باشی"}

        users[uid]["last_rank_reward_day"] = today()
        apply_score(uid, 80, users)
        save_users(users)
        place = top_ids.index(uid) + 1
        return {**public_user(users[uid]), "msg": f"پاداش رتبه #{place}! +۸۰"}
    except Exception as e:
        logger.exception("season.rank_reward")
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
            return {"ok": False, "msg": "مأموریت توکن امروز انجام شده"}
        users[uid]["last_token_day"] = today()
        users[uid]["token_points"] = users[uid].get("token_points", 0) + 40
        apply_score(uid, 40, users)
        save_users(users)
        return {**public_user(users[uid]), "msg": "مأموریت توکن! +۴۰"}
    except Exception as e:
        logger.exception("future.token")
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@app.get("/api/rank/top")
async def api_rank_top():
    users = load_users()
    rows = [
        {
            "name": u.get("first_name") or u.get("username") or "بازیکن",
            "score": u.get("score", 0),
            "level": u.get("level", 1),
        }
        for u in users.values()
    ]
    rows.sort(key=lambda x: x["score"], reverse=True)
    return {"ok": True, "ranks": rows[:20]}


# ============================================================
# 10) UI HELPERS
# ============================================================
BRAND_HEADER_CSS = """
.brand-bar{display:flex;align-items:center;gap:10px}
.brand-logo{width:36px;height:36px;border-radius:50%;overflow:hidden;flex-shrink:0;box-shadow:0 0 0 2px rgba(255,215,0,.45)}
.brand-logo img{width:100%;height:100%;object-fit:cover;display:block}
.brand-logo.fb{display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#ffd700,#ff8c00);font-size:18px}
.brand-name{font-size:18px;font-weight:800;letter-spacing:3px;background:linear-gradient(90deg,#ffe566,#ffb800);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
"""

BRAND_HEADER_HTML = f"""
<div class="brand-bar">
  <div class="brand-logo">
    <img src="{DEFAULT_AVATAR_PATH}" alt="NEXA"
      onerror="this.parentElement.classList.add('fb');this.parentElement.innerHTML='☀️';">
  </div>
  <div class="brand-name">NEXA</div>
</div>
"""


def page_shell(title_icon: str, title: str, body_html: str, extra_js: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
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
{BRAND_HEADER_CSS}
.btn{{display:block;width:100%;border:none;border-radius:14px;padding:14px;font-size:15px;font-weight:700;margin-bottom:10px;cursor:pointer;font-family:inherit}}
.toast{{position:fixed;bottom:24px;left:16px;right:16px;background:rgba(15,15,40,.95);border:1px solid rgba(251,191,36,.4);border-radius:14px;padding:12px;text-align:center;font-size:13px;font-weight:600;color:#fbbf24;display:none;z-index:50}}
.footer{{text-align:center;margin-top:20px;font-size:11px;color:#475569}}.footer strong{{color:#fbbf24}}
</style></head><body>
<div class="wrap">
  <div class="top">
    <div class="top-right"><a class="back" href="/app">→</a>{BRAND_HEADER_HTML}</div>
    <div class="page-title">{title_icon} {title}</div>
  </div>
  {body_html}
  <div class="footer"><strong>NEXA</strong></div>
</div>
<script>
var tg=window.Telegram.WebApp;try{{tg.ready();tg.expand()}}catch(e){{}}
function toast(m){{var t=document.getElementById('toast');if(!t)return;t.innerText=m;t.style.display='block';setTimeout(function(){{t.style.display='none'}},2000)}}
{extra_js}
</script></body></html>"""


# ============================================================
# 11) UI — HOME (/app)
# ============================================================
@app.get("/app", response_class=HTMLResponse)
async def mini_app():
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
#splash{{position:fixed;inset:0;z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;
background:#05051a url('{DEFAULT_AVATAR_PATH}') center center / cover no-repeat;padding-bottom:18%;transition:opacity .35s,visibility .35s}}
#splash.hide{{opacity:0;visibility:hidden;pointer-events:none}}
.splash-slogan{{font-size:15px;color:rgba(255,255,255,.8);font-weight:600;text-align:center;padding:0 28px;margin-bottom:18px;text-shadow:0 2px 14px rgba(0,0,0,.55)}}
.loader{{width:56px;height:4px;background:rgba(255,255,255,.22);border-radius:4px;overflow:hidden;margin-bottom:8px}}
.loader-bar{{height:100%;width:0;background:linear-gradient(90deg,#ff8c00,#ffd700)}}
#main{{display:none;position:relative;z-index:1;padding:14px 14px 36px;background:linear-gradient(180deg,#0a0a2e,#05051a)}}
#main.show{{display:block}}
.top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}}
{BRAND_HEADER_CSS}
.chip{{font-size:11px;background:rgba(251,191,36,.15);color:#fbbf24;padding:5px 11px;border-radius:20px;font-weight:600}}
.profile{{background:rgba(255,255,255,.07);border:1px solid rgba(255,200,50,.16);border-radius:18px;padding:14px;display:flex;align-items:center;gap:12px;margin-bottom:12px}}
.avatar-wrap{{width:52px;height:52px;border-radius:50%;border:2px solid #fbbf24;overflow:hidden;flex-shrink:0;background:#1a1635}}
.avatar-wrap img{{width:100%;height:100%;object-fit:cover;display:block}}
.profile .meta{{flex:1;min-width:0}}
.profile .name{{font-weight:700;font-size:15px}}
.profile .user{{font-size:12px;color:#94a3b8;margin-top:2px}}
.stats{{display:flex;gap:8px;margin-top:8px}}
.stat{{flex:1;text-align:center;background:rgba(0,0,0,.25);border-radius:10px;padding:6px}}
.stat b{{display:block;font-size:13px;color:#fbbf24}}
.stat span{{font-size:10px;color:#94a3b8}}
.rowbtns button{{width:100%;border:none;border-radius:12px;padding:10px;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;background:rgba(251,191,36,.12);color:#fbbf24;border:1px solid rgba(251,191,36,.25);margin-bottom:12px}}
.label{{font-size:11px;color:#64748b;font-weight:600;margin-bottom:8px}}
.titles{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}}
.titles button{{border:1px solid rgba(255,200,50,.2);background:rgba(0,0,0,.25);color:#e2e8f0;border-radius:20px;padding:6px 10px;font-size:11px;cursor:pointer;font-family:inherit}}
.menu{{display:grid;grid-template-columns:1fr 1fr;gap:11px}}
.menu a{{text-decoration:none;color:#fff;background:rgba(255,255,255,.06);border:1px solid rgba(255,200,50,.14);border-radius:16px;padding:16px 10px;text-align:center;font-size:13px;font-weight:700}}
.menu a .ic{{display:block;font-size:24px;margin-bottom:6px}}
.menu a .sub{{display:block;margin-top:4px;font-size:10px;color:#94a3b8;font-weight:500}}
.invite{{margin-top:14px;font-size:12px;color:#94a3b8;text-align:center}}
.invite code{{display:block;margin-top:6px;padding:10px;background:rgba(0,0,0,.3);border-radius:10px;color:#fbbf24;font-size:11px;word-break:break-all}}
.footer{{text-align:center;margin-top:20px;font-size:11px;color:#475569}}
.footer strong{{color:#fbbf24}}
.toast{{position:fixed;bottom:24px;left:16px;right:16px;background:rgba(15,15,40,.95);border:1px solid rgba(251,191,36,.4);border-radius:14px;padding:12px;text-align:center;font-size:13px;font-weight:600;color:#fbbf24;display:none;z-index:50}}
</style>
</head>
<body>
<div id="splash">
  <div class="splash-slogan">قدرتت را بیدار کن • آینده از آنِ توست</div>
  <div class="loader"><div class="loader-bar" id="loaderBar"></div></div>
</div>
<div id="main">
  <div class="top">{BRAND_HEADER_HTML}<div class="chip" id="badge">تازه‌وارد</div></div>
  <div class="profile">
    <div class="avatar-wrap">
      <img id="avatar" src="{DEFAULT_AVATAR_PATH}" alt="avatar" width="52" height="52">
    </div>
    <div class="meta">
      <div class="name" id="name">...</div>
      <div class="user" id="username"></div>
      <div class="stats">
        <div class="stat"><b id="level">1</b><span>سطح</span></div>
        <div class="stat"><b id="score">10</b><span>امتیاز</span></div>
        <div class="stat"><b id="title">Novice</b><span>عنوان</span></div>
      </div>
    </div>
  </div>
  <div class="rowbtns"><button type="button" id="btnActive">فعالیت روزانه (+۱۰)</button></div>
  <div class="label">انتخاب عنوان</div>
  <div class="titles" id="titleBox">
    <button type="button" data-t="Novice">Novice</button>
    <button type="button" data-t="Hunter">Hunter</button>
    <button type="button" data-t="Warrior">Warrior</button>
    <button type="button" data-t="Elite">Elite</button>
    <button type="button" data-t="Legend">Legend</button>
  </div>
  <div class="label">موتورهای NEXA</div>
  <div class="menu">
    <a href="/app/wars"><span class="ic">⚔️</span>جنگ‌ها<span class="sub">قدرت فعال</span></a>
    <a href="/app/groups"><span class="ic">👥</span>گروه‌ها<span class="sub">اهدا فعال</span></a>
    <a href="/app/seasons"><span class="ic">🏆</span>فصل‌ها<span class="sub">پاداش رتبه</span></a>
    <a href="/app/economy"><span class="ic">💰</span>اقتصاد<span class="sub">Boost • Pass</span></a>
  </div>
  <div class="invite">لینک دعوت:<code id="invLink">—</code></div>
  <div class="footer"><strong>NEXA</strong></div>
</div>
<div class="toast" id="toast"></div>
<script>
(function(){{
  var DEFAULT_AVATAR = "{DEFAULT_AVATAR_PATH}";
  var BOT_USER = "{BOT_USERNAME}";

  function toast(m){{
    var t=document.getElementById('toast');
    t.innerText=m; t.style.display='block';
    setTimeout(function(){{t.style.display='none'}},2000);
  }}

  function hideSplash(){{
    document.getElementById('splash').classList.add('hide');
    document.getElementById('main').classList.add('show');
    try{{sessionStorage.setItem('nexa_splash_seen','1')}}catch(e){{}}
  }}

  // لودینگ: ورود اول ۵ثانیه | برگشت ۰.۵ثانیه
  var seen=false;
  try{{seen=sessionStorage.getItem('nexa_splash_seen')==='1'}}catch(e){{}}
  var delay = seen ? 500 : 5000;
  var bar=document.getElementById('loaderBar');
  if(bar){{
    bar.style.transition='width '+(delay/1000)+'s linear';
    setTimeout(function(){{bar.style.width='100%'}},20);
  }}
  setTimeout(hideSplash, delay);
  setTimeout(hideSplash, delay+900);

  // اواتار: فقط عکس واقعی تلگرام یا لوگو لوکال — هرگز از حرف نام ساخته نمی‌شود
  function setAvatar(photoUrl){{
    var img=document.getElementById('avatar');
    img.onerror=function(){{
      this.onerror=null;
      this.src=DEFAULT_AVATAR;
    }};
    if(photoUrl && typeof photoUrl==='string' && photoUrl.indexOf('http')===0){{
      img.src=photoUrl;
    }} else {{
      img.src=DEFAULT_AVATAR;
    }}
  }}
  // پیش‌فرض فوری
  setAvatar(null);

  var tg=null, user=null;
  try{{tg=window.Telegram.WebApp;tg.ready();tg.expand()}}catch(e){{}}
  try{{user=tg.initDataUnsafe && tg.initDataUnsafe.user}}catch(e){{}}

  if(user){{
    document.getElementById('name').innerText=(user.first_name||'')+(user.last_name?(' '+user.last_name):'');
    document.getElementById('username').innerText=user.username?('@'+user.username):'';
    setAvatar(user.photo_url || null);
    document.getElementById('invLink').innerText='https://t.me/'+BOT_USER+'?start=inv_'+user.id;
    fetch('/api/user/sync',{{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{id:user.id,first_name:user.first_name,username:user.username}})
    }}).then(function(r){{return r.json()}}).then(function(d){{
      if(d&&d.ok){{
        document.getElementById('level').innerText=d.level;
        document.getElementById('score').innerText=d.score;
        document.getElementById('badge').innerText=d.badge||'تازه‌وارد';
        document.getElementById('title').innerText=d.title||'Novice';
      }}
    }}).catch(function(){{}});
  }} else {{
    document.getElementById('name').innerText='کاربر مهمان';
    setAvatar(null);
  }}

  document.getElementById('btnActive').onclick=function(){{
    if(!user){{toast('از تلگرام وارد شو');return}}
    fetch('/api/pro/active',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:user.id}})}})
    .then(function(r){{return r.json()}}).then(function(d){{
      toast(d.msg||'');
      if(d.ok){{
        document.getElementById('score').innerText=d.score;
        document.getElementById('level').innerText=d.level;
        document.getElementById('badge').innerText=d.badge;
      }}
    }});
  }};

  document.querySelectorAll('#titleBox button').forEach(function(b){{
    b.onclick=function(){{
      if(!user){{toast('از تلگرام وارد شو');return}}
      fetch('/api/pro/title',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:user.id,title:b.getAttribute('data-t')}})}})
      .then(function(r){{return r.json()}}).then(function(d){{
        toast(d.msg||'');
        if(d.ok) document.getElementById('title').innerText=d.title;
      }});
    }};
  }});
}})();
</script>
</body>
</html>"""
    return HTMLResponse(html)


# ============================================================
# 12) UI — WARS / GROUPS / SEASONS / ECONOMY
# ============================================================
@app.get("/app/wars", response_class=HTMLResponse)
async def page_wars():
    body = """
<p style="color:#94a3b8;font-size:13px;margin-bottom:12px">ورود • حمله • دفاع • چالش • قدرت • خروج</p>
<div style="background:rgba(255,255,255,.06);border-radius:16px;padding:14px;margin-bottom:12px;font-size:13px">
  <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>وضعیت</span><b id="warStatus" style="color:#fbbf24">—</b></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>امتیاز</span><b id="score" style="color:#fbbf24">—</b></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>حمله</span><b id="attacks" style="color:#fbbf24">0</b></div>
  <div style="display:flex;justify-content:space-between"><span>دفاع</span><b id="defenses" style="color:#fbbf24">0</b></div>
</div>
<button class="btn" id="btnJoin" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">ورود (+۱۰)</button>
<button class="btn" id="btnAttack" disabled style="background:linear-gradient(90deg,#dc2626,#f97316);color:#fff;opacity:.45">حمله (+۲۰)</button>
<button class="btn" id="btnDefend" disabled style="background:linear-gradient(90deg,#1d4ed8,#3b82f6);color:#fff;opacity:.45">دفاع (+۱۵)</button>
<button class="btn" id="btnCh" disabled style="background:linear-gradient(90deg,#7c3aed,#a78bfa);color:#fff;opacity:.45">چالش (+۲۵)</button>
<button class="btn" id="btnPower" disabled style="background:linear-gradient(90deg,#ea580c,#fb923c);color:#fff;opacity:.45">قدرت جنگ (+۱۸)</button>
<button class="btn" id="btnLeave" disabled style="background:rgba(255,255,255,.08);color:#94a3b8;opacity:.45">خروج</button>
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function apply(d){
  if(!d||!d.ok)return;
  document.getElementById('score').innerText=d.score;
  document.getElementById('attacks').innerText=d.attacks||0;
  document.getElementById('defenses').innerText=d.defenses||0;
  var on=!!d.in_war;
  document.getElementById('warStatus').innerText=on?'در جنگ':'خارج';
  ['btnAttack','btnDefend','btnCh','btnPower','btnLeave'].forEach(function(id){
    var b=document.getElementById(id);b.disabled=!on;b.style.opacity=on?'1':'.45';
  });
  document.getElementById('btnJoin').disabled=on;
  document.getElementById('btnJoin').style.opacity=on?'.45':'1';
}
function call(u){
  if(!uid){toast('وارد شو');return}
  fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})})
  .then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)apply(d)});
}
document.getElementById('btnJoin').onclick=function(){call('/api/war/join')};
document.getElementById('btnAttack').onclick=function(){call('/api/war/attack')};
document.getElementById('btnDefend').onclick=function(){call('/api/war/defend')};
document.getElementById('btnCh').onclick=function(){call('/api/war/challenge')};
document.getElementById('btnPower').onclick=function(){call('/api/war/power')};
document.getElementById('btnLeave').onclick=function(){call('/api/war/leave')};
if(uid)fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})}).then(function(r){return r.json()}).then(apply);
"""
    return HTMLResponse(page_shell("⚔️", "جنگ‌ها", body, js))


@app.get("/app/groups", response_class=HTMLResponse)
async def page_groups():
    body = """
<input id="gname" maxlength="24" placeholder="نام گروه..." style="width:100%;padding:12px;border-radius:12px;border:1px solid rgba(255,200,50,.25);background:rgba(0,0,0,.3);color:#fff;margin-bottom:10px;font-family:inherit">
<button class="btn" id="btnCreate" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">ساخت (+۲۵)</button>
<button class="btn" id="btnHelp" style="background:rgba(59,130,246,.3);color:#93c5fd">کمک گروهی (+۳۰)</button>
<div id="list"></div>
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function loadList(){
  fetch('/api/group/list').then(function(r){return r.json()}).then(function(d){
    var el=document.getElementById('list');
    if(!d.ok||!d.groups.length){el.innerHTML='<div style="color:#64748b;font-size:12px">گروهی نیست</div>';return}
    el.innerHTML=d.groups.map(function(g){
      var own=uid&&g.owner===uid;
      return '<div style="background:rgba(255,255,255,.06);border-radius:14px;padding:12px;margin-bottom:8px">'
        +'<div style="display:flex;justify-content:space-between;align-items:center">'
        +'<div><b>'+g.name+'</b><div style="font-size:11px;color:#94a3b8">'+g.members+' عضو • لول '+(g.level||1)+' • امتیاز گروه '+g.score+'</div></div>'
        +'<button data-j="'+g.id+'" style="border:none;border-radius:10px;padding:8px 12px;background:rgba(59,130,246,.35);color:#93c5fd;font-weight:700;cursor:pointer">عضویت</button></div>'
        +'<div style="display:flex;gap:6px;margin-top:8px">'
        +'<button data-d="'+g.id+'" style="flex:1;border:none;border-radius:10px;padding:8px;background:rgba(16,185,129,.2);color:#6ee7b7;font-weight:700;cursor:pointer">اهدا ۱۰</button>'
        +(own?'<button data-u="'+g.id+'" style="flex:1;border:none;border-radius:10px;padding:8px;background:rgba(251,191,36,.15);color:#fbbf24;font-weight:700;cursor:pointer">ارتقا</button>':'')
        +'</div></div>';
    }).join('');
    el.querySelectorAll('[data-j]').forEach(function(b){
      b.onclick=function(){
        fetch('/api/group/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,group_id:b.getAttribute('data-j')})})
        .then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)loadList()});
      };
    });
    el.querySelectorAll('[data-u]').forEach(function(b){
      b.onclick=function(){
        fetch('/api/group/upgrade',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,group_id:b.getAttribute('data-u')})})
        .then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)loadList()});
      };
    });
    el.querySelectorAll('[data-d]').forEach(function(b){
      b.onclick=function(){
        fetch('/api/group/donate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,group_id:b.getAttribute('data-d'),amount:10})})
        .then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)loadList()});
      };
    });
  });
}
document.getElementById('btnCreate').onclick=function(){
  if(!uid){toast('وارد شو');return}
  var n=document.getElementById('gname').value.trim();
  if(n.length<2){toast('نام کوتاه');return}
  fetch('/api/group/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,name:n})})
  .then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok){document.getElementById('gname').value='';loadList()}});
};
document.getElementById('btnHelp').onclick=function(){
  if(!uid){toast('وارد شو');return}
  fetch('/api/group/help',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})})
  .then(function(r){return r.json()}).then(function(d){toast(d.msg||'')});
};
loadList();
"""
    return HTMLResponse(page_shell("👥", "گروه‌ها", body, js))


@app.get("/app/seasons", response_class=HTMLResponse)
async def page_seasons():
    body = """
<div style="background:rgba(255,255,255,.06);border-radius:16px;padding:14px;margin-bottom:12px;font-size:13px">
  <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>امتیاز فصل</span><b id="sp" style="color:#fbbf24">0</b></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>توکن</span><b id="tp" style="color:#fbbf24">0</b></div>
  <div style="display:flex;justify-content:space-between"><span>امتیاز کل</span><b id="score" style="color:#fbbf24">—</b></div>
</div>
<button class="btn" id="btnMission" style="background:linear-gradient(90deg,#b45309,#f59e0b);color:#0a0a2e">مأموریت فصل (+۴۰)</button>
<button class="btn" id="btnChest" style="background:linear-gradient(90deg,#d97706,#fbbf24);color:#0a0a2e">صندوق فصل (+۶۰)</button>
<button class="btn" id="btnRank" style="background:linear-gradient(90deg,#be123c,#fb7185);color:#fff">پاداش رتبه Top10 (+۸۰)</button>
<button class="btn" id="btnToken" style="background:linear-gradient(90deg,#0ea5e9,#38bdf8);color:#0a0a2e">مأموریت توکن (+۴۰)</button>
<div id="ranks" style="margin-top:12px"></div>
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function fill(d){if(!d||!d.ok)return;document.getElementById('score').innerText=d.score;document.getElementById('sp').innerText=d.season_points||0;document.getElementById('tp').innerText=d.token_points||0}
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
<div class="toast" id="toast"></div>"""
    js = """
var user=null;try{user=tg.initDataUnsafe.user}catch(e){}
var uid=user?user.id:null;
function fill(d){if(!d||!d.ok)return;document.getElementById('score').innerText=d.score;document.getElementById('boosts').innerText=d.boosts||0;document.getElementById('boxes').innerText=d.boxes||0}
function call(u){if(!uid){toast('وارد شو');return}fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid})}).then(function(r){return r.json()}).then(function(d){toast(d.msg||'');if(d.ok)fill(d)})}
document.getElementById('btnBoost').onclick=function(){call('/api/economy/boost')};
document.getElementById('btnPass').onclick=function(){call('/api/economy/pass')};
document.getElementById('btnBox').onclick=function(){call('/api/economy/box')};
if(uid)fetch('/api/user/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:uid,first_name:user.first_name,username:user.username})}).then(function(r){return r.json()}).then(fill);
"""
    return HTMLResponse(page_shell("💰", "اقتصاد", body, js))


# ============================================================
# 13) LIFECYCLE
# ============================================================
@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("NEXA started | webhook=%s", WEBHOOK_URL)


@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
