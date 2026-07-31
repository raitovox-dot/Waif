"""
Spawn tizimi:
- Normal spawn: har N xabarda random waifu (rarity bo'yicha) chiqadi
- Divine spawn: bir guruhda 10 ta Exclusive tutilganda Divine waifu chiqadi
- Event spawn: aktiv event bo'lsa, bot asosiy guruhida har M xabarda event waifu chiqadi
"""
import asyncio
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import waifus as waifu_db
from database import collections as col_db
from database import users as user_db
from database import groups as grp_db
from database import logs as log_db
from database import events as event_db
from utils.helpers import get_rarity_emoji, get_coin_reward, get_bot_group_id
from utils.stickers import get_catch_sticker, send_sticker as send_stk

SPAWN_TIMEOUT = 15 * 60  # 15 daqiqa

active_spawns: dict = {}

_catch_attempts: dict = {}
CATCH_LIMIT = 3
CATCH_WINDOW = 60


def _is_catch_flooded(user_id: int) -> bool:
    now = time.time()
    attempts = _catch_attempts.get(user_id, [])
    attempts = [t for t in attempts if now - t < CATCH_WINDOW]
    if len(attempts) >= CATCH_LIMIT:
        _catch_attempts[user_id] = attempts
        return True
    attempts.append(now)
    _catch_attempts[user_id] = attempts
    return False


def _name_matches(guess: str, target: str) -> bool:
    guess = guess.lower().strip()
    target = target.lower().strip()
    if guess == target:
        return True
    # Qisman moslik (60% harflar to'g'ri bo'lsa)
    if len(guess) >= 3 and (guess in target or target.startswith(guess)):
        return True
    return False


async def restore_active_spawns(context):
    """Server restart bo'lganda DB dagi aktiv spawnlarni xotiraga qayta yuklaydi."""
    now = datetime.now()
    restored = 0
    try:
        pool = await grp_db.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM spawn_state WHERE waifu_id IS NOT NULL"
            )
            expired_ids = []
            for row in rows:
                group_id = row['group_id']
                waifu_id = row['waifu_id']
                expires_at = row['expires_at']
                is_event = row.get('is_event', 0) or 0
                event_id = row.get('event_id')
                if not expires_at:
                    expired_ids.append(group_id)
                    continue
                if expires_at.replace(tzinfo=None) <= now:
                    expired_ids.append(group_id)
                    continue
                # Event waifu
                if is_event and event_id:
                    ew = None
                    ew_rows = await conn.fetch(
                        "SELECT * FROM event_waifus WHERE waifu_id=$1", waifu_id
                    )
                    if ew_rows:
                        ew = dict(ew_rows[0])
                    if not ew:
                        expired_ids.append(group_id)
                        continue
                    active_spawns[group_id] = {
                        "waifu_id": ew["waifu_id"],
                        "waifu_name": ew["name"],
                        "file_id": ew["file_id"],
                        "rarity": ew["rarity"],
                        "anime": ew["anime"],
                        "price": ew.get("price", 0),
                        "expires_at": expires_at.replace(tzinfo=None),
                        "coin_multiplier": 1.0,
                        "is_event": True,
                        "event_id": event_id,
                    }
                else:
                    waifu = await waifu_db.get_waifu(waifu_id)
                    if not waifu:
                        expired_ids.append(group_id)
                        continue
                    active_spawns[group_id] = {
                        "waifu_id": waifu["waifu_id"],
                        "waifu_name": waifu["name"],
                        "file_id": waifu["file_id"],
                        "rarity": waifu["rarity"],
                        "anime": waifu["anime"],
                        "price": waifu.get("price", 0),
                        "expires_at": expires_at.replace(tzinfo=None),
                        "coin_multiplier": 1.0,
                        "is_event": False,
                        "event_id": None,
                    }
                remaining = (expires_at.replace(tzinfo=None) - now).total_seconds()
                asyncio.create_task(expire_spawn(context, group_id, int(remaining)))
                restored += 1
            for gid in expired_ids:
                await conn.execute("DELETE FROM spawn_state WHERE group_id=$1", gid)
    except Exception as e:
        print("restore_active_spawns error:", e)
    if restored:
        print("Restored", restored, "active spawn(s) from DB")


async def expire_spawn(context, group_id: int, delay: int):
    await asyncio.sleep(delay)
    if group_id in active_spawns:
        spawn = active_spawns.pop(group_id, None)
        if spawn:
            try:
                emoji = get_rarity_emoji(spawn["rarity"])
                await context.bot.send_message(
                    group_id,
                    f"⌛ {emoji} <b>{spawn['waifu_name']}</b> yo'qoldi! Hech kim tutmadi.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        try:
            await grp_db.clear_spawn_state(group_id)
        except Exception:
            pass


async def _do_spawn(context, group_id: int, is_event: bool = False, active_event=None):
    """Guruhda spawn qilish — normal yoki event"""
    if group_id in active_spawns:
        return
    try:
        if is_event and active_event:
            ew = await event_db.get_random_event_waifu(active_event['id'])
            if not ew:
                return
            file_id = ew['file_id']
            rarity = ew['rarity']
            waifu_name = ew['name']
            anime = ew['anime']
            waifu_id = ew['waifu_id']
            price = ew.get('price', 0) or 0
            is_ev_flag = True
            event_id = active_event['id']
        else:
            waifu = await waifu_db.get_random_waifu_by_rarity_weight()
            if not waifu:
                return
            # Divine emas bo'lishi kerak (Divine maxsus)
            while waifu and waifu['rarity'] == 'Divine':
                waifu = await waifu_db.get_random_waifu_by_rarity_weight()
            if not waifu:
                return
            file_id = waifu['file_id']
            rarity = waifu['rarity']
            waifu_name = waifu['name']
            anime = waifu['anime']
            waifu_id = waifu['waifu_id']
            price = waifu.get('price', 0) or 0
            is_ev_flag = False
            event_id = None

        now = datetime.now()
        expires_at = now + timedelta(seconds=SPAWN_TIMEOUT)
        active_spawns[group_id] = {
            "waifu_id": waifu_id,
            "waifu_name": waifu_name,
            "file_id": file_id,
            "rarity": rarity,
            "anime": anime,
            "price": price,
            "expires_at": expires_at,
            "coin_multiplier": 1.0,
            "is_event": is_ev_flag,
            "event_id": event_id,
        }
        await grp_db.set_spawn_state(group_id, waifu_id, now, expires_at)
        asyncio.create_task(expire_spawn(context, group_id, SPAWN_TIMEOUT))

        emoji = get_rarity_emoji(rarity)
        event_badge = f"\n⚡ <b>EVENT WAIFU!</b> [{active_event['name']}]" if is_ev_flag else ""
        price_line = f"\n💰 Narx: <b>{price:,}</b> coin" if price else ""
        stk = get_catch_sticker(rarity)
        await send_stk(context.bot, group_id, stk)
        await context.bot.send_photo(
            chat_id=group_id,
            photo=file_id,
            caption=(
                f"✨ <b>WAIFU PAYDO BO'LDI!</b>{event_badge}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{emoji} <b>{rarity.upper()}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Ismini bilasizmi? <code>/waifu [ism]</code> deb yozing!\n"
                f"⏰ <b>15 daqiqa</b> vaqt!{price_line}"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"_do_spawn error [{group_id}]:", e)


async def _do_divine_spawn(context, group_id: int):
    """Divine waifu spawn qilish (10 ta Exclusive tutilganda)"""
    if group_id in active_spawns:
        return
    try:
        divine_waifu = await waifu_db.get_random_waifu("Divine")
        if not divine_waifu:
            return
        file_id = divine_waifu['file_id']
        waifu_id = divine_waifu['waifu_id']
        waifu_name = divine_waifu['name']
        anime = divine_waifu['anime']
        price = divine_waifu.get('price', 0) or 0
        now = datetime.now()
        expires_at = now + timedelta(seconds=SPAWN_TIMEOUT * 2)  # Divine uchun 30 daqiqa
        active_spawns[group_id] = {
            "waifu_id": waifu_id,
            "waifu_name": waifu_name,
            "file_id": file_id,
            "rarity": "Divine",
            "anime": anime,
            "price": price,
            "expires_at": expires_at,
            "coin_multiplier": 1.0,
            "is_event": False,
            "event_id": None,
        }
        await grp_db.set_spawn_state(group_id, waifu_id, now, expires_at)
        asyncio.create_task(expire_spawn(context, group_id, SPAWN_TIMEOUT * 2))

        price_line = f"\n💰 Narx: <b>{price:,}</b> coin" if price else ""
        stk = get_catch_sticker("Divine")
        await send_stk(context.bot, group_id, stk)
        await context.bot.send_photo(
            chat_id=group_id,
            photo=file_id,
            caption=(
                f"🌟 <b>DIVINE WAIFU PAYDO BO'LDI!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✨ <b>DIVINE</b> ✨\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Bu nadir waifu 10 ta Exclusive tutilgandan keyin paydo bo'ldi!\n"
                f"Ismini bilasizmi? <code>/waifu [ism]</code> deb yozing!\n"
                f"⏰ <b>30 daqiqa</b> vaqt!{price_line}"
            ),
            parse_mode="HTML"
        )
        # Counter ni reset qilish
        await event_db.reset_divine_counter(group_id)
    except Exception as e:
        print(f"_do_divine_spawn error [{group_id}]:", e)


async def handle_message_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return
    group_id = chat.id
    user = update.effective_user
    if not user or user.is_bot:
        return

    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    try:
        bot_member = await context.bot.get_chat_member(group_id, context.bot.id)
        if bot_member.status not in ("administrator", "creator"):
            return
    except Exception:
        return

    from middlewares.flood import check_flood
    is_flooded = await check_flood(user.id, group_id, context)
    if is_flooded:
        return

    # Normal spawn
    threshold = await grp_db.get_spawn_threshold(group_id)
    count = await grp_db.increment_message_count(group_id)
    if count >= threshold and group_id not in active_spawns:
        await grp_db.reset_message_count(group_id)
        await _do_spawn(context, group_id)

    # Event spawn — faqat bot asosiy guruhida
    bot_group_id = get_bot_group_id()
    if bot_group_id and group_id == bot_group_id:
        active_ev = await event_db.get_active_event()
        if active_ev and active_ev.get('waifu_count', 0) > 0:
            ev_count = await event_db.increment_event_message_count(group_id)
            if ev_count >= active_ev['trigger_every']:
                await event_db.reset_event_message_count(group_id)
                # Event spawn alohida kanal yoki guruh sifatida, normal spawndan keyin
                await asyncio.sleep(1)
                ev_group_key = f"ev_{group_id}"
                if ev_group_key not in active_spawns:
                    await _do_spawn(context, group_id, is_event=True, active_event=active_ev)


async def cmd_waifu_catch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Bu komanda faqat guruhda ishlaydi!")
        return
    group_id = chat.id
    user = update.effective_user
    if not user:
        return

    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    if group_id not in active_spawns:
        await update.message.reply_text("🎴 Hozir hech qanday waifu yo'q!")
        return

    if not context.args:
        spawn = active_spawns.get(group_id, {})
        emoji = get_rarity_emoji(spawn.get("rarity", "Common"))
        ev_badge = " ⚡ EVENT" if spawn.get("is_event") else ""
        await update.message.reply_text(
            f"❓ Format: <code>/waifu [ism]</code>\nMisol: <code>/waifu Mikasa</code>\n\n"
            f"{emoji} Rarity: <b>{spawn.get('rarity', '?')}</b>{ev_badge} | Anime: {spawn.get('anime', '?')}",
            parse_mode="HTML"
        )
        return

    spawn = active_spawns.get(group_id)
    if not spawn:
        await update.message.reply_text("🎴 Hozir hech qanday waifu yo'q!")
        return

    if datetime.now() > spawn["expires_at"]:
        active_spawns.pop(group_id, None)
        await update.message.reply_text("⌛ Bu waifu allaqachon yo'qolgan!")
        return

    if _is_catch_flooded(user.id):
        await update.message.reply_text(
            f"⏳ Juda tez! {CATCH_WINDOW}s ichida {CATCH_LIMIT} ta urinish mumkin."
        )
        return

    guess = " ".join(context.args)
    if not _name_matches(guess, spawn["waifu_name"]):
        await update.message.reply_text("❌ Noto'g'ri! Yana urinib ko'ring 🤔")
        return

    caught_spawn = active_spawns.pop(group_id, None)
    if not caught_spawn:
        return

    await grp_db.clear_spawn_state(group_id)

    # Catch jarayoni
    rarity = caught_spawn["rarity"]
    coin_reward = int(get_coin_reward(rarity) * caught_spawn.get("coin_multiplier", 1.0))
    emoji = get_rarity_emoji(rarity)
    display_name = user.full_name or user.username or "Noma'lum"
    mention = f'<a href="tg://user?id={user.id}">{display_name}</a>'

    is_event_catch = caught_spawn.get("is_event", False)

    # Event waifu yoki oddiy waifu
    if is_event_catch:
        # Event waifuni collection ga qo'shish (event_waifus jadvalidan)
        await col_db.add_to_collection(user.id, caught_spawn["waifu_id"])
        await user_db.add_coins(user.id, coin_reward)
        await user_db.update_total_caught(user.id)
        ev_badge = "⚡ <b>EVENT</b> "
    else:
        waifu = await waifu_db.get_waifu(caught_spawn["waifu_id"])
        if not waifu:
            await update.message.reply_text("❌ Xatolik yuz berdi.")
            return
        await col_db.add_to_collection(user.id, caught_spawn["waifu_id"])
        await user_db.add_coins(user.id, coin_reward)
        await user_db.update_total_caught(user.id)
        ev_badge = ""

        # Exclusive tutilganda divine counter oshadi
        if rarity == "Exclusive":
            divine_count = await event_db.increment_divine_counter(group_id)
            if divine_count >= 10:
                # Divine spawn!
                await update.message.reply_text(
                    f"🎉 {mention} Exclusive waifuni tutdi!\n"
                    f"🌟 Guruhda 10 ta Exclusive tutildi — DIVINE waifu paydo bo'lmoqda!",
                    parse_mode="HTML"
                )
                await asyncio.sleep(2)
                await _do_divine_spawn(context, group_id)

    price = caught_spawn.get("price", 0) or 0
    price_line = f"\n💰 Narx: <b>{price:,}</b> coin" if price else ""

    await log_db.add_log("catch", user_id=user.id,
                         details=f"waifu_id={caught_spawn['waifu_id']} rarity={rarity} event={is_event_catch}",
                         group_id=group_id)
    await update.message.reply_text(
        f"🎉 {mention} waifuni qo'lga kiritdi!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{ev_badge}{emoji} <b>{caught_spawn['waifu_name']}</b>\n"
        f"🎌 {caught_spawn['anime']} • ⭐ {rarity}\n"
        f"🆔 <code>#{caught_spawn['waifu_id']}</code>{price_line}\n"
        f"💰 +{coin_reward:,} coin\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )
    stk = get_catch_sticker(rarity)
    await send_stk(context.bot, group_id, stk)


async def force_spawn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin uchun majburiy spawn"""
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Faqat guruhda!")
        return
    group_id = chat.id
    if group_id in active_spawns:
        await update.message.reply_text("⚠️ Guruhda allaqachon aktiv waifu bor!")
        return
    await grp_db.reset_message_count(group_id)
    await _do_spawn(context, group_id)
