"""
Admin va Sudo buyruqlari:
/wsend, /list, /groups, /ping, /plus, /upload, /delete, /update,
/givewayfu, /givevaluta, /startkonkurs, /stopkonkurs, /stopreferal,
/auksion, /top_event, /stats_full

Emergency Mode: admin panel orqali boshqariladi.
"""
import time
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import users as user_db
from database import collections as col_db
from database import waifus as waifu_db
from database import groups as grp_db
from database import logs as log_db
from database.db import get_pool, get_setting, set_setting
from utils.helpers import get_rarity_emoji, is_god_admin, RARITY_ORDER


async def require_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    u = update.effective_user
    if not await log_db.is_admin(u.id):
        if update.message:
            await update.message.reply_text("❌ Ruxsatingiz yo'q. Faqat adminlar uchun.")
        return False
    return True


async def require_full_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    u = update.effective_user
    if not await log_db.is_full_admin(u.id):
        if update.message:
            await update.message.reply_text("❌ Faqat to'liq admin.")
        return False
    return True


async def require_god(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    u = update.effective_user
    if not is_god_admin(u.id):
        if update.message:
            await update.message.reply_text("❌ Faqat ega (god admin) uchun.")
        return False
    return True


# ═══════════════════════════════════════
# /wsend — foydalanuvchiga valuta yuborish
# ═══════════════════════════════════════
async def cmd_wsend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "💸 <b>VALUTA YUBORISH</b>\n"
            "Ishlatish: /wsend [user_id] [miqdor]\n"
            "Misol: /wsend 123456789 500",
            parse_mode="HTML"
        )
        return
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ User ID va miqdor raqam bo'lishi kerak!")
        return

    if amount <= 0:
        await update.message.reply_text("❌ Miqdor musbat bo'lishi kerak!")
        return

    target = await user_db.get_user(target_id)
    if not target:
        await update.message.reply_text(f"❌ {target_id} ID foydalanuvchi topilmadi!")
        return

    await user_db.add_coins(target_id, amount)
    await log_db.add_log("wsend", user_id=update.effective_user.id,
                         details=f"to={target_id} amount={amount}")
    name = target.get("full_name") or target.get("username") or str(target_id)
    await update.message.reply_text(
        f"✅ <b>Valuta yuborildi!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {name}\n"
        f"💰 <b>{amount:,}</b> coin qo'shildi",
        parse_mode="HTML"
    )

    try:
        await context.bot.send_message(
            target_id,
            f"💰 <b>Admin sizga coin yubordi!</b>\n"
            f"💵 <b>+{amount:,}</b> coin",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ═══════════════════════════════════════
# /list — foydalanuvchilar ro'yxati
# ═══════════════════════════════════════
async def cmd_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, username, full_name, total_caught, coins, is_banned "
            "FROM users ORDER BY total_caught DESC LIMIT 30"
        )

    if not rows:
        await update.message.reply_text("📋 Foydalanuvchilar yo'q.")
        return

    total_count = await conn.fetchval("SELECT COUNT(*) FROM users") if False else len(rows)
    pool2 = await get_pool()
    async with pool2.acquire() as conn:
        total_count = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
        banned_count = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_banned=1") or 0

    lines = [
        f"👥 <b>FOYDALANUVCHILAR RO'YXATI</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📊 Jami: <b>{total_count}</b> | 🚫 Banlangan: <b>{banned_count}</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
    ]
    for r in rows[:20]:
        name = r["full_name"] or r["username"] or str(r["user_id"])
        banned = " 🚫" if r["is_banned"] else ""
        lines.append(f"• <code>{r['user_id']}</code> {name}{banned} — {r['total_caught']} 🎴")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════
# /groups — guruhlar ro'yxati
# ═══════════════════════════════════════
async def cmd_list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT g.group_id, g.group_name, g.added_at, "
            "gs.spawn_interval, "
            "COUNT(DISTINCT gm.user_id) as members "
            "FROM allowed_groups g "
            "LEFT JOIN group_settings gs ON gs.group_id=g.group_id "
            "LEFT JOIN group_members gm ON gm.group_id=g.group_id "
            "GROUP BY g.group_id, g.group_name, g.added_at, gs.spawn_interval "
            "ORDER BY members DESC LIMIT 20"
        )

    if not rows:
        await update.message.reply_text("📋 Guruhlar yo'q.")
        return

    lines = ["🏘 <b>GURUHLAR RO'YXATI</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for r in rows:
        name = r["group_name"] or str(r["group_id"])
        interval = r["spawn_interval"] or 100
        lines.append(
            f"• <b>{name}</b>\n"
            f"  🆔 <code>{r['group_id']}</code> | 👥 {r['members']} | ⏰ {interval}x"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════
# /ping — bot tezligini tekshirish
# ═══════════════════════════════════════
async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    start = time.monotonic()
    msg = await update.message.reply_text("🏓 Ping...")
    elapsed = (time.monotonic() - start) * 1000

    pool = await get_pool()
    db_start = time.monotonic()
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
    db_elapsed = (time.monotonic() - db_start) * 1000

    await msg.edit_text(
        f"🏓 <b>PONG!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 Bot: <b>{elapsed:.0f}ms</b>\n"
        f"🗄 DB: <b>{db_elapsed:.0f}ms</b>",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /plus — waifu qo'shish (alias)
# /upload — waifu qo'shish (alias)
# ═══════════════════════════════════════
async def cmd_plus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    from handlers.admin import cmd_addwaifu_cmd
    await cmd_addwaifu_cmd(update, context)


async def cmd_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    from handlers.admin import cmd_addwaifu_cmd
    await cmd_addwaifu_cmd(update, context)


# ═══════════════════════════════════════
# /delete — waifu o'chirish
# ═══════════════════════════════════════
async def cmd_delete_waifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text(
            "🗑 <b>WAIFU O'CHIRISH</b>\n"
            "Ishlatish: /delete [waifu_id]\n"
            "Misol: /delete CM-123456",
            parse_mode="HTML"
        )
        return
    wid = context.args[0]
    waifu = await waifu_db.get_waifu_by_id(wid)
    if not waifu:
        await update.message.reply_text(f"❌ {wid} ID waifu topilmadi!")
        return
    await waifu_db.remove_waifu(wid)
    await log_db.add_log("delete_waifu", user_id=update.effective_user.id, details=f"waifu_id={wid}")
    emoji = get_rarity_emoji(waifu["rarity"])
    await update.message.reply_text(
        f"✅ Waifu o'chirildi!\n"
        f"{emoji} <b>{waifu['name']}</b> | {waifu['rarity']}",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /update — waifu yangilash
# ═══════════════════════════════════════
async def cmd_update_waifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if len(context.args) < 3:
        await update.message.reply_text(
            "✏️ <b>WAIFU YANGILASH</b>\n"
            "Ishlatish: /update [waifu_id] [maydon] [yangi_qiymat]\n"
            "Maydonlar: name, anime, rarity, price\n"
            "Misol: /update CM-123456 name Sakura",
            parse_mode="HTML"
        )
        return
    wid = context.args[0]
    field = context.args[1].lower()
    value = " ".join(context.args[2:])
    allowed_fields = {"name", "anime", "rarity", "price"}
    if field not in allowed_fields:
        await update.message.reply_text(f"❌ Ruxsat etilgan maydonlar: {', '.join(allowed_fields)}")
        return
    waifu = await waifu_db.get_waifu_by_id(wid)
    if not waifu:
        await update.message.reply_text(f"❌ {wid} topilmadi!")
        return
    if field == "price":
        try:
            value = int(value)
        except ValueError:
            await update.message.reply_text("❌ Price raqam bo'lishi kerak!")
            return
    ok = await waifu_db.update_waifu(wid, {field: value})
    if ok:
        await log_db.add_log("update_waifu", user_id=update.effective_user.id,
                             details=f"waifu_id={wid} field={field}")
        await update.message.reply_text(
            f"✅ Waifu yangilandi!\n"
            f"🆔 {wid}: <b>{field}</b> = <code>{value}</code>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ Yangilashda xatolik!")


# ═══════════════════════════════════════
# /givewayfu — guruhga waifu berish (ega)
# ═══════════════════════════════════════
async def cmd_givewayfu_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Bu buyruq guruhda ishlaydi!")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        members = await conn.fetch("SELECT user_id FROM group_members WHERE group_id=$1", chat.id)

    if not members:
        await update.message.reply_text("❌ Guruh a'zolari topilmadi.")
        return

    rarity = " ".join(context.args) if context.args else None
    count = 0
    for m in members:
        waifu = await waifu_db.get_random_waifu(rarity) if rarity else await waifu_db.get_random_waifu_by_rarity_weight()
        if waifu:
            await col_db.add_to_collection(m["user_id"], waifu["waifu_id"])
            count += 1
            try:
                emoji = get_rarity_emoji(waifu["rarity"])
                await context.bot.send_message(
                    m["user_id"],
                    f"🎁 <b>Admin sizga waifu berdi!</b>\n"
                    f"{emoji} <b>{waifu['name']}</b> | {waifu['rarity']}",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    await update.message.reply_text(
        f"✅ <b>{count}</b> ta a'zoga waifu berildi!",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /givevaluta — guruhga valuta berish (ega)
# ═══════════════════════════════════════
async def cmd_givevaluta_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Bu buyruq guruhda ishlaydi!")
        return

    if not context.args:
        await update.message.reply_text("Ishlatish: /givevaluta [miqdor]")
        return

    try:
        amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Miqdor raqam bo'lishi kerak!")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        members = await conn.fetch("SELECT user_id FROM group_members WHERE group_id=$1", chat.id)

    count = 0
    for m in members:
        await user_db.add_coins(m["user_id"], amount)
        count += 1
        try:
            await context.bot.send_message(
                m["user_id"],
                f"💰 <b>Admin sizga coin berdi!</b>\n"
                f"💵 <b>+{amount:,}</b> coin",
                parse_mode="HTML"
            )
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ <b>{count}</b> ta a'zoga <b>{amount:,}</b> coin berildi!",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /startkonkurs — konkurs boshlash
# ═══════════════════════════════════════
async def cmd_startkonkurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    chat = update.effective_chat

    if len(context.args) < 2:
        await update.message.reply_text(
            "🏆 <b>KONKURS BOSHLASH</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Ishlatish: /startkonkurs [nomi] [soat]\n"
            "Misol: /startkonkurs WaifuKing 24\n\n"
            "💡 Eng ko'p waifu tutgan g'olib bo'ladi!",
            parse_mode="HTML"
        )
        return

    title = context.args[0]
    try:
        hours = int(context.args[1])
    except (ValueError, IndexError):
        hours = 24

    end_time = datetime.now() + timedelta(hours=hours)
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Oldingi aktiv konkursni o'chirish
        await conn.execute("UPDATE contest SET is_active=0 WHERE group_id=$1 AND is_active=1", chat.id)
        cid = await conn.fetchval(
            "INSERT INTO contest (group_id, title, end_time, is_active, created_by) "
            "VALUES ($1,$2,$3,1,$4) RETURNING id",
            chat.id, title, end_time, update.effective_user.id
        )

    await update.message.reply_text(
        f"🏆 <b>KONKURS BOSHLANDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 Nomi: <b>{title}</b>\n"
        f"⏰ Davomiyligi: <b>{hours}</b> soat\n"
        f"📅 Tugash vaqti: <b>{end_time.strftime('%d.%m.%Y %H:%M')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Eng ko'p waifu tutgan g'olib bo'ladi!\n"
        f"🆔 Konkurs ID: <code>{cid}</code>",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /stopkonkurs — konkursni to'xtatish
# ═══════════════════════════════════════
async def cmd_stopkonkurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    chat = update.effective_chat
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM contest WHERE group_id=$1 AND is_active=1", chat.id
        )
        if not row:
            await update.message.reply_text("❌ Aktiv konkurs topilmadi!")
            return

        # G'olibni topish
        winner = await conn.fetchrow(
            "SELECT u.user_id, u.full_name, u.username, u.total_caught "
            "FROM users u "
            "JOIN group_members gm ON gm.user_id=u.user_id "
            "WHERE gm.group_id=$1 "
            "ORDER BY u.total_caught DESC LIMIT 1",
            chat.id
        )

        await conn.execute("UPDATE contest SET is_active=0 WHERE id=$1", row["id"])

    winner_text = ""
    if winner:
        name = winner["full_name"] or winner["username"] or str(winner["user_id"])
        winner_text = f"\n🏆 <b>G'olib: {name}</b> — {winner['total_caught']} waifu"

    await update.message.reply_text(
        f"🔴 <b>KONKURS YAKUNLANDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 {row['title']}{winner_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎉 Barcha ishtirokchilarga rahmat!",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /stopreferal — referal yo'nalishini bekor qilish
# ═══════════════════════════════════════
async def cmd_stopreferal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    await set_setting("referral_active", "0")
    await update.message.reply_text(
        "🚫 <b>Referal tizimi o'chirildi!</b>\n"
        "Yangi referal havolalar ishlamaydi.",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /auksion — waifu auksion (ega)
# ═══════════════════════════════════════
async def cmd_auksion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    chat = update.effective_chat

    if not context.args:
        await update.message.reply_text(
            "🏛 <b>WAIFU AUKSION</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Ishlatish: /auksion [waifu_id] [boshlang'ich narx] [daqiqa]\n"
            "Misol: /auksion LG-123456 1000 30",
            parse_mode="HTML"
        )
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Waifu ID va boshlang'ich narxni kiriting!")
        return

    waid = context.args[0]
    try:
        start_price = int(context.args[1])
        duration_min = int(context.args[2]) if len(context.args) > 2 else 30
    except ValueError:
        await update.message.reply_text("❌ Narx va davomiylik raqam bo'lishi kerak!")
        return

    waifu = await waifu_db.get_waifu_by_id(waid)
    if not waifu:
        await update.message.reply_text(f"❌ {waid} waifu topilmadi!")
        return

    emoji = get_rarity_emoji(waifu["rarity"])
    end_time = datetime.now() + timedelta(minutes=duration_min)

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"💰 Taklif berish (+100)", callback_data=f"auction_bid_{waid}_{start_price}"),
    ]])

    await update.message.reply_photo(
        photo=waifu["file_id"],
        caption=f"🏛 <b>WAIFU AUKSION BOSHLANDI!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{emoji} <b>{waifu['name']}</b>\n"
                f"🎌 {waifu['anime']} | {waifu['rarity']}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 Boshlang'ich narx: <b>{start_price:,}</b> coin\n"
                f"⏰ Davomiyligi: <b>{duration_min}</b> daqiqa\n"
                f"📅 Tugash: <b>{end_time.strftime('%H:%M')}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 Taklif berish uchun tugmani bosing!",
        parse_mode="HTML",
        reply_markup=kb
    )


# ═══════════════════════════════════════
# /top_event — event reytingi
# ═══════════════════════════════════════
async def cmd_top_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Aktiv event waifularini tutganlar
        rows = await conn.fetch(
            "SELECT u.user_id, u.full_name, u.username, COUNT(c.id) as event_count "
            "FROM collections c "
            "JOIN event_waifus ew ON c.waifu_id=ew.id::text "
            "JOIN users u ON u.user_id=c.user_id "
            "GROUP BY u.user_id, u.full_name, u.username "
            "ORDER BY event_count DESC LIMIT 10"
        )

    if not rows:
        await update.message.reply_text("📊 Event reytingi bo'sh.")
        return

    lines = ["🎉 <b>EVENT REYTINGI</b>\n━━━━━━━━━━━━━━━━━━━━"]
    medals = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = r["full_name"] or r["username"] or str(r["user_id"])
        lines.append(f"{medal} <b>{name}</b>: {r['event_count']} event waifu")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════
# /stats_full — to'liq statistika
# ═══════════════════════════════════════
async def cmd_stats_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        users_total = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
        users_active = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_banned=0") or 0
        waifus_total = await conn.fetchval("SELECT COUNT(*) FROM waifus WHERE is_active=1") or 0
        collections_total = await conn.fetchval("SELECT COUNT(*) FROM collections") or 0
        trades_total = await conn.fetchval("SELECT COUNT(*) FROM trades") or 0
        groups_total = await conn.fetchval("SELECT COUNT(*) FROM allowed_groups") or 0
        market_active = await conn.fetchval("SELECT COUNT(*) FROM market WHERE status='active'") or 0
        coins_total = await conn.fetchval("SELECT COALESCE(SUM(coins),0) FROM users") or 0
        em_mode = await conn.fetchval("SELECT value FROM bot_settings WHERE key='emergency_mode'") or "0"

    em_status = "🟢 Normal" if em_mode != "1" else "🔴 Emergency"
    await update.message.reply_text(
        f"📊 <b>BOT TO'LIQ STATISTIKASI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Foydalanuvchilar: <b>{users_total}</b>\n"
        f"✅ Aktiv: <b>{users_active}</b>\n"
        f"🎴 Waifular: <b>{waifus_total}</b>\n"
        f"🃏 Kolleksiyalar: <b>{collections_total}</b>\n"
        f"🔄 Tradelar: <b>{trades_total}</b>\n"
        f"🏘 Guruhlar: <b>{groups_total}</b>\n"
        f"🛒 Bozor: <b>{market_active}</b> aktiv\n"
        f"💰 Jami coinlar: <b>{coins_total:,}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Bot holati: {em_status}",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# Emergency Mode toggle (panel tugmasi orqali chaqiriladi)
# ═══════════════════════════════════════
async def toggle_emergency_mode(update, context, query=None):
    """Emergency rejimini yoqish/o'chirish va barcha guruhlarga xabar yuborish."""
    current = await get_setting("emergency_mode", "0")
    new_mode = "0" if current == "1" else "1"
    await set_setting("emergency_mode", new_mode)

    pool = await get_pool()
    async with pool.acquire() as conn:
        groups = await conn.fetch("SELECT group_id FROM allowed_groups")

    if new_mode == "1":
        msg_text = (
            "🚨 <b>TEXNIK ISHLAR</b> 🚨\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚙️ Bot hozirda texnik ishlar uchun to'xtatilgan.\n"
            "⏰ Tez orada ishga tushadi.\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📢 Sabr uchun rahmat!"
        )
        status_text = "🔴 <b>EMERGENCY MODE YOQILDI!</b>\nBarcha guruhlarga xabar yuborildi."
    else:
        msg_text = (
            "✅ <b>BOT ISHGA TUSHDI!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎴 Waifu Catch Bot yana ishlamoqda!\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎮 Hamma buyruqlar aktiv!"
        )
        status_text = "🟢 <b>EMERGENCY MODE O'CHIRILDI!</b>\nBarcha guruhlarga xabar yuborildi."

    sent = 0
    for g in groups:
        try:
            await context.bot.send_message(g["group_id"], msg_text, parse_mode="HTML")
            sent += 1
        except Exception:
            pass

    status_text += f"\n📤 {sent} ta guruhga xabar yuborildi."
    if query:
        try:
            await query.edit_message_text(status_text, parse_mode="HTML")
        except Exception:
            if update.effective_message:
                await update.effective_message.reply_text(status_text, parse_mode="HTML")
    elif update.effective_message:
        await update.effective_message.reply_text(status_text, parse_mode="HTML")
