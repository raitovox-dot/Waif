import os
import re
import sys
import logging

sys.path.insert(0, os.path.dirname(__file__))

from telegram import Update, BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    InlineQueryHandler, filters, ChatMemberHandler
)

from database.db import init_db
from database import logs as log_db
from database.events import get_active_event
from handlers.spawn import handle_message_count, cmd_waifu_catch, restore_active_spawns
from handlers.gallery import cmd_collection_gallery, handle_gallery_callback
from handlers.inline_handler import handle_inline_query
from handlers.user_commands import (
    cmd_start, cmd_help, cmd_profil,
    cmd_daily, cmd_top, cmd_gtop, cmd_search, cmd_anime, cmd_stats,
    cmd_favorite, cmd_history
)
from handlers.trade import cmd_trade, handle_trade_callback
from handlers.gift import cmd_gift, handle_gift_callback
from handlers.market_handler import cmd_sell, cmd_market, cmd_buy, handle_shop_callback
from handlers.admin import (
    cmd_removewaifu, cmd_addwaifu_cmd, cmd_spawn_admin, cmd_broadcast,
    cmd_addadmin, cmd_addsubadmin, cmd_removeadmin, cmd_ban_user, cmd_unban_user,
    cmd_givecoins, cmd_givewaifu, cmd_event, cmd_approvegroup, cmd_denygroup,
    cmd_addchannel, cmd_removechannel, cmd_panel, cmd_setspawn,
    cmd_addgroup_bypass, cmd_admins,
    handle_panel_button, handle_admin_input, handle_admin_photo, handle_admin_callback,
    ALL_PANEL_BUTTONS,
    cmd_settitle, cmd_removetitle, cmd_titles
)
from handlers.group_management import handle_new_chat_member, handle_chat_member
from handlers.duplicate import cmd_duplicate, handle_dup_callback
from middlewares.moderation import cmd_warn, cmd_mute, cmd_unmute, cmd_kick, cmd_ban, cmd_unban
from middlewares.subscription import handle_subscription_check
from middlewares.ban_middleware import ban_check_middleware

# ── Yangi qo'shimcha buyruqlar ──
from handlers.extra_commands import (
    cmd_claim, cmd_harem, cmd_profile, cmd_bozor, cmd_dokon, cmd_wdublikat,
    cmd_wpocket, cmd_ball, cmd_sandiq, cmd_guess, cmd_guess_stop,
    cmd_bonus, cmd_redeem, cmd_whmode, cmd_w, cmd_lucky,
    cmd_inventory, cmd_wrarity, cmd_top_valyuta, cmd_ctop, cmd_topgroups,
    cmd_owners, cmd_changetime, cmd_resetfav,
    handle_guess_message,
)
from handlers.admin_extra import (
    cmd_wsend, cmd_list_users, cmd_list_groups, cmd_ping,
    cmd_plus, cmd_upload, cmd_delete_waifu, cmd_update_waifu,
    cmd_givewayfu_group, cmd_givevaluta_group,
    cmd_startkonkurs, cmd_stopkonkurs, cmd_stopreferal,
    cmd_auksion, cmd_top_event, cmd_stats_full,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════
# Bot buyruqlari ro'yxati
# ════════════════════════════════════════
GROUP_COMMANDS = [
    BotCommand('waifu', '🎴 Waifu tutish'),
    BotCommand('harem', '📚 Haremingizni ko\'rish'),
    BotCommand('collection', '📚 Kolleksiyangiz'),
    BotCommand('profil', '👤 Profilingiz'),
    BotCommand('profile', '👤 Profil kartangiz'),
    BotCommand('claim', '🎁 Kunlik bepul wayfu olish'),
    BotCommand('daily', '🎁 Kunlik mukofot'),
    BotCommand('top', '🏆 Global eng yaxshilar'),
    BotCommand('ctop', '👑 Guruhdagi eng yaxshilar'),
    BotCommand('top_valyuta', '💰 Eng ko\'p valuta egalari'),
    BotCommand('topgroups', '🌍 Eng yaxshi guruhlar'),
    BotCommand('gtop', '🏅 Guruh reytingi'),
    BotCommand('trade', '🔄 Wayfu almashish'),
    BotCommand('gift', '🎁 Wayfu sovg\'a qilish'),
    BotCommand('sell', '💰 Wayfu sotish'),
    BotCommand('bozor', '🏪 Foydalanuvchilar bozori'),
    BotCommand('dokon', '🛍 Wayfu do\'koni'),
    BotCommand('market', '🛒 Bugungi do\'kon'),
    BotCommand('buy', '🛒 Do\'kondan sotib olish'),
    BotCommand('ball', '🎱 Sharlar bilan wayfu yutish'),
    BotCommand('sandiq', '📦 Pullik sandiqlar'),
    BotCommand('guess', '🎯 Wayfu nomini topish'),
    BotCommand('fav', '⭐ Sevimli wayfu qo\'shish'),
    BotCommand('favorite', '⭐ Sevimli belgilash'),
    BotCommand('resetfav', '🔄 Sevimli tiklash'),
    BotCommand('wpocket', '💰 Valyuta balansingiz'),
    BotCommand('search', '🔍 Wayfu qidirish'),
    BotCommand('w', '🆔 Wayfu haqida ma\'lumot'),
    BotCommand('inventory', '📦 To\'plam statistikasi'),
    BotCommand('wrarity', '💎 Rarity bo\'yicha to\'plam'),
    BotCommand('wdublikat', '📋 Dublikat wayfular ro\'yxati'),
    BotCommand('duplicate', '🃏 Duplicate kartalar'),
    BotCommand('lucky', '🍀 Tasodifiy wayfu'),
    BotCommand('bonus', '🎁 Yangi foydalanuvchi bonusi'),
    BotCommand('redeem', '🎫 Kodni ishlatish'),
    BotCommand('owners', '👑 Wayfu qayerda borligini ko\'rish'),
    BotCommand('whmode', '🔀 Harem ko\'rinishini almashtirish'),
    BotCommand('changetime', '⏰ Chiqish vaqtini o\'zgartirish'),
    BotCommand('help', '📋 Yordam'),
]

PRIVATE_COMMANDS = [
    BotCommand('start', '🌸 Botni ishga tushirish'),
    BotCommand('profil', '👤 Profilingiz'),
    BotCommand('profile', '👤 Profil kartangiz'),
    BotCommand('harem', '📚 Haremingizni ko\'rish'),
    BotCommand('collection', '📚 Kolleksiyangiz'),
    BotCommand('claim', '🎁 Kunlik bepul wayfu olish'),
    BotCommand('daily', '🎁 Kunlik mukofot'),
    BotCommand('bonus', '🎁 Yangi foydalanuvchi bonusi'),
    BotCommand('wpocket', '💰 Valyuta balansingiz'),
    BotCommand('top', '🏆 Global reyting'),
    BotCommand('bozor', '🏪 Foydalanuvchilar bozori'),
    BotCommand('dokon', '🛍 Wayfu do\'koni'),
    BotCommand('market', '🛒 Bugungi do\'kon'),
    BotCommand('inventory', '📦 To\'plam statistikasi'),
    BotCommand('wrarity', '💎 Rarity bo\'yicha to\'plam'),
    BotCommand('lucky', '🍀 Tasodifiy wayfu'),
    BotCommand('redeem', '🎫 Kodni ishlatish'),
    BotCommand('search', '🔍 Wayfu qidirish'),
    BotCommand('help', '📋 Yordam'),
    BotCommand('panel', '⚙️ Admin paneli'),
]


# ════════════════════════════════════════
# Start handler (deep link support)
# ════════════════════════════════════════
async def cmd_start_handler(update: Update, context):
    args = context.args or []
    if args and args[0].startswith('col_'):
        try:
            owner_id = int(args[0][4:])
            await show_user_collection_by_id(update, context, owner_id)
            return
        except ValueError:
            pass
    if args and args[0] == 'dup':
        await cmd_duplicate(update, context)
        return
    await cmd_start(update, context)


async def show_user_collection_by_id(update, context, owner_id: int):
    from database import users as user_db, collections as col_db
    from utils.helpers import get_rarity_emoji
    owner = await user_db.get_user(owner_id)
    if not owner:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return
    items = await col_db.get_collection(owner_id, limit=50)
    if not items:
        await update.message.reply_text("📭 Kolleksiya bo'sh.")
        return
    name = owner.get('full_name') or owner.get('username') or str(owner_id)
    lines = [f"🎴 <b>{name}</b> kolleksiyasi:"]
    for it in items[:20]:
        emoji = get_rarity_emoji(it['rarity'])
        fav = "⭐" if it.get('is_favorite') else ""
        lines.append(f"{emoji}{fav} {it['name']} — {it['anime']}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ════════════════════════════════════════
# Top buyrug'i (waifu/coin/ctop)
# ════════════════════════════════════════
async def cmd_top_router(update: Update, context):
    args = context.args or []
    if args and args[0].lower() in ('coin', 'coins', 'valyuta', 'money'):
        await cmd_top_valyuta(update, context)
    else:
        await cmd_top(update, context)


# ════════════════════════════════════════
# Guruh a'zolarini kuzatish
# ════════════════════════════════════════
async def track_group_member(update: Update, context):
    """Guruhda xabar yuborgan foydalanuvchini group_members ga qo'shish."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return
    if chat.type not in ("group", "supergroup"):
        return
    try:
        from database.db import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO group_members (group_id, user_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                chat.id, user.id
            )
            await conn.execute(
                "INSERT INTO allowed_groups (group_id, group_name) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                chat.id, chat.title or str(chat.id)
            )
    except Exception:
        pass


# ════════════════════════════════════════
# Emergency Mode filter
# ════════════════════════════════════════
async def emergency_filter(update: Update, context) -> bool:
    """Emergency mode aktiv bo'lsa user buyruqlarini bloklaydi."""
    from database.db import get_setting
    mode = await get_setting("emergency_mode", "0")
    if mode != "1":
        return True
    user = update.effective_user
    if not user:
        return False
    if await log_db.is_admin(user.id):
        return True
    if update.message and update.message.text and update.message.text.startswith("/"):
        try:
            await update.message.reply_text(
                "🚨 <b>BOT TEXNIK ISHLAR UCHUN TO'XTATILGAN</b>\n"
                "⚙️ Hozirda sozlanish rejimida.\n"
                "⏰ Tez orada ishga tushadi.",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return False
    return False


# ════════════════════════════════════════
# App qurish
# ════════════════════════════════════════
def build_app(token: str) -> Application:
    app = Application.builder().token(token).post_init(on_startup).build()

    # ── Ban tekshiruvi (barcha handlerlardan oldin, group=-1) ──
    app.add_handler(MessageHandler(filters.ALL, ban_check_middleware), group=-1)
    app.add_handler(CallbackQueryHandler(ban_check_middleware), group=-1)

    # ── Admin buyruqlari ──
    app.add_handler(CommandHandler('panel', cmd_panel))
    app.add_handler(CommandHandler('admin', cmd_panel))
    app.add_handler(CommandHandler('addwaifu', cmd_addwaifu_cmd))
    app.add_handler(CommandHandler('removewaifu', cmd_removewaifu))
    app.add_handler(CommandHandler('plus', cmd_plus))
    app.add_handler(CommandHandler('upload', cmd_upload))
    app.add_handler(CommandHandler('delete', cmd_delete_waifu))
    app.add_handler(CommandHandler('update', cmd_update_waifu))
    app.add_handler(CommandHandler('broadcast', cmd_broadcast))
    app.add_handler(CommandHandler('addadmin', cmd_addadmin))
    app.add_handler(CommandHandler('addsubadmin', cmd_addsubadmin))
    app.add_handler(CommandHandler('removeadmin', cmd_removeadmin))
    app.add_handler(CommandHandler('addchannel', cmd_addchannel))
    app.add_handler(CommandHandler('removechannel', cmd_removechannel))
    app.add_handler(CommandHandler('approvegroup', cmd_approvegroup))
    app.add_handler(CommandHandler('denygroup', cmd_denygroup))
    app.add_handler(CommandHandler('setspawn', cmd_setspawn))
    app.add_handler(CommandHandler('addgroup_bypass', cmd_addgroup_bypass))
    app.add_handler(CommandHandler('admins', cmd_admins))
    app.add_handler(CommandHandler('settitle', cmd_settitle))
    app.add_handler(CommandHandler('removetitle', cmd_removetitle))
    app.add_handler(CommandHandler('titles', cmd_titles))
    app.add_handler(CommandHandler('givecoins', cmd_givecoins))
    app.add_handler(CommandHandler('givewaifu', cmd_givewaifu))
    app.add_handler(CommandHandler('ban_user', cmd_ban_user))
    app.add_handler(CommandHandler('unban_user', cmd_unban_user))
    app.add_handler(CommandHandler('event', cmd_event))
    app.add_handler(CommandHandler('spawnwaifu', cmd_spawn_admin))

    # ── Yangi admin buyruqlari ──
    app.add_handler(CommandHandler('wsend', cmd_wsend))
    app.add_handler(CommandHandler('list', cmd_list_users))
    app.add_handler(CommandHandler('groups', cmd_list_groups))
    app.add_handler(CommandHandler('ping', cmd_ping))
    app.add_handler(CommandHandler('givewayfu', cmd_givewayfu_group))
    app.add_handler(CommandHandler('givevaluta', cmd_givevaluta_group))
    app.add_handler(CommandHandler('startkonkurs', cmd_startkonkurs))
    app.add_handler(CommandHandler('stopkonkurs', cmd_stopkonkurs))
    app.add_handler(CommandHandler('stopreferal', cmd_stopreferal))
    app.add_handler(CommandHandler('auksion', cmd_auksion))
    app.add_handler(CommandHandler('top_event', cmd_top_event))

    # ── Moderatsiya ──
    app.add_handler(CommandHandler('warn', cmd_warn))
    app.add_handler(CommandHandler('mute', cmd_mute))
    app.add_handler(CommandHandler('unmute', cmd_unmute))
    app.add_handler(CommandHandler('kick', cmd_kick))
    app.add_handler(CommandHandler('ban', cmd_ban))
    app.add_handler(CommandHandler('unban', cmd_unban))

    # ── Asosiy user buyruqlari ──
    app.add_handler(CommandHandler('start', cmd_start_handler))
    app.add_handler(CommandHandler('help', cmd_help))
    app.add_handler(CommandHandler('profil', cmd_profil))
    app.add_handler(CommandHandler('profile', cmd_profile))
    app.add_handler(CommandHandler('collection', cmd_collection_gallery))
    app.add_handler(CommandHandler('harem', cmd_harem))
    app.add_handler(CommandHandler('daily', cmd_daily))
    app.add_handler(CommandHandler('claim', cmd_claim))
    app.add_handler(CommandHandler('waifu', cmd_waifu_catch))
    app.add_handler(CommandHandler('top', cmd_top_router))
    app.add_handler(CommandHandler('gtop', cmd_gtop))
    app.add_handler(CommandHandler('ctop', cmd_ctop))
    app.add_handler(CommandHandler('top_valyuta', cmd_top_valyuta))
    app.add_handler(CommandHandler('topgroups', cmd_topgroups))
    app.add_handler(CommandHandler('search', cmd_search))
    app.add_handler(CommandHandler('anime', cmd_anime))
    app.add_handler(CommandHandler('stats', cmd_stats))
    app.add_handler(CommandHandler('statsadmin', cmd_stats_full))
    app.add_handler(CommandHandler('favorite', cmd_favorite))
    app.add_handler(CommandHandler('fav', cmd_favorite))
    app.add_handler(CommandHandler('history', cmd_history))
    app.add_handler(CommandHandler('trade', cmd_trade))
    app.add_handler(CommandHandler('gift', cmd_gift))
    app.add_handler(CommandHandler('sell', cmd_sell))
    app.add_handler(CommandHandler('market', cmd_market))
    app.add_handler(CommandHandler('bozor', cmd_bozor))
    app.add_handler(CommandHandler('dokon', cmd_dokon))
    app.add_handler(CommandHandler('buy', cmd_buy))
    app.add_handler(CommandHandler('duplicate', cmd_duplicate))
    app.add_handler(CommandHandler('wdublikat', cmd_wdublikat))

    # ── Yangi user buyruqlari ──
    app.add_handler(CommandHandler('ball', cmd_ball))
    app.add_handler(CommandHandler('sandiq', cmd_sandiq))
    app.add_handler(CommandHandler('guess', cmd_guess))
    app.add_handler(CommandHandler('guess_stop', cmd_guess_stop))
    app.add_handler(CommandHandler('wpocket', cmd_wpocket))
    app.add_handler(CommandHandler('bonus', cmd_bonus))
    app.add_handler(CommandHandler('redeem', cmd_redeem))
    app.add_handler(CommandHandler('whmode', cmd_whmode))
    app.add_handler(CommandHandler('w', cmd_w))
    app.add_handler(CommandHandler('lucky', cmd_lucky))
    app.add_handler(CommandHandler('inventory', cmd_inventory))
    app.add_handler(CommandHandler('wrarity', cmd_wrarity))
    app.add_handler(CommandHandler('owners', cmd_owners))
    app.add_handler(CommandHandler('changetime', cmd_changetime))
    app.add_handler(CommandHandler('resetfav', cmd_resetfav))

    # ── Callback querylar ──
    app.add_handler(CallbackQueryHandler(handle_gallery_callback, pattern=r'^gal_'))
    app.add_handler(CallbackQueryHandler(handle_trade_callback, pattern=r'^trade_'))
    app.add_handler(CallbackQueryHandler(handle_gift_callback, pattern=r'^gift_'))
    app.add_handler(CallbackQueryHandler(handle_shop_callback, pattern=r'^(shop_|buy_)'))
    app.add_handler(CallbackQueryHandler(handle_dup_callback, pattern=r'^dup_'))
    app.add_handler(CallbackQueryHandler(handle_subscription_check, pattern=r'^sub_check$'))
    app.add_handler(CallbackQueryHandler(handle_admin_callback))

    # ── Inline query ──
    app.add_handler(InlineQueryHandler(handle_inline_query))

    # ── Admin panel (Private foto, text) ──
    app.add_handler(MessageHandler(
        filters.PHOTO & filters.ChatType.PRIVATE,
        handle_admin_photo
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        _private_message_handler
    ))

    # ── Guruh xabarlari ──
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_member))
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
        _group_message_handler
    ))

    return app


async def _private_message_handler(update: Update, context):
    """Private chat text xabarlarini yo'naltirish."""
    # 1. Asosiy menyu tugmalari (Kunlik bonus, Sandiqlar, Do'kon…)
    from utils.menu import handle_menu_button
    if await handle_menu_button(update, context):
        return
    # 2. Admin panel tugmalari (➕ Waifu qo'shish, 🗑 Waifular ro'yxati…)
    #    handle_panel_button None qaytaradi, shuning uchun to'g'ridan matn tekshiramiz
    text = (update.message.text or "").strip() if update.message else ""
    if text in ALL_PANEL_BUTTONS:
        await handle_panel_button(update, context)
        return
    # 3. Boshqa text → admin holatlar uchun kirish qabul qilish
    await handle_admin_input(update, context)


async def _group_message_handler(update: Update, context):
    """Guruh xabarlarini qayta ishlash."""
    # A'zoni kuzatish
    await track_group_member(update, context)

    # Guess o'yini
    handled = await handle_guess_message(update, context)
    if handled:
        return

    # Spawn hisoblagich
    await handle_message_count(update, context)


async def on_startup(app: Application):
    """Bot ishga tushganda bajariladigan vazifalar."""
    await init_db()
    logger.info("✅ DB initialized")

    # GitHub backupdan tiklash (agar DB bo'sh bo'lsa)
    try:
        from utils.github_backup import restore_from_github
        restored = await restore_from_github()
        if restored:
            logger.info("✅ GitHub backupdan ma'lumotlar tiklandi")
    except Exception as e:
        logger.warning(f"GitHub restore xatosi: {e}")

    # Buyruqlarni ro'yxatdan o'tkazish
    try:
        await app.bot.set_my_commands(
            GROUP_COMMANDS,
            scope=BotCommandScopeAllGroupChats()
        )
        await app.bot.set_my_commands(
            PRIVATE_COMMANDS,
            scope=BotCommandScopeAllPrivateChats()
        )
        logger.info("✅ Bot commands set")
    except Exception as e:
        logger.warning(f"Commands set error: {e}")

    # Aktiv spawnlarni tiklash
    try:
        await restore_active_spawns(app)
        logger.info("✅ Spawns restored")
    except Exception as e:
        logger.warning(f"Spawn restore error: {e}")

    # GitHub backup schedulerni ishga tushirish (har 6 soatda)
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from utils.github_backup import backup_to_github

        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.add_job(
            backup_to_github,
            trigger='interval',
            hours=6,
            id='github_backup',
            replace_existing=True,
            max_instances=1,
        )
        scheduler.start()
        logger.info("✅ GitHub backup scheduler ishga tushdi (har 6 soatda)")
    except Exception as e:
        logger.warning(f"Scheduler xatosi: {e}")


# ════════════════════════════════════════
# Main
# ════════════════════════════════════════
def main():
    token = os.environ.get('BOT_TOKEN', '').strip()
    if not token:
        logger.error('❌ BOT_TOKEN topilmadi! Railway → Variables ga BOT_TOKEN qo\'ying.')
        logger.error('   https://railway.app → sizning service → Variables')
        sys.exit(1)

    webhook_url = os.environ.get('WEBHOOK_URL', '')
    port = int(os.environ.get('PORT', 8443))

    app = build_app(token)

    if webhook_url:
        logger.info(f'Webhook mode: {webhook_url}')
        app.run_webhook(
            listen='0.0.0.0',
            port=port,
            webhook_url=webhook_url,
            url_path=token,
            drop_pending_updates=True,
        )
    else:
        logger.info('Polling mode...')
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == '__main__':
    main()
