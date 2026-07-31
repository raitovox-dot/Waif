"""
To'liq Admin Panel:
- Waifu bo'limi: qo'shish, ro'yxat, ID bo'yicha tahrirlash, o'chirish, guruhlar
- Event bo'limi: yaratish, ro'yxat, yoqish/o'chirish, tahrirlash, event waifu qo'shish
- Foydalanuvchi bo'limi: ban, unban, coin berish, waifu berish
- Tizim: broadcast, statistika, spawn sozlamalari, kanallar, adminlar
"""
import re
import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import ContextTypes
from database import waifus as waifu_db
from database import users as user_db
from database import logs as log_db
from database import groups as grp_db
from database import collections as col_db
from database import titles as title_db
from database import events as event_db
from utils.helpers import get_rarity_emoji, is_god_admin, RARITY_ORDER, RARITY_CONFIG

# ══════════════════════════════════════════════════════════════
#  PANEL TUGMALARI
# ══════════════════════════════════════════════════════════════

# Asosiy bo'limlar
BTN_WAIFU_SEC   = "🎴 Waifu boshqaruvi"
BTN_EVENT_SEC   = "⚡ Event boshqaruvi"
BTN_USER_SEC    = "👥 Foydalanuvchi"
BTN_SYS_SEC     = "⚙️ Tizim"
BTN_BACK_MAIN   = "🏠 Asosiy menyu"

# Waifu bo'limi
BTN_ADDWAIFU    = "➕ Waifu qo'shish"
BTN_LISTWAIFU   = "📋 Waifular ro'yxati"
BTN_FINDWAIFU   = "🔍 ID bo'yicha topish"
BTN_WAIFU_GRP   = "📂 Guruhlar"

# Event bo'limi
BTN_ADD_EVENT   = "🆕 Event yaratish"
BTN_LIST_EVENT  = "📋 Eventlar ro'yxati"

# Foydalanuvchi bo'limi
BTN_BAN         = "🚫 Ban"
BTN_UNBAN       = "✅ Unban"
BTN_COINS       = "💰 Coin berish"
BTN_GIVEW       = "🎴 Waifu berish"
BTN_TITLE       = "🏅 Unvon berish"
BTN_USERS       = "👁 A'zolar"

# Tizim bo'limi
BTN_BROADCAST   = "📣 Broadcast"
BTN_STATS       = "📊 Statistika"
BTN_SPAWN       = "🔧 Spawn sozlash"
BTN_ADDCH       = "📢 Kanal qo'shish"
BTN_RMCH        = "❌ Kanal o'chirish"
BTN_ADDADMIN    = "👑 Admin qo'shish"
BTN_RMADMIN     = "🔴 Admin o'chirish"
BTN_ADDSUBADM   = "🟡 Sub-Admin"
BTN_ADDGROUP    = "🔓 Guruh bypass"

BTN_CLOSE       = "🚪 Yopish"

SUB_ADMIN_BUTTONS = {BTN_ADDWAIFU, BTN_LISTWAIFU, BTN_WAIFU_SEC, BTN_BACK_MAIN, BTN_CLOSE}

ALL_PANEL_BUTTONS = {
    BTN_WAIFU_SEC, BTN_EVENT_SEC, BTN_USER_SEC, BTN_SYS_SEC, BTN_BACK_MAIN,
    BTN_ADDWAIFU, BTN_LISTWAIFU, BTN_FINDWAIFU, BTN_WAIFU_GRP,
    BTN_ADD_EVENT, BTN_LIST_EVENT,
    BTN_BAN, BTN_UNBAN, BTN_COINS, BTN_GIVEW, BTN_TITLE, BTN_USERS,
    BTN_BROADCAST, BTN_STATS, BTN_SPAWN, BTN_ADDCH, BTN_RMCH,
    BTN_ADDADMIN, BTN_RMADMIN, BTN_ADDSUBADM, BTN_ADDGROUP,
    BTN_CLOSE,
}

SUB_ADMIN_BLOCKED_RARITY = {"Mythick", "Legendary", "Premium", "Exclusive", "Divine"}

# ══════════════════════════════════════════════════════════════
#  STATE MACHINE
# ══════════════════════════════════════════════════════════════
ADM_STATE = "adm_state"
ADM_DATA  = "adm_data"

S_NONE = None

# Waifu qo'shish
S_PHOTO      = "addwaifu_photo"
S_NAME       = "addwaifu_name"
S_ANIME      = "addwaifu_anime"
S_PRICE      = "addwaifu_price"
S_GROUP_SEL  = "addwaifu_group_sel"

# Waifu tahrirlash
S_FIND_ID    = "find_waifu_id"
S_EDIT_FIELD = "edit_waifu_field"
S_EDIT_VAL   = "edit_waifu_val"
S_EDIT_PHOTO = "edit_waifu_photo"

# Waifu guruh
S_NEW_GROUP_NAME = "new_group_name"
S_NEW_GROUP_DESC = "new_group_desc"

# Event
S_EVENT_NAME    = "event_name"
S_EVENT_TYPE    = "event_type"
S_EVENT_DESC    = "event_desc"
S_EVENT_TRIGGER = "event_trigger"
S_EW_PHOTO      = "ew_photo"
S_EW_NAME       = "ew_name"
S_EW_ANIME      = "ew_anime"
S_EW_RARITY     = "ew_rarity"
S_EW_PRICE      = "ew_price"

# Foydalanuvchi
S_BAN         = "ban"
S_UNBAN       = "unban"
S_COINS_UID   = "coins_uid"
S_COINS_AMT   = "coins_amt"
S_GIVEW_UID   = "givew_uid"
S_GIVEW_WID   = "givew_wid"
S_BROADCAST   = "broadcast"
S_ADDADMIN    = "addadmin"
S_ADDSUBADM   = "addsubadm"
S_RMADMIN     = "rmadmin"
S_ADDCH_ID    = "addch_id"
S_ADDCH_NAME  = "addch_name"
S_TITLE_UID   = "title_uid"
S_TITLE_TXT   = "title_txt"
S_SPAWN_SET   = "spawn_set"
S_ADDGROUP_BP = "addgroup_bypass"

PAGE_SIZE = 8

AVAILABLE_RARITIES = [r for r in RARITY_ORDER]


# ══════════════════════════════════════════════════════════════
#  KLAVIATURALAR
# ══════════════════════════════════════════════════════════════

def _main_kb(role: str) -> ReplyKeyboardMarkup:
    if role == "sub":
        rows = [[BTN_WAIFU_SEC], [BTN_CLOSE]]
    elif role == "god":
        rows = [
            [BTN_WAIFU_SEC, BTN_EVENT_SEC],
            [BTN_USER_SEC,  BTN_SYS_SEC],
            [BTN_CLOSE],
        ]
    else:
        rows = [
            [BTN_WAIFU_SEC, BTN_EVENT_SEC],
            [BTN_USER_SEC,  BTN_SYS_SEC],
            [BTN_CLOSE],
        ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def _waifu_kb(role: str) -> ReplyKeyboardMarkup:
    rows = [
        [BTN_ADDWAIFU, BTN_LISTWAIFU],
        [BTN_FINDWAIFU, BTN_WAIFU_GRP],
        [BTN_BACK_MAIN],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def _event_kb(role: str) -> ReplyKeyboardMarkup:
    rows = [
        [BTN_ADD_EVENT, BTN_LIST_EVENT],
        [BTN_BACK_MAIN],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def _user_kb(role: str) -> ReplyKeyboardMarkup:
    rows = [
        [BTN_BAN, BTN_UNBAN],
        [BTN_COINS, BTN_GIVEW],
        [BTN_TITLE, BTN_USERS],
        [BTN_BACK_MAIN],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def _sys_kb(role: str) -> ReplyKeyboardMarkup:
    if role == "god":
        rows = [
            [BTN_BROADCAST, BTN_STATS],
            [BTN_SPAWN, BTN_ADDCH],
            [BTN_RMCH, BTN_ADDADMIN],
            [BTN_ADDSUBADM, BTN_RMADMIN],
            [BTN_ADDGROUP, BTN_BACK_MAIN],
        ]
    else:
        rows = [
            [BTN_BROADCAST, BTN_STATS],
            [BTN_SPAWN, BTN_BACK_MAIN],
        ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def _clear_state(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop(ADM_STATE, None)
    context.user_data.pop(ADM_DATA, None)


async def _get_role(user_id: int) -> str:
    role = await log_db.get_admin_role(user_id)
    return role or ""


async def _get_kb(user_id: int):
    role = await _get_role(user_id)
    mode = _get_mode(user_id)
    if mode == "waifu":
        return _waifu_kb(role), role
    if mode == "event":
        return _event_kb(role), role
    if mode == "user":
        return _user_kb(role), role
    if mode == "sys":
        return _sys_kb(role), role
    return _main_kb(role), role


_user_mode: dict[int, str] = {}


def _get_mode(user_id: int) -> str:
    return _user_mode.get(user_id, "main")


def _set_mode(user_id: int, mode: str):
    _user_mode[user_id] = mode


# ══════════════════════════════════════════════════════════════
#  RUXSAT TEKSHIRISH
# ══════════════════════════════════════════════════════════════

async def require_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not await log_db.is_admin(user.id):
        if update.message:
            await update.message.reply_text("❌ Ruxsatingiz yo'q.")
        return False
    return True


async def require_full_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not await log_db.is_full_admin(user.id):
        if update.message:
            await update.message.reply_text("❌ Faqat to'liq admin.")
        return False
    return True


# ══════════════════════════════════════════════════════════════
#  PANEL KOMANDASI
# ══════════════════════════════════════════════════════════════

async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    user = update.effective_user
    role = await _get_role(user.id)
    _set_mode(user.id, "main")
    _clear_state(context)
    role_label = {"god": "👑 God Admin", "admin": "🔧 Admin", "sub": "🟡 Sub-Admin"}.get(role, "Admin")
    await update.message.reply_text(
        f"🛡 <b>ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {user.full_name} — {role_label}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=_main_kb(role)
    )


# ══════════════════════════════════════════════════════════════
#  WAIFU RO'YXATI VA TAHRIRLASH
# ══════════════════════════════════════════════════════════════

async def _show_waifu_list(message, page: int = 0, owner_id=None, group_id=None, title="📋 WAIFULAR"):
    if owner_id:
        total = await waifu_db.count_waifus_by_admin(owner_id)
        waifus = await waifu_db.get_waifus_by_admin(owner_id, PAGE_SIZE, page * PAGE_SIZE)
    else:
        total = await waifu_db.count_all_active()
        waifus = await waifu_db.get_all_waifus_paginated(PAGE_SIZE, page * PAGE_SIZE, group_id)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if not waifus:
        await message.reply_text("📭 Waifular yo'q.")
        return
    lines = [f"<b>{title}</b> [{page+1}/{total_pages}] — jami: {total}\n━━━━━━━━━━━━━━━━━━━━"]
    buttons = []
    for w in waifus:
        emoji = get_rarity_emoji(w['rarity'])
        grp = f" [{w.get('group_name') or '—'}]" if w.get('group_name') else ""
        price = f" 💰{w.get('price',0):,}" if w.get('price') else ""
        lines.append(f"{emoji} <code>#{w['waifu_id']}</code> <b>{w['name']}</b> | {w['anime']}{grp}{price}")
        buttons.append([
            InlineKeyboardButton(f"✏️ {w['name'][:15]}", callback_data=f"adm_edit_{w['waifu_id']}"),
            InlineKeyboardButton("🗑", callback_data=f"adm_del_{w['waifu_id']}"),
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"adm_wlist_{page-1}_{owner_id or 0}_{group_id or 0}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"adm_wlist_{page+1}_{owner_id or 0}_{group_id or 0}"))
    if nav:
        buttons.append(nav)
    await message.reply_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
    )


async def _show_waifu_edit_menu(message, waifu_id: str):
    waifu = await waifu_db.get_waifu(waifu_id) or await waifu_db.get_waifu_any(waifu_id)
    if not waifu:
        await message.reply_text(f"❌ #{waifu_id} topilmadi.")
        return
    emoji = get_rarity_emoji(waifu['rarity'])
    grp = waifu.get('group_name') or "—"
    price = waifu.get('price', 0) or 0
    text = (
        f"✏️ <b>WAIFU TAHRIRLASH</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} <code>#{waifu['waifu_id']}</code>\n"
        f"📛 Ism: <b>{waifu['name']}</b>\n"
        f"🎌 Anime: <b>{waifu['anime']}</b>\n"
        f"⭐ Rarity: <b>{waifu['rarity']}</b>\n"
        f"💰 Narx: <b>{price:,}</b> coin\n"
        f"📂 Guruh: <b>{grp}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"O'zgartirish uchun tanlang:"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📛 Ism", callback_data=f"adm_ef_name_{waifu_id}"),
            InlineKeyboardButton("🎌 Anime", callback_data=f"adm_ef_anime_{waifu_id}"),
        ],
        [
            InlineKeyboardButton("⭐ Rarity", callback_data=f"adm_ef_rarity_{waifu_id}"),
            InlineKeyboardButton("💰 Narx", callback_data=f"adm_ef_price_{waifu_id}"),
        ],
        [
            InlineKeyboardButton("🖼 Rasm", callback_data=f"adm_ef_photo_{waifu_id}"),
            InlineKeyboardButton("📂 Guruh", callback_data=f"adm_ef_group_{waifu_id}"),
        ],
        [
            InlineKeyboardButton("🗑 O'chirish", callback_data=f"adm_del_{waifu_id}"),
        ],
    ])
    await message.reply_photo(
        photo=waifu['file_id'], caption=text,
        parse_mode="HTML", reply_markup=kb
    )


# ══════════════════════════════════════════════════════════════
#  GURUHLAR
# ══════════════════════════════════════════════════════════════

async def _show_groups(message):
    groups = await waifu_db.get_all_groups_list()
    if not groups:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("➕ Guruh yaratish", callback_data="adm_newgroup")
        ]])
        await message.reply_text("📂 Guruhlar yo'q.", reply_markup=kb)
        return
    lines = ["📂 <b>WAIFU GURUHLARI</b>\n━━━━━━━━━━━━━━━━━━━━"]
    buttons = []
    for g in groups:
        cnt = await waifu_db.count_waifus_in_group(g['id'])
        lines.append(f"• <b>{g['name']}</b> — {cnt} waifu")
        buttons.append([
            InlineKeyboardButton(f"📋 {g['name'][:12]}", callback_data=f"adm_grplist_{g['id']}"),
            InlineKeyboardButton("🗑", callback_data=f"adm_grpdel_{g['id']}"),
        ])
    buttons.append([InlineKeyboardButton("➕ Yangi guruh", callback_data="adm_newgroup")])
    await message.reply_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ══════════════════════════════════════════════════════════════
#  STATISTIKA
# ══════════════════════════════════════════════════════════════

async def _show_stats(message):
    counts = await waifu_db.count_waifus_by_rarity()
    total = sum(counts.values())
    all_users = await user_db.get_all_users()
    from database.market import count_active_listings
    market_count = await count_active_listings()
    channels = await log_db.get_required_channels_count()
    active_ev = await event_db.get_active_event()
    all_events = await event_db.get_all_events()
    groups = await waifu_db.get_all_groups_list()

    lines = [
        "📊 <b>BOT STATISTIKASI</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👥 Foydalanuvchilar: <b>{len(all_users)}</b>",
        f"🎴 Jami waifular: <b>{total}</b>",
        f"📂 Guruhlar: <b>{len(groups)}</b>",
        f"🛒 Bozorda: <b>{market_count}</b>",
        f"📢 Majburiy kanallar: <b>{channels}</b>",
        f"⚡ Eventlar: <b>{len(all_events)}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "<b>Rarity taqsimoti:</b>",
    ]
    for r in RARITY_ORDER:
        cnt = counts.get(r, 0)
        emoji = get_rarity_emoji(r)
        pct = RARITY_CONFIG[r].get("percent", "?")
        lines.append(f"{emoji} {r}: <b>{cnt}</b> ({pct})")
    if active_ev:
        lines += [
            "━━━━━━━━━━━━━━━━━━━━",
            f"⚡ Aktiv event: <b>{active_ev['name']}</b> [{active_ev['event_type']}]",
            f"📋 {active_ev.get('description', '')}",
        ]
    await message.reply_text("\n".join(lines), parse_mode="HTML")


# ══════════════════════════════════════════════════════════════
#  A'ZOLAR
# ══════════════════════════════════════════════════════════════

async def _show_users(message):
    all_ids = await user_db.get_all_users()
    top = await user_db.get_top_users(10, "total_caught")
    admins = await log_db.get_admins()
    role_mark = {"god": "👑", "admin": "🔧", "sub": "🟡"}
    lines = [
        "👥 <b>BOT A'ZOLARI</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"Jami: <b>{len(all_ids)}</b> foydalanuvchi",
        "",
        "🛡️ <b>Adminlar:</b>",
    ]
    for a in admins:
        r = a.get("role") or "admin"
        mark = role_mark.get(r, "🔧")
        uname = f"@{a['username']}" if a.get("username") else ""
        lines.append(f"{mark} <code>{a['user_id']}</code> {uname}")
    lines += ["", "🏆 <b>Top 10 (waifular):</b>"]
    medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, 11)]
    for i, u in enumerate(top):
        name = u.get("full_name") or u.get("username") or str(u["user_id"])
        lines.append(f"{medals[i]} <code>{u['user_id']}</code> {name} — {u['total_caught']} waifu")
    await message.reply_text("\n".join(lines), parse_mode="HTML")


# ══════════════════════════════════════════════════════════════
#  EVENTLAR
# ══════════════════════════════════════════════════════════════

async def _show_events(message, role: str):
    events = await event_db.get_all_events()
    if not events:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("➕ Event yaratish", callback_data="adm_create_event")
        ]])
        await message.reply_text("📭 Eventlar yo'q.", reply_markup=kb)
        return
    active_ev = await event_db.get_active_event()
    active_id = active_ev['id'] if active_ev else None
    lines = ["⚡ <b>EVENTLAR RO'YXATI</b>\n━━━━━━━━━━━━━━━━━━━━"]
    buttons = []
    for e in events:
        ew_count = len(await event_db.get_event_waifus(e['id']))
        status = "🟢 AKTIV" if e['id'] == active_id else "🔴 NOFAOL"
        lines.append(
            f"{status} <b>{e['name']}</b> [{e['event_type']}]\n"
            f"   📋 {e.get('description', '—')}\n"
            f"   🎴 {ew_count} waifu | Har {e['trigger_every']} xabarda"
        )
        row = []
        if e['id'] == active_id:
            row.append(InlineKeyboardButton("⏹ O'chirish", callback_data=f"adm_evoff_{e['id']}"))
        else:
            row.append(InlineKeyboardButton("▶️ Yoqish", callback_data=f"adm_evon_{e['id']}"))
        row.append(InlineKeyboardButton("🎴 Waifular", callback_data=f"adm_evwaifus_{e['id']}"))
        row.append(InlineKeyboardButton("🗑", callback_data=f"adm_evdel_{e['id']}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("➕ Yangi event", callback_data="adm_create_event")])
    await message.reply_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def _show_event_waifus(query_or_msg, event_id: int):
    ev = await event_db.get_event_by_id(event_id)
    if not ev:
        return
    waifus = await event_db.get_event_waifus(event_id)
    lines = [
        f"🎴 <b>{ev['name']} — Waifular</b>\n━━━━━━━━━━━━━━━━━━━━"
    ]
    buttons = []
    for ew in waifus:
        emoji = get_rarity_emoji(ew['rarity'])
        price = ew.get('price', 0) or 0
        lines.append(f"{emoji} <b>{ew['name']}</b> | {ew['anime']} | 💰{price:,}")
        buttons.append([
            InlineKeyboardButton(f"🗑 {ew['name'][:15]}", callback_data=f"adm_ewdel_{ew['id']}_{event_id}")
        ])
    buttons.append([
        InlineKeyboardButton("➕ Waifu qo'shish", callback_data=f"adm_addew_{event_id}"),
        InlineKeyboardButton("⬅️ Orqaga", callback_data=f"adm_evlist_back"),
    ])
    text = "\n".join(lines) if waifus else f"🎴 <b>{ev['name']}</b> — waifular yo'q"
    kb = InlineKeyboardMarkup(buttons)
    if hasattr(query_or_msg, 'edit_message_text'):
        await query_or_msg.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await query_or_msg.reply_text(text, parse_mode="HTML", reply_markup=kb)


# ══════════════════════════════════════════════════════════════
#  PANEL TUGMA HANDLERI (ReplyKeyboard)
# ══════════════════════════════════════════════════════════════

async def handle_panel_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    if text not in ALL_PANEL_BUTTONS:
        return
    if not await log_db.is_admin(user.id):
        await update.message.reply_text("❌ Ruxsatingiz yo'q.", reply_markup=ReplyKeyboardRemove())
        return
    role = await _get_role(user.id)
    is_sub = (role == "sub")

    # State ichida panel tugmasi bosilsa
    current_state = context.user_data.get(ADM_STATE)
    if current_state in (S_PHOTO, S_NAME, S_ANIME, S_PRICE, S_GROUP_SEL,
                         S_EW_PHOTO, S_EW_NAME, S_EW_ANIME, S_EW_RARITY, S_EW_PRICE,
                         S_NEW_GROUP_NAME, S_NEW_GROUP_DESC,
                         S_EVENT_NAME, S_EVENT_TYPE, S_EVENT_DESC, S_EVENT_TRIGGER):
        hint = {
            S_PHOTO: "📸 Waifu rasmini yuboring (yoki /cancel).",
            S_NAME: "📝 Ism kiriting (yoki /cancel).",
            S_ANIME: "🎌 Anime nomini kiriting (yoki /cancel).",
            S_PRICE: "💰 Narx kiriting (yoki 0) (yoki /cancel).",
            S_EW_PHOTO: "📸 Event waifu rasmini yuboring.",
            S_EW_NAME: "📝 Event waifu ismini kiriting.",
            S_EW_ANIME: "🎌 Event waifu anime nomini kiriting.",
            S_EW_PRICE: "💰 Event waifu narxini kiriting.",
            S_NEW_GROUP_NAME: "📂 Guruh nomini kiriting.",
            S_NEW_GROUP_DESC: "📝 Guruh tavsifini kiriting.",
            S_EVENT_NAME: "🆕 Event nomini kiriting.",
            S_EVENT_TYPE: "🏷 Event turini kiriting.",
            S_EVENT_DESC: "📋 Event tavsifini kiriting.",
            S_EVENT_TRIGGER: "🔢 Har necha xabarda chiqsin? (son kiriting).",
        }.get(current_state, "Jarayon davom etmoqda. /cancel deb yozing.")
        mode = _get_mode(user.id)
        kb = _waifu_kb(role) if mode == "waifu" else _event_kb(role) if mode == "event" else _main_kb(role)
        await update.message.reply_text(hint, reply_markup=kb)
        return

    # Sub-admin cheklov
    if is_sub and text not in SUB_ADMIN_BUTTONS:
        await update.message.reply_text("🚫 Sub-admin ushbu amalni bajara olmaydi.")
        return

    # ── Yopish ──
    if text == BTN_CLOSE:
        _clear_state(context)
        _set_mode(user.id, "main")
        await update.message.reply_text("✅ Panel yopildi.", reply_markup=ReplyKeyboardRemove())
        return

    # ── Asosiy menyu ──
    if text == BTN_BACK_MAIN:
        _clear_state(context)
        _set_mode(user.id, "main")
        await update.message.reply_text("🏠 Asosiy menyu:", reply_markup=_main_kb(role))
        return

    # ── Bo'limga o'tish ──
    if text == BTN_WAIFU_SEC:
        _clear_state(context)
        _set_mode(user.id, "waifu")
        await update.message.reply_text("🎴 <b>Waifu boshqaruvi</b>", parse_mode="HTML",
                                        reply_markup=_waifu_kb(role))
        return

    if text == BTN_EVENT_SEC:
        _clear_state(context)
        _set_mode(user.id, "event")
        await update.message.reply_text("⚡ <b>Event boshqaruvi</b>", parse_mode="HTML",
                                        reply_markup=_event_kb(role))
        await _show_events(update.message, role)
        return

    if text == BTN_USER_SEC:
        _clear_state(context)
        _set_mode(user.id, "user")
        await update.message.reply_text("👥 <b>Foydalanuvchi boshqaruvi</b>", parse_mode="HTML",
                                        reply_markup=_user_kb(role))
        return

    if text == BTN_SYS_SEC:
        _clear_state(context)
        _set_mode(user.id, "sys")
        await update.message.reply_text("⚙️ <b>Tizim sozlamalari</b>", parse_mode="HTML",
                                        reply_markup=_sys_kb(role))
        return

    # ════════════════════════
    #  WAIFU BO'LIMI
    # ════════════════════════
    kb = _waifu_kb(role)

    if text == BTN_ADDWAIFU:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_PHOTO
        await update.message.reply_text(
            "📸 <b>WAIFU QO'SHISH</b>\n\nWaifu rasmini yuboring:\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb
        )
        return

    if text == BTN_LISTWAIFU:
        _clear_state(context)
        owner = user.id if is_sub else None
        await _show_waifu_list(update.message, page=0, owner_id=owner)
        return

    if text == BTN_FINDWAIFU:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_FIND_ID
        await update.message.reply_text(
            "🔍 <b>ID BO'YICHA TOPISH</b>\n\nWaifu ID raqamini kiriting (#raqam):",
            parse_mode="HTML", reply_markup=kb
        )
        return

    if text == BTN_WAIFU_GRP:
        _clear_state(context)
        await _show_groups(update.message)
        return

    # ════════════════════════
    #  EVENT BO'LIMI
    # ════════════════════════
    kb_ev = _event_kb(role)

    if text == BTN_ADD_EVENT:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_EVENT_NAME
        await update.message.reply_text(
            "🆕 <b>EVENT YARATISH</b>\n\nEvent nomini kiriting:\nMisol: <i>Yozgi festival</i>\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb_ev
        )
        return

    if text == BTN_LIST_EVENT:
        _clear_state(context)
        await _show_events(update.message, role)
        return

    # ════════════════════════
    #  FOYDALANUVCHI BO'LIMI
    # ════════════════════════
    kb_u = _user_kb(role)

    if text == BTN_BAN:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_BAN
        await update.message.reply_text(
            "🚫 <b>BAN</b>\n\nUser ID va sabab kiriting:\nFormat: <code>123456789 Sabab</code>",
            parse_mode="HTML", reply_markup=kb_u
        )
        return

    if text == BTN_UNBAN:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_UNBAN
        await update.message.reply_text("✅ Unban — User ID kiriting:", reply_markup=kb_u)
        return

    if text == BTN_COINS:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_COINS_UID
        await update.message.reply_text("💰 Coin berish — User ID kiriting:", reply_markup=kb_u)
        return

    if text == BTN_GIVEW:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_GIVEW_UID
        await update.message.reply_text("🎴 Waifu berish — User ID kiriting:", reply_markup=kb_u)
        return

    if text == BTN_TITLE:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_TITLE_UID
        await update.message.reply_text("🏅 Unvon berish — User ID kiriting:", reply_markup=kb_u)
        return

    if text == BTN_USERS:
        _clear_state(context)
        await _show_users(update.message)
        return

    # ════════════════════════
    #  TIZIM BO'LIMI
    # ════════════════════════
    kb_s = _sys_kb(role)

    if text == BTN_BROADCAST:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_BROADCAST
        await update.message.reply_text(
            "📣 <b>BROADCAST</b>\n\nXabar yozing (matn/rasm):\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb_s
        )
        return

    if text == BTN_STATS:
        _clear_state(context)
        await _show_stats(update.message)
        return

    if text == BTN_SPAWN:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_SPAWN_SET
        await update.message.reply_text(
            "🔧 <b>SPAWN</b>\nHozirgi guruh uchun spawn chegarasini kiriting (son):\n"
            "Misol: 50 (har 50 xabarda 1 waifu)\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb_s
        )
        return

    if text == BTN_ADDCH:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_ADDCH_ID
        await update.message.reply_text(
            "📢 Kanal ID kiriting (masalan @channel yoki -100...)\n\n/cancel — bekor qilish",
            reply_markup=kb_s
        )
        return

    if text == BTN_RMCH:
        _clear_state(context)
        channels = await grp_db.get_required_channels()
        if not channels:
            await update.message.reply_text("📋 Majburiy kanallar yo'q.", reply_markup=kb_s)
            return
        rows = []
        for ch in channels:
            name = ch.get("channel_name") or ch["channel_id"]
            rows.append([InlineKeyboardButton(f"❌ {name}", callback_data=f"adm_rmch_{ch['channel_id']}")])
        await update.message.reply_text("O'chirish uchun kanalni tanlang:",
                                        reply_markup=InlineKeyboardMarkup(rows))
        return

    if text == BTN_ADDADMIN:
        if not is_god_admin(user.id):
            await update.message.reply_text("❌ Faqat God Admin.", reply_markup=kb_s)
            return
        _clear_state(context)
        context.user_data[ADM_STATE] = S_ADDADMIN
        await update.message.reply_text(
            "👑 Admin qo'shish — User ID kiriting:\n\n/cancel — bekor qilish",
            reply_markup=kb_s
        )
        return

    if text == BTN_ADDSUBADM:
        if not is_god_admin(user.id):
            await update.message.reply_text("❌ Faqat God Admin.", reply_markup=kb_s)
            return
        _clear_state(context)
        context.user_data[ADM_STATE] = S_ADDSUBADM
        await update.message.reply_text(
            "🟡 Sub-Admin qo'shish — User ID kiriting:\n\n/cancel — bekor qilish",
            reply_markup=kb_s
        )
        return

    if text == BTN_RMADMIN:
        if not is_god_admin(user.id):
            await update.message.reply_text("❌ Faqat God Admin.", reply_markup=kb_s)
            return
        _clear_state(context)
        context.user_data[ADM_STATE] = S_RMADMIN
        await update.message.reply_text(
            "🔴 Admin o'chirish — User ID kiriting:\n\n/cancel — bekor qilish",
            reply_markup=kb_s
        )
        return

    if text == BTN_ADDGROUP:
        if not is_god_admin(user.id):
            await update.message.reply_text("❌ Faqat God Admin.", reply_markup=kb_s)
            return
        _clear_state(context)
        context.user_data[ADM_STATE] = S_ADDGROUP_BP
        await update.message.reply_text(
            "🔓 Guruh bypass — Guruh ID kiriting:\n\n/cancel — bekor qilish",
            reply_markup=kb_s
        )
        return


# ══════════════════════════════════════════════════════════════
#  MATN HANDLER (state machine)
# ══════════════════════════════════════════════════════════════

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user = update.effective_user
    text = update.message.text or ""
    if text in ALL_PANEL_BUTTONS:
        return
    if not await log_db.is_admin(user.id):
        return
    state = context.user_data.get(ADM_STATE)
    if state is None:
        return
    role = await _get_role(user.id)
    mode = _get_mode(user.id)
    kb_waifu = _waifu_kb(role)
    kb_event = _event_kb(role)
    kb_user = _user_kb(role)
    kb_sys = _sys_kb(role)

    def kb_for_mode():
        if mode == "waifu":
            return kb_waifu
        if mode == "event":
            return kb_event
        if mode == "user":
            return kb_user
        if mode == "sys":
            return kb_sys
        return _main_kb(role)

    if text.strip().lower() == "/cancel":
        _clear_state(context)
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=kb_for_mode())
        return

    # ── Waifu qo'shish: ism ──
    if state == S_NAME:
        context.user_data[ADM_DATA]["name"] = text.strip()
        context.user_data[ADM_STATE] = S_ANIME
        await update.message.reply_text("🎌 Anime nomini kiriting:", reply_markup=kb_waifu)
        return

    # ── Waifu qo'shish: anime ──
    if state == S_ANIME:
        context.user_data[ADM_DATA]["anime"] = text.strip()
        context.user_data[ADM_STATE] = S_PRICE
        await update.message.reply_text(
            "💰 Waifu narxini kiriting (coin, 0 bo'lsa bepul):", reply_markup=kb_waifu
        )
        return

    # ── Waifu qo'shish: narx ──
    if state == S_PRICE:
        try:
            price = int(text.replace(",", "").replace(" ", ""))
        except ValueError:
            price = 0
        context.user_data[ADM_DATA]["price"] = price
        context.user_data[ADM_STATE] = S_GROUP_SEL
        # rarity selection
        is_sub = role == "sub"
        available = [r for r in RARITY_ORDER if r not in ({"Divine"} | ({"Mythick", "Legendary", "Premium", "Exclusive"} if is_sub else {"Divine"}))]
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_rarity_emoji(r)} {r}", callback_data=f"rarity_{r}")]
            for r in available
        ])
        context.user_data[ADM_STATE] = S_GROUP_SEL
        await update.message.reply_text("⭐ Darajani tanlang:", reply_markup=keyboard)
        return

    # ── Waifu topish: ID bo'yicha ──
    if state == S_FIND_ID:
        wid = text.lstrip("#").strip()
        waifu = await waifu_db.get_waifu(wid) or await waifu_db.get_waifu_any(wid)
        if not waifu:
            await update.message.reply_text(f"❌ #{wid} topilmadi.", reply_markup=kb_waifu)
            return
        _clear_state(context)
        await _show_waifu_edit_menu(update.message, wid)
        return

    # ── Waifu tahrirlash: qiymat ──
    if state == S_EDIT_VAL:
        data = context.user_data.get(ADM_DATA, {})
        wid = data.get("wid")
        field = data.get("field")
        if field == "price":
            try:
                val = int(text.replace(",", "").replace(" ", ""))
            except ValueError:
                await update.message.reply_text("❌ Faqat raqam:", reply_markup=kb_waifu)
                return
        else:
            val = text.strip()
        await waifu_db.edit_waifu(wid, **{field: val})
        _clear_state(context)
        await update.message.reply_text(
            f"✅ #{wid} — <b>{field}</b> yangilandi!", parse_mode="HTML", reply_markup=kb_waifu
        )
        await _show_waifu_edit_menu(update.message, wid)
        return

    # ── Yangi guruh: nom ──
    if state == S_NEW_GROUP_NAME:
        context.user_data[ADM_DATA] = {"group_name": text.strip()}
        context.user_data[ADM_STATE] = S_NEW_GROUP_DESC
        await update.message.reply_text("📝 Guruh tavsifini kiriting (yoki - kiriting):", reply_markup=kb_waifu)
        return

    if state == S_NEW_GROUP_DESC:
        data = context.user_data.get(ADM_DATA, {})
        gname = data.get("group_name", "Nomsiz")
        desc = text.strip() if text.strip() != "-" else ""
        gid = await waifu_db.create_group(gname, desc, user.id)
        _clear_state(context)
        if gid:
            await update.message.reply_text(f"✅ Guruh <b>{gname}</b> yaratildi!", parse_mode="HTML", reply_markup=kb_waifu)
        else:
            await update.message.reply_text("❌ Xatolik (guruh nomi takrorlangan bo'lishi mumkin).", reply_markup=kb_waifu)
        return

    # ── Event yaratish ──
    if state == S_EVENT_NAME:
        context.user_data[ADM_DATA] = {"event_name": text.strip()}
        context.user_data[ADM_STATE] = S_EVENT_TYPE
        await update.message.reply_text(
            "🏷 Event turini kiriting:\nMisol: <i>Festival</i>, <i>Bayram</i>, <i>Special</i>",
            parse_mode="HTML", reply_markup=kb_event
        )
        return

    if state == S_EVENT_TYPE:
        context.user_data[ADM_DATA]["event_type"] = text.strip()
        context.user_data[ADM_STATE] = S_EVENT_DESC
        await update.message.reply_text("📋 Event tavsifini kiriting (- = tavsif yo'q):", reply_markup=kb_event)
        return

    if state == S_EVENT_DESC:
        desc = text.strip() if text.strip() != "-" else ""
        context.user_data[ADM_DATA]["event_desc"] = desc
        context.user_data[ADM_STATE] = S_EVENT_TRIGGER
        await update.message.reply_text(
            "🔢 Har necha xabarda event waifu chiqsin?\nMisol: <code>50</code> (har 50 xabarda 1 ta)",
            parse_mode="HTML", reply_markup=kb_event
        )
        return

    if state == S_EVENT_TRIGGER:
        try:
            trigger = int(text.replace(" ", ""))
            if trigger < 1:
                trigger = 50
        except ValueError:
            await update.message.reply_text("❌ Faqat musbat raqam:", reply_markup=kb_event)
            return
        data = context.user_data.get(ADM_DATA, {})
        eid = await event_db.create_event(
            name=data.get("event_name", "Event"),
            event_type=data.get("event_type", "Custom"),
            description=data.get("event_desc", ""),
            trigger_every=trigger,
            created_by=user.id
        )
        _clear_state(context)
        if eid:
            await update.message.reply_text(
                f"✅ Event <b>{data.get('event_name')}</b> yaratildi!\n"
                f"Endi waifular qo'shing 👇",
                parse_mode="HTML", reply_markup=kb_event
            )
            await _show_event_waifus(update.message, eid)
        else:
            await update.message.reply_text("❌ Xatolik yuz berdi.", reply_markup=kb_event)
        return

    # ── Event waifu qo'shish ──
    if state == S_EW_NAME:
        context.user_data[ADM_DATA]["ew_name"] = text.strip()
        context.user_data[ADM_STATE] = S_EW_ANIME
        await update.message.reply_text("🎌 Event waifu anime nomini kiriting:", reply_markup=kb_event)
        return

    if state == S_EW_ANIME:
        context.user_data[ADM_DATA]["ew_anime"] = text.strip()
        context.user_data[ADM_STATE] = S_EW_PRICE
        await update.message.reply_text("💰 Event waifu narxini kiriting (0 = bepul):", reply_markup=kb_event)
        return

    if state == S_EW_PRICE:
        try:
            price = int(text.replace(",", "").replace(" ", ""))
        except ValueError:
            price = 0
        context.user_data[ADM_DATA]["ew_price"] = price
        context.user_data[ADM_STATE] = S_EW_RARITY
        kb_rar = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_rarity_emoji(r)} {r}", callback_data=f"ewrar_{r}")]
            for r in RARITY_ORDER
        ])
        await update.message.reply_text("⭐ Event waifu darajasini tanlang:", reply_markup=kb_rar)
        return

    # ── Foydalanuvchi bo'limi ──
    if state == S_BAN:
        parts = text.split(None, 1)
        try:
            uid = int(parts[0])
        except ValueError:
            await update.message.reply_text("❌ Format: <code>UserID sabab</code>", parse_mode="HTML")
            return
        reason = parts[1] if len(parts) > 1 else "Sabab ko'rsatilmagan"
        await user_db.ban_user(uid, reason)
        from middlewares.ban_middleware import clear_ban_cache
        clear_ban_cache(uid)
        _clear_state(context)
        await update.message.reply_text(
            f"✅ <code>{uid}</code> bloklandi!\n📋 Sabab: {reason}",
            parse_mode="HTML", reply_markup=kb_user
        )
        return

    if state == S_UNBAN:
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam:")
            return
        await user_db.unban_user(uid)
        from middlewares.ban_middleware import clear_ban_cache
        clear_ban_cache(uid)
        _clear_state(context)
        await update.message.reply_text(f"✅ <code>{uid}</code> blokdan chiqarildi!", parse_mode="HTML", reply_markup=kb_user)
        return

    if state == S_COINS_UID:
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam:")
            return
        context.user_data[ADM_DATA] = {"uid": uid}
        context.user_data[ADM_STATE] = S_COINS_AMT
        u = await user_db.get_user(uid)
        current = u["coins"] if u else "?"
        await update.message.reply_text(
            f"💰 <code>{uid}</code>\nHozirgi coin: <b>{current}</b>\n\nNecha coin?",
            parse_mode="HTML", reply_markup=kb_user
        )
        return

    if state == S_COINS_AMT:
        try:
            amount = int(text.replace(",", "").replace(" ", ""))
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam:")
            return
        uid = context.user_data.get(ADM_DATA, {}).get("uid")
        if not uid:
            _clear_state(context)
            return
        await user_db.add_coins(uid, amount)
        await log_db.add_log("give_coins", user_id=user.id, details=f"to={uid} amount={amount}")
        _clear_state(context)
        await update.message.reply_text(
            f"✅ <code>{uid}</code> ga <b>{amount:,}</b> coin berildi!",
            parse_mode="HTML", reply_markup=kb_user
        )
        return

    if state == S_GIVEW_UID:
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam:")
            return
        context.user_data[ADM_DATA] = {"uid": uid}
        context.user_data[ADM_STATE] = S_GIVEW_WID
        await update.message.reply_text(
            f"🎴 <code>{uid}</code> ga qaysi waifu?\nWaifu ID (#raqam) kiriting:",
            parse_mode="HTML", reply_markup=kb_user
        )
        return

    if state == S_GIVEW_WID:
        wid = text.lstrip("#").strip()
        waifu = await waifu_db.get_waifu(wid)
        if not waifu:
            await update.message.reply_text(f"❌ #{wid} topilmadi:")
            return
        uid = context.user_data.get(ADM_DATA, {}).get("uid")
        await col_db.add_to_collection(uid, waifu["waifu_id"])
        emoji = get_rarity_emoji(waifu["rarity"])
        _clear_state(context)
        await update.message.reply_text(
            f"✅ {emoji} <b>{waifu['name']}</b> → <code>{uid}</code> ga berildi!",
            parse_mode="HTML", reply_markup=kb_user
        )
        return

    if state == S_TITLE_UID:
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam:")
            return
        context.user_data[ADM_DATA] = {"uid": uid}
        context.user_data[ADM_STATE] = S_TITLE_TXT
        await update.message.reply_text(f"🏅 <code>{uid}</code> uchun unvon matni:", parse_mode="HTML", reply_markup=kb_user)
        return

    if state == S_TITLE_TXT:
        uid = context.user_data.get(ADM_DATA, {}).get("uid")
        if not uid:
            _clear_state(context)
            return
        await title_db.set_title(uid, text.strip(), user.id)
        _clear_state(context)
        await update.message.reply_text(
            f"✅ <code>{uid}</code>\n🏅 <b>{text.strip()}</b>",
            parse_mode="HTML", reply_markup=kb_user
        )
        return

    if state == S_BROADCAST:
        all_users = await user_db.get_all_users()
        sent = 0
        failed = 0
        for uid in all_users:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)
        _clear_state(context)
        await update.message.reply_text(
            f"📣 Broadcast tugadi!\n✅ Yuborildi: {sent}\n❌ Xato: {failed}",
            reply_markup=kb_sys
        )
        return

    if state == S_ADDADMIN:
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam:")
            return
        u = await user_db.get_user(uid)
        uname = u.get("username") if u else str(uid)
        await log_db.add_admin(uid, uname, user.id, 'admin')
        _clear_state(context)
        await update.message.reply_text(f"✅ <code>{uid}</code> admin qilindi!", parse_mode="HTML", reply_markup=kb_sys)
        return

    if state == S_ADDSUBADM:
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam:")
            return
        u = await user_db.get_user(uid)
        uname = u.get("username") if u else str(uid)
        await log_db.add_admin(uid, uname, user.id, 'sub')
        _clear_state(context)
        await update.message.reply_text(f"✅ <code>{uid}</code> sub-admin qilindi!", parse_mode="HTML", reply_markup=kb_sys)
        return

    if state == S_RMADMIN:
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam:")
            return
        await log_db.remove_admin(uid)
        _clear_state(context)
        await update.message.reply_text(f"✅ <code>{uid}</code> admin ro'yxatidan o'chirildi!", parse_mode="HTML", reply_markup=kb_sys)
        return

    if state == S_ADDCH_ID:
        context.user_data[ADM_DATA] = {"ch_id": text.strip()}
        context.user_data[ADM_STATE] = S_ADDCH_NAME
        await update.message.reply_text("📛 Kanal nomini kiriting:", reply_markup=kb_sys)
        return

    if state == S_ADDCH_NAME:
        ch_id = context.user_data.get(ADM_DATA, {}).get("ch_id")
        ch_name = text.strip()
        if ch_id:
            await grp_db.add_required_channel(ch_id, ch_name, "channel", user.id)
        _clear_state(context)
        await update.message.reply_text(f"✅ {ch_name} ({ch_id}) qo'shildi!", reply_markup=kb_sys)
        return

    if state == S_SPAWN_SET:
        try:
            threshold = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam:")
            return
        from utils.helpers import get_bot_group_id
        gid = get_bot_group_id()
        if gid:
            await grp_db.set_spawn_threshold(gid, threshold)
        _clear_state(context)
        await update.message.reply_text(
            f"✅ Spawn chegarasi {threshold} ga o'rnatildi!", reply_markup=kb_sys
        )
        return

    if state == S_ADDGROUP_BP:
        try:
            gid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam:")
            return
        await grp_db.bypass_group(gid)
        _clear_state(context)
        await update.message.reply_text(f"✅ {gid} bypass qilindi!", reply_markup=kb_sys)
        return


# ══════════════════════════════════════════════════════════════
#  RASM HANDLER (waifu qo'shish)
# ══════════════════════════════════════════════════════════════

async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await log_db.is_admin(user.id):
        return
    state = context.user_data.get(ADM_STATE)
    role = await _get_role(user.id)
    kb_waifu = _waifu_kb(role)
    kb_event = _event_kb(role)

    # Waifu qo'shish rasmini qabul qilish
    if state == S_PHOTO:
        photo = update.message.photo[-1]
        file_id = photo.file_id
        context.user_data[ADM_DATA] = {"file_id": file_id}
        context.user_data[ADM_STATE] = S_NAME
        await update.message.reply_text("📝 Waifu ismini kiriting:", reply_markup=kb_waifu)
        return

    # Waifu rasmini yangilash
    if state == S_EDIT_PHOTO:
        data = context.user_data.get(ADM_DATA, {})
        wid = data.get("wid")
        if wid:
            photo = update.message.photo[-1]
            await waifu_db.edit_waifu(wid, file_id=photo.file_id)
            _clear_state(context)
            await update.message.reply_text(f"✅ #{wid} rasmi yangilandi!", reply_markup=kb_waifu)
            await _show_waifu_edit_menu(update.message, wid)
        return

    # Event waifu rasmi
    if state == S_EW_PHOTO:
        photo = update.message.photo[-1]
        file_id = photo.file_id
        context.user_data[ADM_DATA]["ew_file_id"] = file_id
        context.user_data[ADM_STATE] = S_EW_NAME
        await update.message.reply_text("📝 Event waifu ismini kiriting:", reply_markup=kb_event)
        return


# ══════════════════════════════════════════════════════════════
#  CALLBACK HANDLER (InlineKeyboard)
# ══════════════════════════════════════════════════════════════

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if not await log_db.is_admin(user.id):
        await query.answer("❌ Ruxsatingiz yo'q.", show_alert=True)
        return
    data = query.data
    role = await _get_role(user.id)
    is_sub = (role == "sub")

    # ── Rarity tanlash (waifu qo'shish) ──
    if data.startswith("rarity_"):
        rarity = data[7:]
        state = context.user_data.get(ADM_STATE)
        if state not in (S_GROUP_SEL,):
            return
        context.user_data[ADM_DATA]["rarity"] = rarity
        # Guruh tanlash
        groups = await waifu_db.get_all_groups_list()
        if groups:
            rows = [[InlineKeyboardButton("— Guruhs iz—", callback_data="wgrp_none")]]
            for g in groups:
                rows.append([InlineKeyboardButton(g['name'], callback_data=f"wgrp_{g['id']}")])
            await query.edit_message_text("📂 Guruh tanlang:", reply_markup=InlineKeyboardMarkup(rows))
        else:
            await _finalize_add_waifu(query, context, user, role, group_id=None)
        return

    # ── Guruh tanlash (waifu qo'shish) ──
    if data.startswith("wgrp_"):
        gid_str = data[5:]
        group_id = None if gid_str == "none" else int(gid_str)
        await _finalize_add_waifu(query, context, user, role, group_id=group_id)
        return

    # ── Waifu o'chirish ──
    if data.startswith("adm_del_"):
        wid = data[8:]
        await waifu_db.remove_waifu(wid)
        await log_db.add_log("remove_waifu", user_id=user.id, details=f"waifu_id={wid}")
        await query.edit_message_text(f"🗑 #{wid} o'chirildi!")
        return

    # ── Waifu sahifa ko'rish ──
    if data.startswith("adm_wlist_"):
        parts = data.split("_")
        page = int(parts[3])
        owner_id_val = int(parts[4])
        group_id_val = int(parts[5])
        owner = owner_id_val if owner_id_val else None
        gid = group_id_val if group_id_val else None
        try:
            await query.delete_message()
        except Exception:
            pass
        await _show_waifu_list(query.message or update.effective_message, page=page, owner_id=owner, group_id=gid)
        return

    # ── Waifu tahrirlash ──
    if data.startswith("adm_edit_"):
        wid = data[9:]
        await query.delete_message()
        await _show_waifu_edit_menu(update.effective_message, wid)
        return

    # ── Waifu field tanlash ──
    if data.startswith("adm_ef_"):
        parts = data.split("_", 4)
        field = parts[3]
        wid = parts[4]
        context.user_data[ADM_DATA] = {"wid": wid, "field": field}
        if field == "rarity":
            kb_rar = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{get_rarity_emoji(r)} {r}", callback_data=f"adm_efrar_{wid}_{r}")]
                for r in RARITY_ORDER if r != "Divine"
            ])
            await query.edit_message_caption("⭐ Yangi darajani tanlang:", reply_markup=kb_rar)
            return
        elif field == "photo":
            context.user_data[ADM_STATE] = S_EDIT_PHOTO
            await query.answer("📸 Yangi rasmni yuboring", show_alert=True)
            return
        elif field == "group":
            groups = await waifu_db.get_all_groups_list()
            rows = [[InlineKeyboardButton("— Guruhsiz —", callback_data=f"adm_efgset_{wid}_0")]]
            for g in groups:
                rows.append([InlineKeyboardButton(g['name'], callback_data=f"adm_efgset_{wid}_{g['id']}")])
            await query.edit_message_caption("📂 Guruh tanlang:", reply_markup=InlineKeyboardMarkup(rows))
            return
        else:
            context.user_data[ADM_STATE] = S_EDIT_VAL
            field_hints = {"name": "📝 Yangi ism:", "anime": "🎌 Yangi anime:", "price": "💰 Yangi narx:"}
            await query.answer(field_hints.get(field, "Yangi qiymat:"), show_alert=True)
            return

    # ── Rarity o'zgartirish ──
    if data.startswith("adm_efrar_"):
        parts = data.split("_", 4)
        wid = parts[3]
        rarity = parts[4]
        await waifu_db.edit_waifu(wid, rarity=rarity)
        await query.edit_message_caption(f"✅ #{wid} daraja → <b>{rarity}</b>", parse_mode="HTML")
        return

    # ── Guruh o'zgartirish ──
    if data.startswith("adm_efgset_"):
        parts = data.split("_")
        wid = parts[3]
        gid = None if parts[4] == "0" else int(parts[4])
        await waifu_db.edit_waifu(wid, group_id=gid)
        await query.edit_message_caption(f"✅ #{wid} guruh yangilandi!")
        return

    # ── Kanal o'chirish ──
    if data.startswith("adm_rmch_"):
        ch_id = data[9:]
        await grp_db.remove_required_channel(ch_id)
        await query.edit_message_text(f"✅ {ch_id} o'chirildi!")
        return

    # ── Guruh bo'limi ──
    if data == "adm_newgroup":
        context.user_data[ADM_STATE] = S_NEW_GROUP_NAME
        context.user_data[ADM_DATA] = {}
        await query.edit_message_text(
            "📂 <b>YANGI GURUH</b>\n\nGuruh nomini kiriting:\n\n/cancel — bekor qilish",
            parse_mode="HTML"
        )
        return

    if data.startswith("adm_grplist_"):
        gid = int(data[12:])
        try:
            await query.delete_message()
        except Exception:
            pass
        await _show_waifu_list(update.effective_message, page=0, group_id=gid, title=f"📂 GURUH #{gid}")
        return

    if data.startswith("adm_grpdel_"):
        gid = int(data[11:])
        g = await waifu_db.get_group_by_id(gid)
        gname = g['name'] if g else str(gid)
        await waifu_db.delete_group(gid)
        await query.edit_message_text(f"🗑 Guruh <b>{gname}</b> o'chirildi!", parse_mode="HTML")
        return

    # ── EVENT ──
    if data.startswith("adm_evon_"):
        eid = int(data[9:])
        ev = await event_db.get_event_by_id(eid)
        wcs = await event_db.get_event_waifus(eid)
        if not wcs:
            await query.answer("❌ Eventga avval waifular qo'shing!", show_alert=True)
            return
        await event_db.activate_event(eid)
        await query.answer(f"✅ Event yoqildi!", show_alert=True)
        await query.edit_message_text(f"⚡ <b>{ev['name']}</b> event yoqildi!", parse_mode="HTML")
        return

    if data.startswith("adm_evoff_"):
        eid = int(data[10:])
        ev = await event_db.get_event_by_id(eid)
        await event_db.deactivate_event(eid)
        await query.answer("⏹ Event o'chirildi.", show_alert=True)
        await query.edit_message_text(f"⏹ <b>{ev['name'] if ev else 'Event'}</b> o'chirildi.", parse_mode="HTML")
        return

    if data.startswith("adm_evdel_"):
        eid = int(data[10:])
        ev = await event_db.get_event_by_id(eid)
        await event_db.delete_event(eid)
        await query.edit_message_text(f"🗑 Event <b>{ev['name'] if ev else ''}</b> o'chirildi!", parse_mode="HTML")
        return

    if data.startswith("adm_evwaifus_"):
        eid = int(data[13:])
        await _show_event_waifus(query, eid)
        return

    if data == "adm_evlist_back":
        await query.delete_message()
        await _show_events(update.effective_message, role)
        return

    if data == "adm_create_event":
        context.user_data[ADM_STATE] = S_EVENT_NAME
        context.user_data[ADM_DATA] = {}
        await query.edit_message_text(
            "🆕 <b>EVENT YARATISH</b>\n\nEvent nomini kiriting:\nMisol: <i>Yozgi festival</i>\n\n/cancel — bekor qilish",
            parse_mode="HTML"
        )
        return

    if data.startswith("adm_addew_"):
        eid = int(data[10:])
        context.user_data[ADM_STATE] = S_EW_PHOTO
        context.user_data[ADM_DATA] = {"event_id": eid}
        await query.answer("📸 Event waifu rasmini yuboring", show_alert=True)
        return

    if data.startswith("adm_ewdel_"):
        parts = data.split("_")
        ew_id = int(parts[3])
        eid = int(parts[4])
        await event_db.remove_event_waifu(ew_id)
        await _show_event_waifus(query, eid)
        return

    # ── Event waifu rarity tanlash ──
    if data.startswith("ewrar_"):
        rarity = data[6:]
        data_d = context.user_data.get(ADM_DATA, {})
        eid = data_d.get("event_id")
        if not eid:
            return
        ew_id = await event_db.add_event_waifu(
            event_id=eid,
            file_id=data_d.get("ew_file_id", ""),
            name=data_d.get("ew_name", ""),
            anime=data_d.get("ew_anime", ""),
            rarity=rarity,
            price=data_d.get("ew_price", 0),
            added_by=user.id
        )
        _clear_state(context)
        if ew_id:
            await query.edit_message_text(
                f"✅ Event waifu qo'shildi!\n{get_rarity_emoji(rarity)} <b>{data_d.get('ew_name')}</b>",
                parse_mode="HTML"
            )
            await _show_event_waifus(update.effective_message, eid)
        else:
            await query.edit_message_text("❌ Xatolik yuz berdi.")
        return


async def _finalize_add_waifu(query, context, user, role, group_id):
    data = context.user_data.get(ADM_DATA, {})
    file_id = data.get("file_id")
    name = data.get("name")
    anime = data.get("anime")
    rarity = data.get("rarity")
    price = data.get("price", 0)
    if not all([file_id, name, anime, rarity]):
        await query.edit_message_text("❌ Ma'lumotlar to'liq emas.")
        return
    ok, wid = await waifu_db.add_waifu(name, anime, rarity, file_id, user.id, price, group_id)
    await log_db.add_log("add_waifu", user_id=user.id, details=f"id={wid} name={name} rarity={rarity}")
    _clear_state(context)
    emoji = get_rarity_emoji(rarity)
    grp_info = f" | Guruh: #{group_id}" if group_id else ""
    await query.edit_message_text(
        f"✅ Waifu qo'shildi!\n{emoji} <b>{name}</b> | {anime}\n"
        f"⭐ {rarity} | 💰 {price:,} coin{grp_info}\n"
        f"🆔 <code>#{wid}</code>",
        parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════════
#  ESKI KOMANDALAR (muvofiqlik uchun)
# ══════════════════════════════════════════════════════════════

async def cmd_addwaifu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    await update.message.reply_text("➕ Admin paneldan waifu qo'shing: /panel → 🎴 Waifu boshqaruvi → ➕ Waifu qo'shish")


async def cmd_removewaifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("❌ /removewaifu [id]")
        return
    wid = context.args[0].lstrip("#")
    await waifu_db.remove_waifu(wid)
    await update.message.reply_text(f"🗑 #{wid} o'chirildi!")


async def cmd_spawn_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    from handlers.spawn import force_spawn
    await force_spawn(update, context)


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("❌ /broadcast [xabar]")
        return
    text = " ".join(context.args)
    all_users = await user_db.get_all_users()
    sent = 0
    failed = 0
    for uid in all_users:
        try:
            await context.bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await update.message.reply_text(f"📣 Broadcast!\n✅ {sent}\n❌ {failed}")


async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_god_admin(update.effective_user.id):
        await update.message.reply_text("❌ Faqat God Admin.")
        return
    if not context.args:
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        return
    u = await user_db.get_user(uid)
    uname = u.get("username") if u else str(uid)
    await log_db.add_admin(uid, uname, update.effective_user.id, 'admin')
    await update.message.reply_text(f"✅ {uid} admin!")


async def cmd_addsubadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_god_admin(update.effective_user.id):
        await update.message.reply_text("❌ Faqat God Admin.")
        return
    if not context.args:
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        return
    u = await user_db.get_user(uid)
    uname = u.get("username") if u else str(uid)
    await log_db.add_admin(uid, uname, update.effective_user.id, 'sub')
    await update.message.reply_text(f"✅ {uid} sub-admin!")


async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_god_admin(update.effective_user.id):
        await update.message.reply_text("❌ Faqat God Admin.")
        return
    if not context.args:
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        return
    await log_db.remove_admin(uid)
    await update.message.reply_text(f"✅ {uid} o'chirildi!")


async def cmd_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if not context.args:
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        return
    reason = " ".join(context.args[1:]) or "Sabab yo'q"
    await user_db.ban_user(uid, reason)
    await update.message.reply_text(f"🚫 {uid} ban!")


async def cmd_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if not context.args:
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        return
    await user_db.unban_user(uid)
    await update.message.reply_text(f"✅ {uid} unban!")


async def cmd_givecoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if len(context.args) < 2:
        return
    try:
        uid = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        return
    await user_db.add_coins(uid, amount)
    await update.message.reply_text(f"✅ {uid} ga {amount:,} coin!")


async def cmd_givewaifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if len(context.args) < 2:
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        return
    wid = context.args[1].lstrip("#")
    waifu = await waifu_db.get_waifu(wid)
    if not waifu:
        await update.message.reply_text(f"❌ #{wid} topilmadi!")
        return
    await col_db.add_to_collection(uid, wid)
    emoji = get_rarity_emoji(waifu["rarity"])
    await update.message.reply_text(f"✅ {emoji} {waifu['name']} → {uid}")


async def cmd_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    await update.message.reply_text("⚡ Admin paneldan: /panel → ⚡ Event boshqaruvi")


async def cmd_approvegroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if not context.args:
        return
    try:
        gid = int(context.args[0])
    except ValueError:
        return
    await grp_db.approve_group(gid, update.effective_user.id)
    await update.message.reply_text(f"✅ {gid} approved!")


async def cmd_denygroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if not context.args:
        return
    try:
        gid = int(context.args[0])
    except ValueError:
        return
    await grp_db.deny_group(gid)
    await update.message.reply_text(f"❌ {gid} denied!")


async def cmd_addchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if not context.args:
        return
    ch_id = context.args[0]
    ch_name = " ".join(context.args[1:]) or ch_id
    await grp_db.add_required_channel(ch_id, ch_name, "channel", update.effective_user.id)
    await update.message.reply_text(f"✅ {ch_name} qo'shildi!")


async def cmd_removechannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if not context.args:
        return
    await grp_db.remove_required_channel(context.args[0])
    await update.message.reply_text(f"✅ O'chirildi!")


async def cmd_setspawn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if not context.args:
        return
    try:
        t = int(context.args[0])
    except ValueError:
        return
    gid = update.effective_chat.id
    await grp_db.set_spawn_threshold(gid, t)
    await update.message.reply_text(f"✅ Spawn: {t}")


async def cmd_addgroup_bypass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_god_admin(update.effective_user.id):
        await update.message.reply_text("❌ Faqat God Admin.")
        return
    if not context.args:
        return
    try:
        gid = int(context.args[0])
    except ValueError:
        return
    await grp_db.bypass_group(gid)
    await update.message.reply_text(f"✅ {gid} bypass!")


async def cmd_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    admins = await log_db.get_admins()
    role_mark = {"god": "👑 God Admin", "admin": "🔧 Admin", "sub": "🟡 Sub-Admin"}
    lines = ["🛡️ <b>ADMINLAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for a in admins:
        r = a.get("role") or "admin"
        mark = role_mark.get(r, "🔧 Admin")
        uname = f"@{a['username']}" if a.get("username") else ""
        lines.append(f"{mark}: <code>{a['user_id']}</code> {uname}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_settitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ /settitle [user_id] [unvon]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Raqam.")
        return
    title_text = " ".join(context.args[1:]).strip()
    await title_db.set_title(uid, title_text, update.effective_user.id)
    await update.message.reply_text(f"✅ <code>{uid}</code>\n🏅 <b>{title_text}</b>", parse_mode="HTML")


async def cmd_removetitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("❌ /removetitle [user_id]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        return
    await title_db.remove_title(uid)
    await update.message.reply_text(f"✅ {uid} unvoni o'chirildi.")


async def cmd_titles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    all_titles = await title_db.get_all_titles()
    if not all_titles:
        await update.message.reply_text("📋 Unvonlar yo'q.")
        return
    lines = ["🏅 <b>UNVONLAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for t in all_titles:
        name = t.get("full_name") or t.get("username") or str(t["user_id"])
        lines.append(f"• <code>{t['user_id']}</code> {name} — 🏅 <b>{t['title']}</b>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def received_rarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Eski rarity callback - endi handle_admin_callback ga yo'naltirildi"""
    pass
