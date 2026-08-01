"""
To'liq Admin Panel — original zip uslubida (flat tugmalar),
lekin barcha yangi funksiyalar: events, waifu groups, rarity, narx, ID tahrirlash qo'shilgan.
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

# ══════════════════════════════════════════════════════
#  PANEL TUGMALARI — original uslub (flat)
# ══════════════════════════════════════════════════════
BTN_ADDWAIFU  = "➕ Waifu qo'shish"
BTN_RMWAIFU   = "🗑 Waifular ro'yxati"
BTN_FINDWAIFU = "🔍 Waifu topish"
BTN_WAIFU_GRP = "📂 Guruhlar"
BTN_ADDCH     = "📢 Kanal qo'shish"
BTN_RMCH      = "❌ Kanal o'chirish"
BTN_COINS     = "💰 Coin berish"
BTN_GIVEW     = "🎴 Waifu berish"
BTN_BAN       = "🚫 Ban"
BTN_UNBAN     = "✅ Unban"
BTN_BROADCAST = "📣 Broadcast"
BTN_EVENT     = "⚡ Event"
BTN_STATS     = "📊 Statistika"
BTN_SPAWN     = "🔧 Spawn"
BTN_TITLE     = "🏅 Unvon berish"
BTN_USERS     = "👥 A'zolar"
BTN_ADDADMIN  = "👑 Admin qo'shish"
BTN_RMADMIN   = "🔴 Admin o'chirish"
BTN_ADDSUBADM = "🟡 Sub-Admin qo'shish"
BTN_ADDGROUP  = "🔓 Guruh qo'shish"
BTN_CLOSE     = "🚪 Panelni yopish"

# Sub-admin faqat ko'ra oladigan tugmalar
SUB_ADMIN_BUTTONS = {BTN_ADDWAIFU, BTN_RMWAIFU, BTN_CLOSE}

ALL_PANEL_BUTTONS = {
    BTN_ADDWAIFU, BTN_RMWAIFU, BTN_FINDWAIFU, BTN_WAIFU_GRP,
    BTN_ADDCH, BTN_RMCH, BTN_COINS, BTN_GIVEW,
    BTN_BAN, BTN_UNBAN, BTN_BROADCAST, BTN_EVENT,
    BTN_STATS, BTN_SPAWN, BTN_TITLE, BTN_USERS,
    BTN_ADDADMIN, BTN_RMADMIN, BTN_ADDSUBADM, BTN_ADDGROUP,
    BTN_CLOSE,
}

SUB_ADMIN_BLOCKED_RARITY = {"Mythick", "Legendary", "Premium", "Exclusive", "Divine"}

# ══════════════════════════════════════════════════════
#  STATE MACHINE
# ══════════════════════════════════════════════════════
ADM_STATE = "adm_state"
ADM_DATA  = "adm_data"

S_NONE = None

# Waifu qo'shish
S_PHOTO      = "addwaifu_photo"
S_NAME       = "addwaifu_name"
S_ANIME      = "addwaifu_anime"
S_PRICE      = "addwaifu_price"
S_GROUP_SEL  = "addwaifu_group_sel"   # inline rarity tanlash kutiladi

# Waifu tahrirlash
S_FIND_ID    = "find_waifu_id"
S_EDIT_VAL   = "edit_waifu_val"
S_EDIT_PHOTO = "edit_waifu_photo"

# Waifu guruhi
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

# Barcha matnli state-lar (foto kutilmaydi)
_TEXT_STATES = {
    S_NAME, S_ANIME, S_PRICE, S_FIND_ID, S_EDIT_VAL,
    S_NEW_GROUP_NAME, S_NEW_GROUP_DESC,
    S_EVENT_NAME, S_EVENT_TYPE, S_EVENT_DESC, S_EVENT_TRIGGER,
    S_EW_NAME, S_EW_ANIME, S_EW_PRICE,
    S_BAN, S_UNBAN, S_COINS_UID, S_COINS_AMT,
    S_GIVEW_UID, S_GIVEW_WID, S_BROADCAST,
    S_ADDADMIN, S_ADDSUBADM, S_RMADMIN,
    S_ADDCH_ID, S_ADDCH_NAME,
    S_TITLE_UID, S_TITLE_TXT, S_SPAWN_SET, S_ADDGROUP_BP,
}


# ══════════════════════════════════════════════════════
#  KLAVIATURALAR — original flat uslub
# ══════════════════════════════════════════════════════

def _panel_kb(role: str) -> ReplyKeyboardMarkup:
    if role == "sub":
        rows = [
            [BTN_ADDWAIFU],
            [BTN_RMWAIFU],
            [BTN_CLOSE],
        ]
    elif role == "god":
        rows = [
            [BTN_ADDWAIFU, BTN_RMWAIFU],
            [BTN_FINDWAIFU, BTN_WAIFU_GRP],
            [BTN_ADDCH, BTN_RMCH],
            [BTN_COINS, BTN_GIVEW],
            [BTN_BAN, BTN_UNBAN],
            [BTN_BROADCAST, BTN_EVENT],
            [BTN_STATS, BTN_SPAWN],
            [BTN_TITLE, BTN_USERS],
            [BTN_ADDADMIN, BTN_ADDSUBADM],
            [BTN_RMADMIN, BTN_ADDGROUP],
            [BTN_CLOSE],
        ]
    else:  # admin
        rows = [
            [BTN_ADDWAIFU, BTN_RMWAIFU],
            [BTN_FINDWAIFU, BTN_WAIFU_GRP],
            [BTN_COINS, BTN_GIVEW],
            [BTN_BAN, BTN_UNBAN],
            [BTN_BROADCAST, BTN_EVENT],
            [BTN_STATS, BTN_SPAWN],
            [BTN_TITLE, BTN_USERS],
            [BTN_ADDCH, BTN_RMCH],
            [BTN_CLOSE],
        ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def _clear_state(ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.pop(ADM_STATE, None)
    ctx.user_data.pop(ADM_DATA, None)


async def _get_role(uid: int) -> str:
    return await log_db.get_admin_role(uid) or ""


async def require_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    u = update.effective_user
    if not await log_db.is_admin(u.id):
        if update.message:
            await update.message.reply_text("❌ Ruxsatingiz yo'q.")
        return False
    return True


async def require_full_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    u = update.effective_user
    if not await log_db.is_full_admin(u.id):
        if update.message:
            await update.message.reply_text("❌ Faqat to'liq admin.")
        return False
    return True


# ══════════════════════════════════════════════════════
#  PANEL KOMANDASI
# ══════════════════════════════════════════════════════

async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    u = update.effective_user
    role = await _get_role(u.id)
    _clear_state(context)
    role_label = {"god": "👑 God Admin", "admin": "🔧 Admin", "sub": "🟡 Sub-Admin"}.get(role, "Admin")
    kb = _panel_kb(role)
    await update.message.reply_text(
        f"🛡 <b>ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {u.full_name} — {role_label}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Amalni tanlang:",
        parse_mode="HTML",
        reply_markup=kb
    )


# ══════════════════════════════════════════════════════
#  WAIFU RO'YXATI
# ══════════════════════════════════════════════════════

async def _show_waifu_list(message, page=0, owner_id=None, group_id=None, title="🗑 WAIFULAR"):
    if owner_id:
        total = await waifu_db.count_waifus_by_admin(owner_id)
        waifus = await waifu_db.get_waifus_by_admin(owner_id, PAGE_SIZE, page * PAGE_SIZE)
    else:
        total = await waifu_db.count_all_active()
        waifus = await waifu_db.get_all_waifus_paginated(PAGE_SIZE, page * PAGE_SIZE, group_id)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if not waifus:
        await message.reply_text("📭 Waifular yo'q.")
        return
    lines = [f"<b>{title}</b> [{page+1}/{pages}] — jami: {total}\n━━━━━━━━━━━━━━━━━━━━"]
    btns = []
    for w in waifus:
        emoji = get_rarity_emoji(w['rarity'])
        grp = f" [{w.get('group_name','—')}]" if w.get('group_name') else ""
        price = f" 💰{w.get('price',0):,}" if w.get('price') else ""
        lines.append(f"{emoji} <code>#{w['waifu_id']}</code> <b>{w['name']}</b>{grp}{price}")
        btns.append([
            InlineKeyboardButton(f"✏️ {w['name'][:14]}", callback_data=f"adm_edit_{w['waifu_id']}"),
            InlineKeyboardButton("🗑", callback_data=f"adm_del_{w['waifu_id']}"),
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"adm_wlist_{page-1}_{owner_id or 0}_{group_id or 0}"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"adm_wlist_{page+1}_{owner_id or 0}_{group_id or 0}"))
    if nav:
        btns.append(nav)
    await message.reply_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(btns) if btns else None
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
        f"━━━━━━━━━━━━━━━━━━━━"
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
        [InlineKeyboardButton("🗑 O'chirish", callback_data=f"adm_del_{waifu_id}")],
    ])
    await message.reply_photo(
        photo=waifu['file_id'], caption=text,
        parse_mode="HTML", reply_markup=kb
    )


# ══════════════════════════════════════════════════════
#  GURUHLAR
# ══════════════════════════════════════════════════════

async def _show_groups(message):
    gs = await waifu_db.get_all_groups_list()
    btns = []
    lines = ["📂 <b>WAIFU GURUHLARI</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for g in gs:
        cnt = await waifu_db.count_waifus_in_group(g['id'])
        lines.append(f"• <b>{g['name']}</b> — {cnt} ta waifu")
        btns.append([
            InlineKeyboardButton(f"📋 {g['name'][:14]}", callback_data=f"adm_grplist_{g['id']}"),
            InlineKeyboardButton("🗑", callback_data=f"adm_grpdel_{g['id']}"),
        ])
    btns.append([InlineKeyboardButton("➕ Yangi guruh", callback_data="adm_newgroup")])
    text = "\n".join(lines) if gs else "📂 Guruhlar yo'q"
    await message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))


# ══════════════════════════════════════════════════════
#  STATISTIKA
# ══════════════════════════════════════════════════════

async def _show_stats(message):
    counts = await waifu_db.count_waifus_by_rarity()
    total_w = sum(counts.values())
    users = await user_db.get_all_users()
    from database.market import count_active_listings
    market_c = await count_active_listings()
    ch_c = await log_db.get_required_channels_count()
    active_ev = await event_db.get_active_event()
    all_ev = await event_db.get_all_events()
    gs = await waifu_db.get_all_groups_list()
    lines = [
        "📊 <b>BOT STATISTIKASI</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👥 Foydalanuvchilar: <b>{len(users)}</b>",
        f"🎴 Jami waifular: <b>{total_w}</b>",
        f"📂 Waifu guruhlari: <b>{len(gs)}</b>",
        f"🛒 Bozorda: <b>{market_c}</b>",
        f"📢 Majburiy kanallar: <b>{ch_c}</b>",
        f"⚡ Eventlar: <b>{len(all_ev)}</b>",
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
        ]
    await message.reply_text("\n".join(lines), parse_mode="HTML")


# ══════════════════════════════════════════════════════
#  A'ZOLAR
# ══════════════════════════════════════════════════════

async def _show_users(message):
    all_ids = await user_db.get_all_users()
    top = await user_db.get_top_users(10, "total_caught")
    admins = await log_db.get_admins()
    role_mark = {"god": "👑", "admin": "🔧", "sub": "🟡"}
    lines = [
        "👥 <b>BOT A'ZOLARI</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"Jami: <b>{len(all_ids)}</b> foydalanuvchi", "",
        "🛡️ <b>Adminlar:</b>",
    ]
    for a in admins:
        r = a.get("role") or "admin"
        uname = f"@{a['username']}" if a.get("username") else ""
        lines.append(f"{role_mark.get(r,'🔧')} <code>{a['user_id']}</code> {uname}")
    lines += ["", "🏆 <b>Top 10:</b>"]
    medals = ["🥇","🥈","🥉"] + [f"{i}." for i in range(4,11)]
    for i, u in enumerate(top):
        name = u.get("full_name") or u.get("username") or str(u["user_id"])
        lines.append(f"{medals[i]} <code>{u['user_id']}</code> {name} — {u['total_caught']} waifu")
    await message.reply_text("\n".join(lines), parse_mode="HTML")


# ══════════════════════════════════════════════════════
#  EVENTLAR
# ══════════════════════════════════════════════════════

async def _show_events(message):
    events = await event_db.get_all_events()
    active_ev = await event_db.get_active_event()
    active_id = active_ev['id'] if active_ev else None
    btns = []
    lines = ["⚡ <b>EVENTLAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for e in events:
        wcs = await event_db.get_event_waifus(e['id'])
        status = "🟢" if e['id'] == active_id else "🔴"
        lines.append(
            f"{status} <b>{e['name']}</b> [{e['event_type']}] — {len(wcs)} waifu\n"
            f"   📋 {e.get('description','—')} | Har {e['trigger_every']} xabarda"
        )
        row = []
        if e['id'] == active_id:
            row.append(InlineKeyboardButton("⏹ O'chirish", callback_data=f"adm_evoff_{e['id']}"))
        else:
            row.append(InlineKeyboardButton("▶️ Yoqish", callback_data=f"adm_evon_{e['id']}"))
        row.append(InlineKeyboardButton("🎴 Waifular", callback_data=f"adm_evwaifus_{e['id']}"))
        row.append(InlineKeyboardButton("🗑", callback_data=f"adm_evdel_{e['id']}"))
        btns.append(row)
    btns.append([InlineKeyboardButton("➕ Yangi event", callback_data="adm_create_event")])
    if not events:
        lines = ["⚡ Eventlar yo'q"]
    await message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))


async def _show_event_waifus(msg_or_query, event_id: int):
    ev = await event_db.get_event_by_id(event_id)
    if not ev:
        return
    ws = await event_db.get_event_waifus(event_id)
    lines = [f"🎴 <b>{ev['name']} — Waifular</b>\n━━━━━━━━━━━━━━━━━━━━"]
    btns = []
    for ew in ws:
        emoji = get_rarity_emoji(ew['rarity'])
        price = ew.get('price',0) or 0
        lines.append(f"{emoji} <b>{ew['name']}</b> | {ew['anime']} | 💰{price:,}")
        btns.append([InlineKeyboardButton(
            f"🗑 {ew['name'][:15]}", callback_data=f"adm_ewdel_{ew['id']}_{event_id}"
        )])
    btns.append([
        InlineKeyboardButton("➕ Waifu qo'shish", callback_data=f"adm_addew_{event_id}"),
        InlineKeyboardButton("⬅️ Orqaga", callback_data="adm_evlist_back"),
    ])
    text = "\n".join(lines) if ws else f"🎴 <b>{ev['name']}</b> — waifular yo'q"
    kb = InlineKeyboardMarkup(btns)
    if hasattr(msg_or_query, 'edit_message_text'):
        try:
            await msg_or_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await msg_or_query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await msg_or_query.reply_text(text, parse_mode="HTML", reply_markup=kb)


# ══════════════════════════════════════════════════════
#  PANEL TUGMA HANDLERI (ReplyKeyboard)
# ══════════════════════════════════════════════════════

async def handle_panel_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text or ""
    if text not in ALL_PANEL_BUTTONS:
        return
    if not await log_db.is_admin(user.id):
        await update.message.reply_text("❌ Ruxsatingiz yo'q.", reply_markup=ReplyKeyboardRemove())
        return
    role = await _get_role(user.id)
    kb = _panel_kb(role)
    is_sub = (role == "sub")

    # Jarayon davom etayotganda panel tugmasini bosish
    state = context.user_data.get(ADM_STATE)
    if state in _TEXT_STATES or state == S_GROUP_SEL:
        state_hints = {
            S_PHOTO: "📸 Rasmni yuboring (yoki /cancel).",
            S_NAME: "📝 Ismni kiriting (yoki /cancel).",
            S_ANIME: "🎌 Anime nomini kiriting (yoki /cancel).",
            S_PRICE: "💰 Narxni kiriting (yoki /cancel).",
            S_GROUP_SEL: "⭐ Rarity tugmasini bosing (yoki /cancel).",
            S_FIND_ID: "🔍 Waifu ID kiriting (yoki /cancel).",
            S_EDIT_VAL: "📝 Yangi qiymatni kiriting (yoki /cancel).",
            S_BAN: "🚫 User ID va sabab kiriting (yoki /cancel).",
            S_UNBAN: "✅ User ID kiriting (yoki /cancel).",
            S_COINS_UID: "💰 User ID kiriting (yoki /cancel).",
            S_COINS_AMT: "💰 Miqdorni kiriting (yoki /cancel).",
            S_GIVEW_UID: "🎴 User ID kiriting (yoki /cancel).",
            S_GIVEW_WID: "🎴 Waifu ID kiriting (yoki /cancel).",
            S_BROADCAST: "📣 Xabar kiriting (yoki /cancel).",
            S_ADDADMIN: "👑 User ID kiriting (yoki /cancel).",
            S_ADDSUBADM: "🟡 User ID kiriting (yoki /cancel).",
            S_RMADMIN: "🔴 User ID kiriting (yoki /cancel).",
            S_ADDCH_ID: "📢 Kanal ID kiriting (yoki /cancel).",
            S_ADDCH_NAME: "📛 Kanal nomini kiriting (yoki /cancel).",
            S_TITLE_UID: "🏅 User ID kiriting (yoki /cancel).",
            S_TITLE_TXT: "🏅 Unvon matni kiriting (yoki /cancel).",
            S_SPAWN_SET: "🔧 Spawn sonini kiriting (yoki /cancel).",
            S_ADDGROUP_BP: "🔓 Guruh ID kiriting (yoki /cancel).",
            S_NEW_GROUP_NAME: "📂 Guruh nomini kiriting (yoki /cancel).",
            S_NEW_GROUP_DESC: "📝 Tavsif kiriting (yoki /cancel).",
            S_EVENT_NAME: "🆕 Event nomini kiriting (yoki /cancel).",
            S_EVENT_TYPE: "🏷 Event turini kiriting (yoki /cancel).",
            S_EVENT_DESC: "📋 Tavsif kiriting (yoki /cancel).",
            S_EVENT_TRIGGER: "🔢 Trigger sonini kiriting (yoki /cancel).",
            S_EW_PHOTO: "📸 Event waifu rasmini yuboring (yoki /cancel).",
            S_EW_NAME: "📝 Event waifu ismini kiriting (yoki /cancel).",
            S_EW_ANIME: "🎌 Anime nomini kiriting (yoki /cancel).",
            S_EW_PRICE: "💰 Narxni kiriting (yoki /cancel).",
        }
        hint = state_hints.get(state, "Jarayon davom etmoqda. /cancel deb yozing.")
        await update.message.reply_text(hint, reply_markup=kb)
        return

    # Sub-admin cheklov
    if is_sub and text not in SUB_ADMIN_BUTTONS:
        await update.message.reply_text("🚫 Sub-admin bu amalni bajara olmaydi.", reply_markup=kb)
        return

    # ── Yopish ──
    if text == BTN_CLOSE:
        _clear_state(context)
        await update.message.reply_text("✅ Panel yopildi.", reply_markup=ReplyKeyboardRemove())
        return

    # ── Waifu qo'shish ──
    if text == BTN_ADDWAIFU:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_PHOTO
        await update.message.reply_text(
            "📸 <b>WAIFU QO'SHISH</b>\n\nWaifu rasmini yuboring:\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Waifular ro'yxati ──
    if text == BTN_RMWAIFU:
        _clear_state(context)
        owner = user.id if is_sub else None
        await _show_waifu_list(update.message, page=0, owner_id=owner)
        return

    # ── Waifu topish ──
    if text == BTN_FINDWAIFU:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_FIND_ID
        await update.message.reply_text(
            "🔍 <b>WAIFU TOPISH</b>\n\nWaifu ID raqamini kiriting:\nMisol: <code>42</code>\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Waifu guruhlari ──
    if text == BTN_WAIFU_GRP:
        _clear_state(context)
        await _show_groups(update.message)
        return

    # ── Majburiy kanallar: qo'shish ──
    if text == BTN_ADDCH:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_ADDCH_ID
        # Hozirgi kanallar ro'yxatini ham ko'rsat
        channels = await grp_db.get_required_channels()
        lines = ["📢 <b>MAJBURIY KANALLAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
        if channels:
            for ch in channels:
                name = ch.get("channel_name") or ch["channel_id"]
                lines.append(f"• {name} (<code>{ch['channel_id']}</code>)")
        else:
            lines.append("Hozircha majburiy kanal yo'q.")
        lines.append("\n━━━━━━━━━━━━━━━━━━━━\nYangi kanal ID kiriting:\n(@channel yoki -100...)\n\n/cancel — bekor qilish")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=kb)
        return

    # ── Majburiy kanallar: o'chirish ──
    if text == BTN_RMCH:
        _clear_state(context)
        channels = await grp_db.get_required_channels()
        if not channels:
            await update.message.reply_text("📋 Majburiy kanallar yo'q.", reply_markup=kb)
            return
        rows = []
        for ch in channels:
            name = ch.get("channel_name") or ch["channel_id"]
            rows.append([InlineKeyboardButton(f"❌ {name}", callback_data=f"adm_rmch_{ch['channel_id']}")])
        await update.message.reply_text(
            "📋 <b>Qaysi kanalni o'chirmoqchisiz?</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(rows)
        )
        return

    # ── Coin berish ──
    if text == BTN_COINS:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_COINS_UID
        await update.message.reply_text("💰 <b>Coin berish</b>\n\nUser ID kiriting:", parse_mode="HTML", reply_markup=kb)
        return

    # ── Waifu berish ──
    if text == BTN_GIVEW:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_GIVEW_UID
        await update.message.reply_text("🎴 <b>Waifu berish</b>\n\nUser ID kiriting:", parse_mode="HTML", reply_markup=kb)
        return

    # ── Ban ──
    if text == BTN_BAN:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_BAN
        await update.message.reply_text(
            "🚫 <b>BAN</b>\n\nUser ID va sabab kiriting:\n<code>123456789 Sabab</code>",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Unban ──
    if text == BTN_UNBAN:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_UNBAN
        await update.message.reply_text("✅ <b>Unban</b>\n\nUser ID kiriting:", parse_mode="HTML", reply_markup=kb)
        return

    # ── Broadcast ──
    if text == BTN_BROADCAST:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_BROADCAST
        all_users = await user_db.get_all_users()
        await update.message.reply_text(
            f"📣 <b>BROADCAST</b>\n\nJami: <b>{len(all_users)}</b> foydalanuvchi\n\nXabarni kiriting:\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Event ──
    if text == BTN_EVENT:
        _clear_state(context)
        await _show_events(update.message)
        return

    # ── Statistika ──
    if text == BTN_STATS:
        _clear_state(context)
        await _show_stats(update.message)
        return

    # ── Spawn ──
    if text == BTN_SPAWN:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_SPAWN_SET
        from utils.helpers import get_bot_group_id
        gid = get_bot_group_id()
        cur = await grp_db.get_spawn_threshold(gid) if gid else "?"
        await update.message.reply_text(
            f"🔧 <b>SPAWN</b>\n\nHozirgi chegara: <b>{cur}</b>\n"
            f"Har N ta xabarda 1 ta waifu paydo bo'ladi.\n\nYangi sonni kiriting:\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Unvon berish ──
    if text == BTN_TITLE:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_TITLE_UID
        await update.message.reply_text("🏅 <b>Unvon berish</b>\n\nUser ID kiriting:", parse_mode="HTML", reply_markup=kb)
        return

    # ── A'zolar ──
    if text == BTN_USERS:
        _clear_state(context)
        await _show_users(update.message)
        return

    # ── Admin qo'shish ──
    if text == BTN_ADDADMIN:
        if not is_god_admin(user.id):
            await update.message.reply_text("❌ Faqat God Admin.", reply_markup=kb)
            return
        _clear_state(context)
        context.user_data[ADM_STATE] = S_ADDADMIN
        await update.message.reply_text(
            "👑 <b>Admin qo'shish</b>\n\nUser ID kiriting:\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Sub-Admin qo'shish ──
    if text == BTN_ADDSUBADM:
        if not is_god_admin(user.id):
            await update.message.reply_text("❌ Faqat God Admin.", reply_markup=kb)
            return
        _clear_state(context)
        context.user_data[ADM_STATE] = S_ADDSUBADM
        await update.message.reply_text(
            "🟡 <b>Sub-Admin qo'shish</b>\n\nUser ID kiriting:\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Admin o'chirish ──
    if text == BTN_RMADMIN:
        if not is_god_admin(user.id):
            await update.message.reply_text("❌ Faqat God Admin.", reply_markup=kb)
            return
        _clear_state(context)
        context.user_data[ADM_STATE] = S_RMADMIN
        await update.message.reply_text(
            "🔴 <b>Admin o'chirish</b>\n\nUser ID kiriting:\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Guruh bypass ──
    if text == BTN_ADDGROUP:
        if not is_god_admin(user.id):
            await update.message.reply_text("❌ Faqat God Admin.", reply_markup=kb)
            return
        _clear_state(context)
        context.user_data[ADM_STATE] = S_ADDGROUP_BP
        await update.message.reply_text(
            "🔓 <b>Guruh bypass</b>\n\nGuruh ID kiriting:\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb
        )
        return


# ══════════════════════════════════════════════════════
#  MATN HANDLERI — state machine
# ══════════════════════════════════════════════════════

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user = update.effective_user
    text = (update.message.text or "").strip()
    if text in ALL_PANEL_BUTTONS:
        return
    if not await log_db.is_admin(user.id):
        return
    state = context.user_data.get(ADM_STATE)
    if state not in _TEXT_STATES:
        return
    role = await _get_role(user.id)
    kb = _panel_kb(role)

    if text.lower() == "/cancel":
        _clear_state(context)
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=kb)
        return

    # ── Waifu qo'shish: ism ──
    if state == S_NAME:
        context.user_data[ADM_DATA]["name"] = text
        context.user_data[ADM_STATE] = S_ANIME
        await update.message.reply_text("🎌 Anime nomini kiriting:", reply_markup=kb)
        return

    # ── Waifu qo'shish: anime ──
    if state == S_ANIME:
        context.user_data[ADM_DATA]["anime"] = text
        context.user_data[ADM_STATE] = S_PRICE
        await update.message.reply_text(
            "💰 Waifu narxini kiriting (coin, 0 = bepul):", reply_markup=kb
        )
        return

    # ── Waifu qo'shish: narx → rarity tanlash ──
    if state == S_PRICE:
        try:
            price = int(text.replace(",","").replace(" ",""))
        except ValueError:
            price = 0
        context.user_data[ADM_DATA]["price"] = price
        is_sub = (role == "sub")
        blocked = {"Divine"} | (SUB_ADMIN_BLOCKED_RARITY if is_sub else set())
        available = [r for r in RARITY_ORDER if r not in blocked]
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{get_rarity_emoji(r)} {r} ({RARITY_CONFIG[r]['percent']})",
                callback_data=f"rarity_{r}"
            )]
            for r in available
        ])
        context.user_data[ADM_STATE] = S_GROUP_SEL
        await update.message.reply_text("⭐ <b>Darajani tanlang:</b>", parse_mode="HTML", reply_markup=keyboard)
        return

    # ── Waifu topish ──
    if state == S_FIND_ID:
        wid = text.lstrip("#")
        waifu = await waifu_db.get_waifu(wid) or await waifu_db.get_waifu_any(wid)
        if not waifu:
            # Ism bo'yicha qidirish
            results = await waifu_db.search_waifus(wid, limit=5)
            if results:
                lines = [f"🔍 <b>'{wid}' bo'yicha topildi:</b>\n"]
                btns = []
                for w in results:
                    emoji = get_rarity_emoji(w['rarity'])
                    lines.append(f"{emoji} <code>#{w['waifu_id']}</code> <b>{w['name']}</b>")
                    btns.append([InlineKeyboardButton(
                        f"✏️ {w['name'][:20]}", callback_data=f"adm_edit_{w['waifu_id']}"
                    )])
                _clear_state(context)
                await update.message.reply_text("\n".join(lines), parse_mode="HTML",
                                                reply_markup=InlineKeyboardMarkup(btns))
            else:
                await update.message.reply_text(f"❌ #{wid} topilmadi.", reply_markup=kb)
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
                val = int(text.replace(",","").replace(" ",""))
            except ValueError:
                await update.message.reply_text("❌ Faqat raqam:", reply_markup=kb)
                return
        else:
            val = text
        await waifu_db.edit_waifu(wid, **{field: val})
        _clear_state(context)
        await update.message.reply_text(
            f"✅ #{wid} — <b>{field}</b> yangilandi!", parse_mode="HTML", reply_markup=kb
        )
        await _show_waifu_edit_menu(update.message, wid)
        return

    # ── Yangi guruh: nom ──
    if state == S_NEW_GROUP_NAME:
        context.user_data[ADM_DATA] = {"group_name": text}
        context.user_data[ADM_STATE] = S_NEW_GROUP_DESC
        await update.message.reply_text("📝 Guruh tavsifini kiriting (- = yo'q):", reply_markup=kb)
        return

    if state == S_NEW_GROUP_DESC:
        data = context.user_data.get(ADM_DATA, {})
        gname = data.get("group_name", "Nomsiz")
        desc = "" if text == "-" else text
        gid = await waifu_db.create_group(gname, desc, user.id)
        _clear_state(context)
        if gid:
            await update.message.reply_text(f"✅ Guruh <b>{gname}</b> yaratildi!", parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text("❌ Xatolik (nom takrorlangan bo'lishi mumkin).", reply_markup=kb)
        return

    # ── Event yaratish ──
    if state == S_EVENT_NAME:
        context.user_data[ADM_DATA] = {"event_name": text}
        context.user_data[ADM_STATE] = S_EVENT_TYPE
        await update.message.reply_text(
            "🏷 Event turini kiriting:\nMisol: <i>Festival, Bayram, Special</i>",
            parse_mode="HTML", reply_markup=kb
        )
        return

    if state == S_EVENT_TYPE:
        context.user_data[ADM_DATA]["event_type"] = text
        context.user_data[ADM_STATE] = S_EVENT_DESC
        await update.message.reply_text("📋 Tavsif kiriting (- = yo'q):", reply_markup=kb)
        return

    if state == S_EVENT_DESC:
        desc = "" if text == "-" else text
        context.user_data[ADM_DATA]["event_desc"] = desc
        context.user_data[ADM_STATE] = S_EVENT_TRIGGER
        await update.message.reply_text(
            "🔢 Har necha xabarda event waifu chiqsin?\n"
            "Misol: <code>50</code> — har 50 xabarda 1 ta\n\n/cancel — bekor qilish",
            parse_mode="HTML", reply_markup=kb
        )
        return

    if state == S_EVENT_TRIGGER:
        try:
            trigger = max(1, int(text.replace(" ","")))
        except ValueError:
            await update.message.reply_text("❌ Faqat musbat raqam:", reply_markup=kb)
            return
        data = context.user_data.get(ADM_DATA, {})
        eid = await event_db.create_event(
            name=data.get("event_name","Event"),
            event_type=data.get("event_type","Custom"),
            description=data.get("event_desc",""),
            trigger_every=trigger,
            created_by=user.id
        )
        _clear_state(context)
        if eid:
            await update.message.reply_text(
                f"✅ Event <b>{data.get('event_name')}</b> yaratildi!\n"
                f"Endi waifular qo'shing 👇",
                parse_mode="HTML", reply_markup=kb
            )
            await _show_event_waifus(update.message, eid)
        else:
            await update.message.reply_text("❌ Xatolik yuz berdi.", reply_markup=kb)
        return

    # ── Event waifu ──
    if state == S_EW_NAME:
        context.user_data[ADM_DATA]["ew_name"] = text
        context.user_data[ADM_STATE] = S_EW_ANIME
        await update.message.reply_text("🎌 Anime nomini kiriting:", reply_markup=kb)
        return

    if state == S_EW_ANIME:
        context.user_data[ADM_DATA]["ew_anime"] = text
        context.user_data[ADM_STATE] = S_EW_PRICE
        await update.message.reply_text("💰 Narxini kiriting (0 = bepul):", reply_markup=kb)
        return

    if state == S_EW_PRICE:
        try:
            price = int(text.replace(",","").replace(" ",""))
        except ValueError:
            price = 0
        context.user_data[ADM_DATA]["ew_price"] = price
        kb_rar = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_rarity_emoji(r)} {r}", callback_data=f"ewrar_{r}")]
            for r in RARITY_ORDER
        ])
        context.user_data[ADM_STATE] = None  # inline kutish
        await update.message.reply_text("⭐ Event waifu darajasini tanlang:", reply_markup=kb_rar)
        return

    # ── Foydalanuvchi ──
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
            parse_mode="HTML", reply_markup=kb
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
        await update.message.reply_text(f"✅ <code>{uid}</code> blokdan chiqarildi!", parse_mode="HTML", reply_markup=kb)
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
            f"💰 <code>{uid}</code>\nHozirgi coin: <b>{current}</b>\n\nNecha coin berish?",
            parse_mode="HTML", reply_markup=kb
        )
        return

    if state == S_COINS_AMT:
        try:
            amount = int(text.replace(",","").replace(" ",""))
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
            parse_mode="HTML", reply_markup=kb
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
            f"🎴 <code>{uid}</code> ga qaysi waifu?\nWaifu ID (<code>#raqam</code>) kiriting:",
            parse_mode="HTML", reply_markup=kb
        )
        return

    if state == S_GIVEW_WID:
        wid = text.lstrip("#")
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
            parse_mode="HTML", reply_markup=kb
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
        await update.message.reply_text(f"🏅 <code>{uid}</code> uchun unvon matni:", parse_mode="HTML", reply_markup=kb)
        return

    if state == S_TITLE_TXT:
        uid = context.user_data.get(ADM_DATA, {}).get("uid")
        if not uid:
            _clear_state(context)
            return
        await title_db.set_title(uid, text, user.id)
        _clear_state(context)
        await update.message.reply_text(
            f"✅ <code>{uid}</code>\n🏅 <b>{text}</b>",
            parse_mode="HTML", reply_markup=kb
        )
        return

    if state == S_BROADCAST:
        all_users = await user_db.get_all_users()
        sent = 0; failed = 0
        for uid in all_users:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)
        _clear_state(context)
        await update.message.reply_text(
            f"📣 Broadcast tugadi!\n✅ {sent}\n❌ {failed}", reply_markup=kb
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
        await update.message.reply_text(f"✅ <code>{uid}</code> admin qilindi!", parse_mode="HTML", reply_markup=kb)
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
        await update.message.reply_text(f"✅ <code>{uid}</code> sub-admin qilindi!", parse_mode="HTML", reply_markup=kb)
        return

    if state == S_RMADMIN:
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam:")
            return
        await log_db.remove_admin(uid)
        _clear_state(context)
        await update.message.reply_text(f"✅ <code>{uid}</code> o'chirildi!", parse_mode="HTML", reply_markup=kb)
        return

    if state == S_ADDCH_ID:
        context.user_data[ADM_DATA] = {"ch_id": text}
        context.user_data[ADM_STATE] = S_ADDCH_NAME
        await update.message.reply_text("📛 Kanal nomini kiriting:", reply_markup=kb)
        return

    if state == S_ADDCH_NAME:
        ch_id = context.user_data.get(ADM_DATA, {}).get("ch_id")
        ch_name = text
        if ch_id:
            await grp_db.add_required_channel(ch_id, ch_name, "channel", user.id)
        _clear_state(context)
        await update.message.reply_text(
            f"✅ Majburiy kanal qo'shildi!\n📢 <b>{ch_name}</b> (<code>{ch_id}</code>)",
            parse_mode="HTML", reply_markup=kb
        )
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
            f"✅ Spawn chegarasi <b>{threshold}</b> ga o'rnatildi!\n"
            f"Har {threshold} ta xabarda 1 ta waifu paydo bo'ladi.",
            parse_mode="HTML", reply_markup=kb
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
        await update.message.reply_text(f"✅ Guruh <code>{gid}</code> bypass qilindi!", parse_mode="HTML", reply_markup=kb)
        return


# ══════════════════════════════════════════════════════
#  RASM HANDLERI
# ══════════════════════════════════════════════════════

async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return
    user = update.effective_user
    if not await log_db.is_admin(user.id):
        return
    state = context.user_data.get(ADM_STATE)
    role = await _get_role(user.id)
    kb = _panel_kb(role)
    photo = update.message.photo[-1]

    if state == S_PHOTO:
        context.user_data[ADM_DATA] = {"file_id": photo.file_id}
        context.user_data[ADM_STATE] = S_NAME
        await update.message.reply_text("📝 Waifu ismini kiriting:", reply_markup=kb)
        return

    if state == S_EDIT_PHOTO:
        data = context.user_data.get(ADM_DATA, {})
        wid = data.get("wid")
        if wid:
            await waifu_db.edit_waifu(wid, file_id=photo.file_id)
            _clear_state(context)
            await update.message.reply_text(f"✅ #{wid} rasmi yangilandi!", reply_markup=kb)
            await _show_waifu_edit_menu(update.message, wid)
        return

    if state == S_EW_PHOTO:
        context.user_data[ADM_DATA]["ew_file_id"] = photo.file_id
        context.user_data[ADM_STATE] = S_EW_NAME
        await update.message.reply_text("📝 Event waifu ismini kiriting:", reply_markup=kb)
        return


# ══════════════════════════════════════════════════════
#  INLINE CALLBACK HANDLERI
# ══════════════════════════════════════════════════════

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
        if state != S_GROUP_SEL:
            await query.answer("❌ Noto'g'ri holat.", show_alert=True)
            return
        context.user_data[ADM_DATA]["rarity"] = rarity
        gs = await waifu_db.get_all_groups_list()
        if gs:
            rows = [[InlineKeyboardButton("— Guruhsiz —", callback_data="wgrp_none")]]
            for g in gs:
                cnt = await waifu_db.count_waifus_in_group(g['id'])
                rows.append([InlineKeyboardButton(f"📂 {g['name']} ({cnt})", callback_data=f"wgrp_{g['id']}")])
            await query.edit_message_text("📂 Guruh tanlang:", reply_markup=InlineKeyboardMarkup(rows))
        else:
            await _finalize_add_waifu(query, context, user, role, group_id=None)
        return

    # ── Guruh tanlash ──
    if data.startswith("wgrp_"):
        gid_str = data[5:]
        group_id = None if gid_str == "none" else int(gid_str)
        await _finalize_add_waifu(query, context, user, role, group_id=group_id)
        return

    # ── Waifu o'chirish ──
    if data.startswith("adm_del_"):
        wid = data[8:]
        waifu = await waifu_db.get_waifu_any(wid)
        name = waifu['name'] if waifu else wid
        await waifu_db.remove_waifu(wid)
        await log_db.add_log("remove_waifu", user_id=user.id, details=f"waifu_id={wid}")
        await query.edit_message_text(f"🗑 <b>{name}</b> (#{wid}) o'chirildi!", parse_mode="HTML")
        return

    # ── Waifu sahifa ──
    if data.startswith("adm_wlist_"):
        parts = data.split("_")
        page = int(parts[3])
        owner_id_v = int(parts[4])
        group_id_v = int(parts[5])
        owner = owner_id_v if owner_id_v else None
        gid = group_id_v if group_id_v else None
        try:
            await query.delete_message()
        except Exception:
            pass
        await _show_waifu_list(update.effective_message, page=page, owner_id=owner, group_id=gid)
        return

    # ── Waifu tahrirlash menyu ──
    if data.startswith("adm_edit_"):
        wid = data[9:]
        try:
            await query.delete_message()
        except Exception:
            pass
        await _show_waifu_edit_menu(update.effective_message, wid)
        return

    # ── Field tanlash ──
    if data.startswith("adm_ef_"):
        parts = data.split("_", 4)
        field = parts[3]
        wid = parts[4]
        context.user_data[ADM_DATA] = {"wid": wid, "field": field}

        if field == "rarity":
            blocked = {"Divine"} | (SUB_ADMIN_BLOCKED_RARITY if is_sub else set())
            kb_rar = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"{get_rarity_emoji(r)} {r} ({RARITY_CONFIG[r]['percent']})",
                    callback_data=f"adm_efrar_{wid}_{r}"
                )]
                for r in RARITY_ORDER if r not in blocked
            ])
            try:
                await query.edit_message_caption("⭐ Yangi darajani tanlang:", reply_markup=kb_rar)
            except Exception:
                await query.edit_message_text("⭐ Yangi darajani tanlang:", reply_markup=kb_rar)
            return

        if field == "photo":
            context.user_data[ADM_STATE] = S_EDIT_PHOTO
            await query.answer("📸 Yangi rasmni yuboring", show_alert=True)
            return

        if field == "group":
            gs = await waifu_db.get_all_groups_list()
            rows = [[InlineKeyboardButton("— Guruhsiz —", callback_data=f"adm_efgset_{wid}_0")]]
            for g in gs:
                rows.append([InlineKeyboardButton(f"📂 {g['name']}", callback_data=f"adm_efgset_{wid}_{g['id']}")])
            try:
                await query.edit_message_caption("📂 Guruh tanlang:", reply_markup=InlineKeyboardMarkup(rows))
            except Exception:
                await query.edit_message_text("📂 Guruh tanlang:", reply_markup=InlineKeyboardMarkup(rows))
            return

        context.user_data[ADM_STATE] = S_EDIT_VAL
        hints = {"name": "📝 Yangi ism:", "anime": "🎌 Yangi anime:", "price": "💰 Yangi narx (son):"}
        await query.answer(hints.get(field, "Yangi qiymat:"), show_alert=True)
        return

    # ── Rarity yangilash ──
    if data.startswith("adm_efrar_"):
        parts = data.split("_", 4)
        wid = parts[3]
        rarity = parts[4]
        await waifu_db.edit_waifu(wid, rarity=rarity)
        try:
            await query.edit_message_caption(f"✅ #{wid} daraja → <b>{rarity}</b>", parse_mode="HTML")
        except Exception:
            await query.edit_message_text(f"✅ #{wid} daraja → <b>{rarity}</b>", parse_mode="HTML")
        return

    # ── Guruh yangilash ──
    if data.startswith("adm_efgset_"):
        parts = data.split("_")
        wid = parts[3]
        gid = None if parts[4] == "0" else int(parts[4])
        await waifu_db.edit_waifu(wid, group_id=gid)
        gname = "Guruhsiz" if not gid else (await waifu_db.get_group_by_id(gid) or {}).get('name', str(gid))
        try:
            await query.edit_message_caption(f"✅ #{wid} guruh → <b>{gname}</b>", parse_mode="HTML")
        except Exception:
            await query.edit_message_text(f"✅ #{wid} guruh → <b>{gname}</b>", parse_mode="HTML")
        return

    # ── Kanal o'chirish ──
    if data.startswith("adm_rmch_"):
        ch_id = data[9:]
        await grp_db.remove_required_channel(ch_id)
        await query.edit_message_text(f"✅ <code>{ch_id}</code> majburiy kanaldan o'chirildi!", parse_mode="HTML")
        return

    # ── Waifu guruhlari ──
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
        g = await waifu_db.get_group_by_id(gid)
        gname = g['name'] if g else f"#{gid}"
        try:
            await query.delete_message()
        except Exception:
            pass
        await _show_waifu_list(update.effective_message, page=0, group_id=gid, title=f"📂 {gname}")
        return

    if data.startswith("adm_grpdel_"):
        gid = int(data[11:])
        g = await waifu_db.get_group_by_id(gid)
        gname = g['name'] if g else str(gid)
        await waifu_db.delete_group(gid)
        await query.edit_message_text(f"🗑 Guruh <b>{gname}</b> o'chirildi!", parse_mode="HTML")
        return

    # ══════════════════════════════════════════════════════
    #  EVENT CALLBACKLAR
    # ══════════════════════════════════════════════════════

    if data.startswith("adm_evon_"):
        eid = int(data[9:])
        ev = await event_db.get_event_by_id(eid)
        ws = await event_db.get_event_waifus(eid)
        if not ws:
            await query.answer("❌ Eventga avval waifular qo'shing!", show_alert=True)
            return
        await event_db.activate_event(eid)
        await query.edit_message_text(
            f"🟢 <b>{ev['name']}</b> event yoqildi!\n"
            f"🎴 {len(ws)} ta waifu | Har {ev['trigger_every']} xabarda chiqadi",
            parse_mode="HTML"
        )
        return

    if data.startswith("adm_evoff_"):
        eid = int(data[10:])
        ev = await event_db.get_event_by_id(eid)
        await event_db.deactivate_event(eid)
        await query.edit_message_text(
            f"🔴 <b>{ev['name'] if ev else 'Event'}</b> o'chirildi.",
            parse_mode="HTML"
        )
        return

    if data.startswith("adm_evdel_"):
        eid = int(data[10:])
        ev = await event_db.get_event_by_id(eid)
        await event_db.delete_event(eid)
        await query.edit_message_text(
            f"🗑 Event <b>{ev['name'] if ev else ''}</b> o'chirildi!",
            parse_mode="HTML"
        )
        return

    if data.startswith("adm_evwaifus_"):
        eid = int(data[13:])
        await _show_event_waifus(query, eid)
        return

    if data == "adm_evlist_back":
        try:
            await query.delete_message()
        except Exception:
            pass
        await _show_events(update.effective_message)
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

    # ── Event waifu rarity ──
    if data.startswith("ewrar_"):
        rarity = data[6:]
        d = context.user_data.get(ADM_DATA, {})
        eid = d.get("event_id")
        if not eid:
            await query.answer("❌ Xatolik.", show_alert=True)
            return
        ew_id = await event_db.add_event_waifu(
            event_id=eid,
            file_id=d.get("ew_file_id",""),
            name=d.get("ew_name",""),
            anime=d.get("ew_anime",""),
            rarity=rarity,
            price=d.get("ew_price",0),
            added_by=user.id
        )
        _clear_state(context)
        if ew_id:
            await query.edit_message_text(
                f"✅ Event waifu qo'shildi!\n"
                f"{get_rarity_emoji(rarity)} <b>{d.get('ew_name')}</b> | {d.get('ew_anime')}",
                parse_mode="HTML"
            )
            await _show_event_waifus(update.effective_message, eid)
        else:
            await query.edit_message_text("❌ Xatolik yuz berdi.")
        return


async def _finalize_add_waifu(query, context, user, role, group_id):
    d = context.user_data.get(ADM_DATA, {})
    file_id = d.get("file_id")
    name = d.get("name")
    anime = d.get("anime")
    rarity = d.get("rarity")
    price = d.get("price", 0)
    if not all([file_id, name, anime, rarity]):
        await query.edit_message_text("❌ Ma'lumotlar to'liq emas.")
        return
    ok, wid = await waifu_db.add_waifu(name, anime, rarity, file_id, user.id, price, group_id)
    await log_db.add_log("add_waifu", user_id=user.id, details=f"id={wid} name={name} rarity={rarity}")
    _clear_state(context)
    emoji = get_rarity_emoji(rarity)
    grp = ""
    if group_id:
        g = await waifu_db.get_group_by_id(group_id)
        grp = f"\n📂 Guruh: <b>{g['name'] if g else group_id}</b>"
    await query.edit_message_text(
        f"✅ Waifu qo'shildi!\n"
        f"{emoji} <b>{name}</b> | {anime}\n"
        f"⭐ {rarity} | 💰 {price:,} coin{grp}\n"
        f"🆔 <code>#{wid}</code>",
        parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════
#  KOMANDALAR (muvofiqlik uchun)
# ══════════════════════════════════════════════════════

async def cmd_addwaifu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    await update.message.reply_text("➕ /panel → ➕ Waifu qo'shish tugmasini bosing.")


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
    sent = 0; failed = 0
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
    await _show_events(update.message)


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
    await update.message.reply_text(f"✅ Spawn chegarasi: {t}")


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
        uname = f"@{a['username']}" if a.get("username") else ""
        lines.append(f"{role_mark.get(r,'🔧')}: <code>{a['user_id']}</code> {uname}")
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
        return
    title_text = " ".join(context.args[1:])
    await title_db.set_title(uid, title_text, update.effective_user.id)
    await update.message.reply_text(f"✅ <code>{uid}</code>\n🏅 <b>{title_text}</b>", parse_mode="HTML")


async def cmd_removetitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
        return
    if not context.args:
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
    """Eski rarity callback — endi handle_admin_callback ga yo'naltirildi"""
    pass
