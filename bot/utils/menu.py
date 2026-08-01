"""
Asosiy menyu klaviaturasi va tugma handlerlari (private chat uchun)
"""
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

# ── Menyu tugmalari ───────────────────────────────────────────
MENU_KEYBOARD = [
    ["🎁 Kunlik bonus",   "📦 Sandiqlar"],
    ["🛍 Do'kon",         "📦 Admin savdo"],
    ["👥 Referal",        "🏆 Haftalik reyting"],
    ["🏪 Bozor",          "🏪 Bozorim"],
]

# Barcha tugmalar to'plami (tez tekshirish uchun)
MENU_BUTTON_TEXTS = {btn for row in MENU_KEYBOARD for btn in row}


def get_main_menu() -> ReplyKeyboardMarkup:
    """Doimiy ReplyKeyboard qaytaradi."""
    return ReplyKeyboardMarkup(
        MENU_KEYBOARD,
        resize_keyboard=True,
        is_persistent=True,
    )


async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Xabar menyu tugmasi bo'lsa ishlaydi.
    True qaytaradi — boshqa handlerga o'tmaslik uchun.
    False — oddiy xabar, keyingi handlerga o'tsin.
    """
    text = update.message.text if update.message else None
    if not text or text not in MENU_BUTTON_TEXTS:
        return False

    if text == "🎁 Kunlik bonus":
        from handlers.user_commands import cmd_daily
        await cmd_daily(update, context)

    elif text == "📦 Sandiqlar":
        from handlers.extra_commands import cmd_sandiq
        await cmd_sandiq(update, context)

    elif text == "🛍 Do'kon":
        from handlers.extra_commands import cmd_dokon
        await cmd_dokon(update, context)

    elif text == "📦 Admin savdo":
        from handlers.market_handler import cmd_market
        await cmd_market(update, context)

    elif text == "👥 Referal":
        await _cmd_referal(update, context)

    elif text == "🏆 Haftalik reyting":
        from handlers.user_commands import cmd_top
        await cmd_top(update, context)

    elif text == "🏪 Bozor":
        from handlers.market_handler import cmd_market
        await cmd_market(update, context)

    elif text == "🏪 Bozorim":
        await _cmd_bozorim(update, context)

    return True


# ── Referal ───────────────────────────────────────────────────
async def _cmd_referal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
    except Exception:
        bot_username = "bot"
    link = f"https://t.me/{bot_username}?start=ref_{user.id}"
    await update.message.reply_text(
        f"👥 <b>REFERAL TIZIMI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Sizning havolangiz:\n"
        f"<code>{link}</code>\n\n"
        f"💡 Do'stingiz shu havola orqali botga kirsa,\n"
        f"ikkalangiz ham bonus olasiz!",
        parse_mode="HTML",
        reply_markup=get_main_menu(),
    )


# ── Bozorim (shaxsiy e'lonlar) ────────────────────────────────
async def _cmd_bozorim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import users as user_db
    from database.db import get_pool
    from utils.helpers import get_rarity_emoji

    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT m.id, m.collection_id, m.waifu_id, m.price, "
            "w.name, w.anime, w.rarity "
            "FROM market m "
            "JOIN waifus w ON m.waifu_id = w.waifu_id "
            "WHERE m.seller_id=$1 AND m.status='active' "
            "ORDER BY m.listed_at DESC LIMIT 15",
            user.id,
        )

    if not rows:
        await update.message.reply_text(
            "🏪 <b>MENING BOZORIM</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📭 Hozirda bozorda hech narsingiz yo'q.\n\n"
            "💡 Waifu sotish: <code>/sell [ID] [narx]</code>",
            parse_mode="HTML",
            reply_markup=get_main_menu(),
        )
        return

    lines = [f"🏪 <b>MENING BOZORIM</b> ({len(rows)} ta)\n━━━━━━━━━━━━━━━━━━━━"]
    for r in rows:
        emoji = get_rarity_emoji(r["rarity"])
        lines.append(
            f"{emoji} <b>{r['name']}</b> — {r['anime']}\n"
            f"   💰 <b>{r['price']:,}</b> coin  |  🆔 <code>#{r['id']}</code>\n"
            f"   ❌ Bekor: <code>/cancel {r['id']}</code>"
        )
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    await update.message.reply_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=get_main_menu()
    )
