"""
Emergency Mode middleware.
Aktiv bo'lsa, barcha user buyruqlari blokirovka qilinadi.
Adminlar esa ishlashda davom etadi.
"""
from telegram import Update
from telegram.ext import ContextTypes
from database.db import get_setting


async def emergency_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    True qaytarsa — normal ishlash.
    False qaytarsa — emergency mode, buyruq blokirovka.
    """
    from database import logs as log_db
    user = update.effective_user
    if not user:
        return False

    mode = await get_setting("emergency_mode", "0")
    if mode != "1":
        return True  # Normal rejim

    # Admin bo'lsa — o'tkazib yuborish
    if await log_db.is_admin(user.id):
        return True

    # User buyrug'i bo'lsa — blokirovka
    if update.message and update.message.text:
        text = update.message.text.strip()
        if text.startswith("/"):
            try:
                await update.message.reply_text(
                    "🚨 <b>BOT TEXNIK ISHLAR UCHUN TO'XTATILGAN</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "⚙️ Hozirda bot sozlanish rejimida.\n"
                    "⏰ Tez orada ishga tushadi.\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "📢 Yangiliklar uchun kuting!",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            return False

    return False


async def is_emergency_active() -> bool:
    mode = await get_setting("emergency_mode", "0")
    return mode == "1"
