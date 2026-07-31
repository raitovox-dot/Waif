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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

GROUP_COMMANDS = [
    BotCommand('waifu', 'Waifu tutish: /waifu [ism]'),
    BotCommand('collection', 'Kolleksiyangiz'),
    BotCommand('profil', 'Profilingiz'),
    BotCommand('daily', 'Kunlik mukofot'),
    BotCommand('top', 'Global reyting'),
    BotCommand('gtop', 'Guruh reytingi'),
    BotCommand('trade', 'Waifu savdosi'),
    BotCommand('gift', "Waifu sovg'a qilish"),
    BotCommand('sell', "Bozorga qo'yish"),
    BotCommand('market', "Bugungi do'kon"),
    BotCommand('buy', "Do'kondan sotib olish"),
    BotCommand('search', 'Waifu qidirish'),
    BotCommand('duplicate', 'Duplicate kartalar'),
    BotCommand('help', 'Yordam'),
]

PRIVATE_COMMANDS = [
    BotCommand('start', 'Botni boshlash'),
    BotCommand('profil', 'Profilingiz'),
    BotCommand('collection', 'Kolleksiyangiz'),
    BotCommand('daily', 'Kunlik mukofot'),
    BotCommand('top', 'Global reyting'),
    BotCommand('market', "Bugungi do'kon"),
    BotCommand('search', 'Waifu qidirish'),
    BotCommand('stats', 'Statistika'),
    BotCommand('help', 'Yordam'),
    BotCommand('panel', 'Admin panel'),
]


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
    user = await user_db.get_user(owner_id)
    if not user:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return
    name = user.get('full_name') or user.get('username') or str(owner_id)
    items = await col_db.get_collection(owner_id, limit=10, offset=0)
    total = await col_db.count_collection(owner_id)
    lines = [f"🎴 <b>{name}</b> kolleksiyasi ({total} ta)\n━━━━━━━━━━━━━━━━━━━━"]
    for item in items:
        emoji = get_rarity_emoji(item['rarity'])
        lines.append(f"{emoji} <b>{item['name']}</b> | {item['anime']}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def post_init(app):
    # DB init
    await init_db()
    # God admin ro'yxatga
    god_id_str = os.environ.get("GOD_ADMIN_ID", "")
    if god_id_str:
        try:
            await log_db.register_god_admin(int(god_id_str))
        except Exception:
            pass
    # Spawn eski holatlarini tiklash
    await restore_active_spawns(app)
    # Komandalarni o'rnatish
    try:
        await app.bot.set_my_commands(GROUP_COMMANDS, scope=BotCommandScopeAllGroupChats())
        await app.bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    except Exception as e:
        logger.warning(f"Commands set error: {e}")
    logger.info("Bot initialized!")


def build_app(token: str) -> Application:
    app = Application.builder().token(token).post_init(post_init).build()

    # ── Middleware ──
    app.add_handler(MessageHandler(filters.ALL, ban_check_middleware), group=-10)

    # ── Start / Help ──
    app.add_handler(CommandHandler('start', cmd_start_handler))
    app.add_handler(CommandHandler('help', cmd_help))

    # ── Waifu tutish ──
    app.add_handler(CommandHandler('waifu', cmd_waifu_catch))

    # ── Gallereya ──
    app.add_handler(CommandHandler('collection', cmd_collection_gallery))
    app.add_handler(CallbackQueryHandler(handle_gallery_callback, pattern=r'^gal_'))

    # ── Profil / Statistika ──
    app.add_handler(CommandHandler('profil', cmd_profil))
    app.add_handler(CommandHandler('stats', cmd_stats))
    app.add_handler(CommandHandler('daily', cmd_daily))
    app.add_handler(CommandHandler('top', cmd_top))
    app.add_handler(CommandHandler('gtop', cmd_gtop))
    app.add_handler(CommandHandler('search', cmd_search))
    app.add_handler(CommandHandler('anime', cmd_anime))
    app.add_handler(CommandHandler('favorite', cmd_favorite))
    app.add_handler(CommandHandler('history', cmd_history))

    # ── Trade / Gift ──
    app.add_handler(CommandHandler('trade', cmd_trade))
    app.add_handler(CallbackQueryHandler(handle_trade_callback, pattern=r'^trade_'))
    app.add_handler(CommandHandler('gift', cmd_gift))
    app.add_handler(CallbackQueryHandler(handle_gift_callback, pattern=r'^gift_'))

    # ── Bozor ──
    app.add_handler(CommandHandler('sell', cmd_sell))
    app.add_handler(CommandHandler('market', cmd_market))
    app.add_handler(CommandHandler('buy', cmd_buy))
    app.add_handler(CallbackQueryHandler(handle_shop_callback, pattern=r'^shop_'))

    # ── Duplicate ──
    app.add_handler(CommandHandler('duplicate', cmd_duplicate))
    app.add_handler(CallbackQueryHandler(handle_dup_callback, pattern=r'^dup_'))

    # ── Admin Panel ──
    app.add_handler(CommandHandler('panel', cmd_panel))
    app.add_handler(CommandHandler('addwaifu', cmd_addwaifu_cmd))
    app.add_handler(CommandHandler('removewaifu', cmd_removewaifu))
    app.add_handler(CommandHandler('spawn', cmd_spawn_admin))
    app.add_handler(CommandHandler('broadcast', cmd_broadcast))
    app.add_handler(CommandHandler('addadmin', cmd_addadmin))
    app.add_handler(CommandHandler('addsubadmin', cmd_addsubadmin))
    app.add_handler(CommandHandler('removeadmin', cmd_removeadmin))
    app.add_handler(CommandHandler('ban', cmd_ban_user))
    app.add_handler(CommandHandler('unban', cmd_unban_user))
    app.add_handler(CommandHandler('givecoins', cmd_givecoins))
    app.add_handler(CommandHandler('givewaifu', cmd_givewaifu))
    app.add_handler(CommandHandler('event', cmd_event))
    app.add_handler(CommandHandler('approvegroup', cmd_approvegroup))
    app.add_handler(CommandHandler('denygroup', cmd_denygroup))
    app.add_handler(CommandHandler('addchannel', cmd_addchannel))
    app.add_handler(CommandHandler('removechannel', cmd_removechannel))
    app.add_handler(CommandHandler('setspawn', cmd_setspawn))
    app.add_handler(CommandHandler('addgroup', cmd_addgroup_bypass))
    app.add_handler(CommandHandler('admins', cmd_admins))
    app.add_handler(CommandHandler('settitle', cmd_settitle))
    app.add_handler(CommandHandler('removetitle', cmd_removetitle))
    app.add_handler(CommandHandler('titles', cmd_titles))

    # ── Moderation ──
    app.add_handler(CommandHandler('warn', cmd_warn))
    app.add_handler(CommandHandler('mute', cmd_mute))
    app.add_handler(CommandHandler('unmute', cmd_unmute))
    app.add_handler(CommandHandler('kick', cmd_kick))
    app.add_handler(CommandHandler('mban', cmd_ban))
    app.add_handler(CommandHandler('munban', cmd_unban))

    # ── Obuna tekshirish ──
    app.add_handler(CallbackQueryHandler(handle_subscription_check, pattern=r'^sub_check$'))

    # ── Admin Callback ──
    app.add_handler(CallbackQueryHandler(
        handle_admin_callback,
        pattern=r'^(adm_|rarity_|wgrp_|ewrar_)'
    ))

    # ── Inline ──
    app.add_handler(InlineQueryHandler(handle_inline_query))

    # ── Admin Panel Tugmalari (ReplyKeyboard) ──
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        handle_panel_button,
        block=False
    ))

    # ── Admin Rasm ──
    app.add_handler(MessageHandler(
        filters.PHOTO & filters.ChatType.PRIVATE,
        handle_admin_photo
    ))

    # ── Admin Matn (state machine) ──
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        handle_admin_input
    ))

    # ── Guruh ──
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_member))
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
        handle_message_count
    ))

    return app


def main():
    token = os.environ.get('BOT_TOKEN')
    if not token:
        logger.error('BOT_TOKEN not found!')
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
