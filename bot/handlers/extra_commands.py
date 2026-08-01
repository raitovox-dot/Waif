"""
Qo'shimcha buyruqlar: /claim, /ball, /bozor, /dokon, /sandiq, /guess, /harem,
/wpocket, /profile, /bonus, /redeem, /whmode, /w, /wdublikat, /lucky,
/inventory, /wrarity, /top_valyuta, /ctop, /topgroups, /owners,
/changetime, /resetfav
"""
import random
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, dice
from telegram.ext import ContextTypes
from database import users as user_db
from database import collections as col_db
from database import waifus as waifu_db
from database import groups as grp_db
from database.db import get_pool, get_setting, set_setting
from utils.helpers import get_rarity_emoji, RARITY_ORDER, format_waifu_card

# ── Sandiq narxlari ──
SANDIQ_TYPES = {
    "common": {"name": "📦 Oddiy Sandiq", "price": 100, "rarities": ["Common", "Rare"], "weights": [70, 30]},
    "rare":   {"name": "💠 Nodir Sandiq",  "price": 300, "rarities": ["Rare", "Super Rare", "Epic"], "weights": [50, 35, 15]},
    "epic":   {"name": "🟣 Epic Sandiq",   "price": 700, "rarities": ["Epic", "Mythick", "Legendary"], "weights": [55, 30, 15]},
    "legend": {"name": "👑 Legend Sandiq", "price": 2000, "rarities": ["Legendary", "Premium", "Exclusive"], "weights": [60, 30, 10]},
}

# Guess o'yini uchun aktiv sessiyalar
_guess_sessions: dict = {}


async def _check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    from middlewares.subscription import check_subscription
    return await check_subscription(update, context)


async def _check_ban(user_id: int) -> bool:
    u = await user_db.get_user(user_id)
    return bool(u and u.get("is_banned"))


# ═══════════════════════════════════════
# /claim — kunlik mukofot (alias /daily)
# ═══════════════════════════════════════
async def cmd_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.user_commands import cmd_daily
    await cmd_daily(update, context)


# ═══════════════════════════════════════
# /harem — kolleksiya (alias /collection)
# ═══════════════════════════════════════
async def cmd_harem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.gallery import cmd_collection_gallery
    await cmd_collection_gallery(update, context)


# ═══════════════════════════════════════
# /profile — profil (alias /profil)
# ═══════════════════════════════════════
async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.user_commands import cmd_profil
    await cmd_profil(update, context)


# ═══════════════════════════════════════
# /bozor — foydalanuvchilar bozori
# ═══════════════════════════════════════
async def cmd_bozor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    from handlers.market_handler import cmd_market
    await cmd_market(update, context)


# ═══════════════════════════════════════
# /dokon — wayfu do'koni
# ═══════════════════════════════════════
async def cmd_dokon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    from handlers.market_handler import cmd_market
    await cmd_market(update, context)


# ═══════════════════════════════════════
# /wdublikat — dublikat wayfular
# ═══════════════════════════════════════
async def cmd_wdublikat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.duplicate import cmd_duplicate
    await cmd_duplicate(update, context)


# ═══════════════════════════════════════
# /wpocket — valyuta balansi
# ═══════════════════════════════════════
async def cmd_wpocket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)
    u = await user_db.get_user(user.id)
    coins = u.get("coins", 0) if u else 0
    col_count = await col_db.count_collection(user.id)
    await update.message.reply_text(
        f"💰 <b>VALYUTA HAMYON</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {user.full_name}\n"
        f"💵 Balans: <b>{coins:,} coin</b>\n"
        f"🎴 Kolleksiya: <b>{col_count}</b> ta\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>/daily — kunlik mukofot\n"
        f"/sell — bozorga qo'yish</i>",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /ball — sharlar bilan wayfu yutish
# ═══════════════════════════════════════
async def cmd_ball(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    if await _check_ban(user.id):
        await update.message.reply_text("🚫 Siz banlangansiz.")
        return

    u = await user_db.get_user(user.id)
    bet = 50  # 50 coin stavka
    if u.get("coins", 0) < bet:
        await update.message.reply_text(
            f"❌ Yetarli coin yo'q!\n"
            f"💰 Sizda: <b>{u.get('coins',0)}</b> coin\n"
            f"🎲 Stavka: <b>{bet}</b> coin\n\n"
            f"💡 /daily buyrug'i bilan coin oling!",
            parse_mode="HTML"
        )
        return

    # Dice o'ynatish
    dice_msg = await update.message.reply_dice(emoji="🎲")
    dice_val = dice_msg.dice.value
    import asyncio
    await asyncio.sleep(3)  # Animatsiya tugashini kutish

    if dice_val >= 5:  # 5 yoki 6 — g'alaba
        await user_db.remove_coins(user.id, bet)  # stavkani olish
        waifu = await waifu_db.get_random_waifu_by_rarity_weight()
        if waifu:
            await col_db.add_to_collection(user.id, waifu["waifu_id"])
            emoji = get_rarity_emoji(waifu["rarity"])
            await update.message.reply_text(
                f"🎲 <b>Zar: {dice_val}</b> — 🎉 G'ALABA!\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{emoji} <b>{waifu['name']}</b>\n"
                f"🎌 {waifu['anime']} | {waifu['rarity']}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Kolleksiyangizga qo'shildi!\n"
                f"💸 Stavka: -{bet} coin",
                parse_mode="HTML"
            )
        else:
            await user_db.add_coins(user.id, bet)  # stavkani qaytarish
            await update.message.reply_text(
                f"🎲 <b>Zar: {dice_val}</b> — 🎉 G'ALABA!\n"
                f"💰 <b>{bet * 2}</b> coin yutdingiz!",
                parse_mode="HTML"
            )
    else:
        await user_db.remove_coins(user.id, bet)
        await update.message.reply_text(
            f"🎲 <b>Zar: {dice_val}</b> — 😔 Yutqazdingiz!\n"
            f"💸 <b>{bet}</b> coin yutqazildi.\n\n"
            f"💡 Yana urinib ko'ring! 5 yoki 6 chiqsa yutasiz.",
            parse_mode="HTML"
        )


# ═══════════════════════════════════════
# /sandiq — pullik sandiqlar
# ═══════════════════════════════════════
async def cmd_sandiq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    if await _check_ban(user.id):
        return

    args = context.args
    if not args or args[0] not in SANDIQ_TYPES:
        # Ko'rsatish
        lines = ["📦 <b>SANDIQLAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
        for key, s in SANDIQ_TYPES.items():
            rarities_str = " / ".join(s["rarities"])
            lines.append(f"{s['name']}\n   💰 <b>{s['price']}</b> coin | {rarities_str}")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("📌 Ishlatish: /sandiq common|rare|epic|legend")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        return

    stype = args[0]
    sandiq = SANDIQ_TYPES[stype]
    u = await user_db.get_user(user.id)
    if u.get("coins", 0) < sandiq["price"]:
        await update.message.reply_text(
            f"❌ Yetarli coin yo'q!\n"
            f"💰 Sizda: <b>{u.get('coins',0):,}</b> coin\n"
            f"📦 Sandiq narxi: <b>{sandiq['price']:,}</b> coin",
            parse_mode="HTML"
        )
        return

    ok = await user_db.remove_coins(user.id, sandiq["price"])
    if not ok:
        await update.message.reply_text("❌ Xatolik yuz berdi.")
        return

    rarity = random.choices(sandiq["rarities"], weights=sandiq["weights"], k=1)[0]
    waifu = await waifu_db.get_random_waifu(rarity)
    if not waifu:
        waifu = await waifu_db.get_random_waifu()
    if not waifu:
        await user_db.add_coins(user.id, sandiq["price"])
        await update.message.reply_text("❌ Hozircha wayfular yo'q. Pullar qaytarildi.")
        return

    await col_db.add_to_collection(user.id, waifu["waifu_id"])
    emoji = get_rarity_emoji(waifu["rarity"])
    await update.message.reply_photo(
        photo=waifu["file_id"],
        caption=f"📦 <b>{sandiq['name']}</b> ochildi!\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{emoji} <b>{waifu['name']}</b>\n"
                f"🎌 {waifu['anime']} | <b>{waifu['rarity']}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Kolleksiyangizga qo'shildi!",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /guess — waifu nomini topish o'yini
# ═══════════════════════════════════════
async def cmd_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    user = update.effective_user
    chat = update.effective_chat
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    if await _check_ban(user.id):
        return

    key = (chat.id, user.id)
    waifu = await waifu_db.get_random_waifu()
    if not waifu:
        await update.message.reply_text("❌ Hozircha wayfular yo'q.")
        return

    _guess_sessions[key] = {
        "waifu": waifu,
        "attempts": 3,
        "started_at": datetime.now()
    }

    emoji = get_rarity_emoji(waifu["rarity"])
    await update.message.reply_photo(
        photo=waifu["file_id"],
        caption=f"🎯 <b>WAIFU TOPISH O'YINI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{emoji} Rarity: <b>{waifu['rarity']}</b>\n"
                f"🎌 Anime: <b>{waifu['anime']}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"❓ Bu wayfu kimning ismi?\n"
                f"3 ta urinish bor!\n\n"
                f"💡 Ismini yozing (to'liq yoki qisman)\n"
                f"❌ /guess_stop — to'xtatish",
        parse_mode="HTML"
    )


async def cmd_guess_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    key = (chat.id, user.id)
    session = _guess_sessions.pop(key, None)
    if session:
        waifu = session["waifu"]
        await update.message.reply_text(
            f"❌ O'yin to'xtatildi.\n"
            f"💡 To'g'ri javob: <b>{waifu['name']}</b>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ Aktiv o'yin topilmadi.")


async def handle_guess_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    key = (chat.id, user.id)
    session = _guess_sessions.get(key)
    if not session:
        return False

    waifu = session["waifu"]
    guess = update.message.text.strip().lower()
    target = waifu["name"].lower()

    def _match(g, t):
        g = g.strip()
        t = t.strip()
        if g == t:
            return True
        if len(g) >= 3 and (g in t or t.startswith(g)):
            return True
        return False

    if _match(guess, target):
        del _guess_sessions[key]
        await col_db.add_to_collection(user.id, waifu["waifu_id"])
        emoji = get_rarity_emoji(waifu["rarity"])
        await update.message.reply_text(
            f"✅ <b>To'g'ri!</b> 🎉\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{emoji} <b>{waifu['name']}</b>\n"
            f"🎌 {waifu['anime']} | {waifu['rarity']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Kolleksiyangizga qo'shildi!",
            parse_mode="HTML"
        )
        return True

    session["attempts"] -= 1
    if session["attempts"] <= 0:
        del _guess_sessions[key]
        await update.message.reply_text(
            f"😔 Urinishlar tugadi!\n"
            f"💡 To'g'ri javob: <b>{waifu['name']}</b>\n\n"
            f"🎯 Yana urinish: /guess",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"❌ Noto'g'ri! {session['attempts']} ta urinish qoldi.\n"
            f"💡 Yana urinib ko'ring...",
            parse_mode="HTML"
        )
    return True


# ═══════════════════════════════════════
# /bonus — yangi foydalanuvchi bonusi
# ═══════════════════════════════════════
async def cmd_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    pool = await get_pool()
    async with pool.acquire() as conn:
        claimed = await conn.fetchrow("SELECT 1 FROM bonus_claimed WHERE user_id=$1", user.id)
        if claimed:
            await update.message.reply_text(
                "❌ Siz bonus olganmiz!\n"
                "💡 Bonus faqat <b>1 marta</b> beriladi.",
                parse_mode="HTML"
            )
            return
        await conn.execute("INSERT INTO bonus_claimed (user_id) VALUES ($1)", user.id)

    bonus_coins = 500
    await user_db.add_coins(user.id, bonus_coins)
    waifu = await waifu_db.get_random_waifu("Common")
    if not waifu:
        waifu = await waifu_db.get_random_waifu()

    text = (
        f"🎁 <b>YANGI FOYDALANUVCHI BONUSI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Bonus berildi!\n"
        f"💰 <b>{bonus_coins:,}</b> coin\n"
    )
    if waifu:
        await col_db.add_to_collection(user.id, waifu["waifu_id"])
        emoji = get_rarity_emoji(waifu["rarity"])
        text += (
            f"{emoji} <b>{waifu['name']}</b> ({waifu['rarity']})\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎌 {waifu['anime']}\n"
        )
    text += (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Bu bonus faqat 1 marta beriladi!\n"
        f"🎴 /collection — kolleksiyangiz"
    )
    if waifu:
        await update.message.reply_photo(photo=waifu["file_id"], caption=text, parse_mode="HTML")
    else:
        await update.message.reply_text(text, parse_mode="HTML")


# ═══════════════════════════════════════
# /redeem — kodni ishlatish
# ═══════════════════════════════════════
async def cmd_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    if not context.args:
        await update.message.reply_text(
            "🎫 <b>KOD ISHLATISH</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 Ishlatish: /redeem [KOD]\n"
            "📌 Misol: /redeem PROMO2024",
            parse_mode="HTML"
        )
        return

    code = context.args[0].upper().strip()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM redeem_codes WHERE code=$1 AND is_active=1", code
        )
        if not row:
            await update.message.reply_text(
                f"❌ <b>{code}</b> kod topilmadi yoki yaroqsiz!",
                parse_mode="HTML"
            )
            return

        used = await conn.fetchrow(
            "SELECT 1 FROM redeem_history WHERE code=$1 AND user_id=$2", code, user.id
        )
        if used:
            await update.message.reply_text(
                f"❌ Siz bu kodni allaqachon ishlatgansiz!",
                parse_mode="HTML"
            )
            return

        if row["max_uses"] > 0 and row["used_count"] >= row["max_uses"]:
            await update.message.reply_text(
                f"❌ Bu kodning maksimal ishlatish limiti tugadi!",
                parse_mode="HTML"
            )
            return

        await conn.execute(
            "INSERT INTO redeem_history (code, user_id) VALUES ($1,$2)", code, user.id
        )
        await conn.execute(
            "UPDATE redeem_codes SET used_count = used_count + 1 WHERE code=$1", code
        )

    rewards = []
    if row["reward_coins"] and row["reward_coins"] > 0:
        await user_db.add_coins(user.id, row["reward_coins"])
        rewards.append(f"💰 <b>{row['reward_coins']:,}</b> coin")

    waifu_got = None
    if row["reward_waifu_rarity"]:
        waifu_got = await waifu_db.get_random_waifu(row["reward_waifu_rarity"])
        if waifu_got:
            await col_db.add_to_collection(user.id, waifu_got["waifu_id"])
            emoji = get_rarity_emoji(waifu_got["rarity"])
            rewards.append(f"{emoji} {waifu_got['name']} ({waifu_got['rarity']})")

    rewards_text = "\n".join(rewards) if rewards else "Hech narsa yo'q"
    text = (
        f"✅ <b>KOD MUVAFFAQIYATLI ISHLATILDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎫 Kod: <code>{code}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 Mukofotlar:\n{rewards_text}"
    )
    if waifu_got:
        await update.message.reply_photo(photo=waifu_got["file_id"], caption=text, parse_mode="HTML")
    else:
        await update.message.reply_text(text, parse_mode="HTML")


# ═══════════════════════════════════════
# /whmode — harem ko'rinishini almashtirish
# ═══════════════════════════════════════
async def cmd_whmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT harem_view FROM user_preferences WHERE user_id=$1", user.id)
        current = row["harem_view"] if row else "list"
        new_mode = "grid" if current == "list" else "list"
        await conn.execute(
            "INSERT INTO user_preferences (user_id, harem_view) VALUES ($1,$2) "
            "ON CONFLICT (user_id) DO UPDATE SET harem_view=$2, updated_at=NOW()",
            user.id, new_mode
        )
    mode_names = {"list": "📋 Ro'yxat", "grid": "🔲 Jadval"}
    await update.message.reply_text(
        f"🔀 <b>Harem ko'rinishi o'zgartirildi</b>\n"
        f"✅ Yangi rejim: <b>{mode_names[new_mode]}</b>",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /w — wayfu haqida ma'lumot (kolleksiya ID)
# ═══════════════════════════════════════
async def cmd_w(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    if not context.args:
        await update.message.reply_text(
            "📋 <b>WAIFU MA'LUMOT</b>\n"
            "Ishlatish: /w [kolleksiya ID]\n"
            "Misol: /w 123\n\n"
            "Kolleksiya ID ni /collection dan toping.",
            parse_mode="HTML"
        )
        return

    try:
        cid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID raqam bo'lishi kerak.")
        return

    item = await col_db.get_collection_item(cid)
    if not item:
        await update.message.reply_text("❌ Bunday kolleksiya topilmadi.")
        return

    owner = await user_db.get_user(item["user_id"])
    owner_name = owner.get("full_name") or owner.get("username") or str(item["user_id"]) if owner else "Noma'lum"
    emoji = get_rarity_emoji(item["rarity"])
    fav = "⭐ Sevimli" if item.get("is_favorite") else ""

    await update.message.reply_photo(
        photo=item["file_id"],
        caption=f"🆔 <b>WAIFU MA'LUMOT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{emoji} <b>{item['name']}</b>\n"
                f"🎌 Anime: <b>{item['anime']}</b>\n"
                f"⭐ Rarity: <b>{item['rarity']}</b>\n"
                f"🗂 Kolleksiya ID: <code>{cid}</code>\n"
                f"👤 Egasi: <b>{owner_name}</b>\n"
                f"{fav}\n"
                f"📅 Tutilgan: {str(item.get('caught_at',''))[:10]}\n"
                f"━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /lucky — tasodifiy wayfu (cooldown bilan)
# ═══════════════════════════════════════
async def cmd_lucky(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    if await _check_ban(user.id):
        return

    pool = await get_pool()
    now = datetime.now()
    cooldown_hours = 6
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT last_lucky FROM lucky_cooldown WHERE user_id=$1", user.id)
        if row:
            diff = now - row["last_lucky"]
            if diff.total_seconds() < cooldown_hours * 3600:
                remaining = timedelta(hours=cooldown_hours) - diff
                h = int(remaining.total_seconds() // 3600)
                m = int((remaining.total_seconds() % 3600) // 60)
                await update.message.reply_text(
                    f"⏰ Keyingi lucky spin: <b>{h}s {m}d</b> dan so'ng!\n"
                    f"🍀 Har {cooldown_hours} soatda 1 marta urinish mumkin.",
                    parse_mode="HTML"
                )
                return
        await conn.execute(
            "INSERT INTO lucky_cooldown (user_id, last_lucky) VALUES ($1,$2) "
            "ON CONFLICT (user_id) DO UPDATE SET last_lucky=$2",
            user.id, now
        )

    # 30% ehtimollik bilan waifu berish
    roll = random.randint(1, 100)
    if roll <= 30:
        waifu = await waifu_db.get_random_waifu_by_rarity_weight()
        if waifu:
            await col_db.add_to_collection(user.id, waifu["waifu_id"])
            emoji = get_rarity_emoji(waifu["rarity"])
            await update.message.reply_photo(
                photo=waifu["file_id"],
                caption=f"🍀 <b>OMADINGIZ BOR!</b> 🎉\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🎲 Natija: <b>{roll}/100</b> (30 dan kam)\n"
                        f"{emoji} <b>{waifu['name']}</b>\n"
                        f"🎌 {waifu['anime']} | {waifu['rarity']}\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"✅ Kolleksiyangizga qo'shildi!\n"
                        f"⏰ Keyingi urinish: {cooldown_hours} soatdan keyin",
                parse_mode="HTML"
            )
            return

    await update.message.reply_text(
        f"😔 <b>Omad kulinmadi...</b>\n"
        f"🎲 Natija: <b>{roll}/100</b> (30 dan yuqori)\n"
        f"💡 30% ehtimollik bilan waifu olasiz!\n"
        f"⏰ Keyingi urinish: {cooldown_hours} soatdan keyin",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /inventory — to'plam statistikasi
# ═══════════════════════════════════════
async def cmd_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Rarity bo'yicha hisob
        rows = await conn.fetch(
            "SELECT w.rarity, COUNT(*) as cnt FROM collections c "
            "JOIN waifus w ON c.waifu_id=w.waifu_id "
            "WHERE c.user_id=$1 GROUP BY w.rarity",
            user.id
        )
        rarity_counts = {r["rarity"]: r["cnt"] for r in rows}
        total = sum(rarity_counts.values())

        # Anime bo'yicha top 5
        anime_rows = await conn.fetch(
            "SELECT w.anime, COUNT(*) as cnt FROM collections c "
            "JOIN waifus w ON c.waifu_id=w.waifu_id "
            "WHERE c.user_id=$1 GROUP BY w.anime ORDER BY cnt DESC LIMIT 5",
            user.id
        )

    u = await user_db.get_user(user.id)
    lines = [
        f"📦 <b>INVENTAR STATISTIKASI</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"👤 {user.full_name}",
        f"🎴 Jami: <b>{total}</b> ta waifu",
        f"💰 Coin: <b>{u.get('coins',0):,}</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📊 <b>Rarity bo'yicha:</b>",
    ]
    for r in RARITY_ORDER:
        cnt = rarity_counts.get(r, 0)
        if cnt > 0:
            emoji = get_rarity_emoji(r)
            lines.append(f"  {emoji} {r}: <b>{cnt}</b> ta")

    if anime_rows:
        lines.append(f"━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"🎌 <b>Top 5 Anime:</b>")
        for i, row in enumerate(anime_rows, 1):
            lines.append(f"  {i}. {row['anime']}: <b>{row['cnt']}</b> ta")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════
# /wrarity — rarity bo'yicha to'plam
# ═══════════════════════════════════════
async def cmd_wrarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    rarity_filter = " ".join(context.args).strip() if context.args else None

    pool = await get_pool()
    async with pool.acquire() as conn:
        if rarity_filter:
            rows = await conn.fetch(
                "SELECT c.id, w.name, w.anime, w.rarity, w.file_id, c.is_favorite "
                "FROM collections c JOIN waifus w ON c.waifu_id=w.waifu_id "
                "WHERE c.user_id=$1 AND w.rarity ILIKE $2 "
                "ORDER BY c.is_favorite DESC, w.name LIMIT 20",
                user.id, f"%{rarity_filter}%"
            )
        else:
            rows = await conn.fetch(
                "SELECT w.rarity, COUNT(*) as cnt FROM collections c "
                "JOIN waifus w ON c.waifu_id=w.waifu_id "
                "WHERE c.user_id=$1 GROUP BY w.rarity",
                user.id
            )

    if rarity_filter and rows:
        lines = [f"💎 <b>{rarity_filter.title()} WAIFULAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
        for r in rows:
            emoji = get_rarity_emoji(r["rarity"])
            fav = "⭐" if r["is_favorite"] else ""
            lines.append(f"{emoji} {fav}<b>{r['name']}</b> — {r['anime']} | <code>#{r['id']}</code>")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    elif rarity_filter:
        await update.message.reply_text(f"❌ <b>{rarity_filter}</b> rarity topilmadi yoki kolleksiyangiz bo'sh.", parse_mode="HTML")
    else:
        rarity_dict = {r["rarity"]: r["cnt"] for r in rows}
        lines = [f"💎 <b>RARITY BO'YICHA TO'PLAM</b>\n━━━━━━━━━━━━━━━━━━━━"]
        for r in RARITY_ORDER:
            cnt = rarity_dict.get(r, 0)
            emoji = get_rarity_emoji(r)
            bar = "🟦" * min(cnt, 10) + "⬜" * max(0, 10 - cnt)
            lines.append(f"{emoji} {r}: <b>{cnt}</b> ta  {bar}")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 Filtrlash: /wrarity Common")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════
# /top_valyuta — eng ko'p valuta egalari
# ═══════════════════════════════════════
async def cmd_top_valyuta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    top = await user_db.get_top_users(10, by="coins")
    if not top:
        await update.message.reply_text("📊 Reyting bo'sh.")
        return

    lines = ["💰 <b>ENG BOY FOYDALANUVCHILAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = u.get("full_name") or u.get("username") or str(u["user_id"])
        lines.append(f"{medal} <b>{name}</b>\n   💰 {u['coins']:,} coin")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════
# /ctop — guruhdagi eng yaxshilar
# ═══════════════════════════════════════
async def cmd_ctop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Bu buyruq faqat guruhda ishlaydi!")
        return

    # Guruh a'zolarini olish
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id FROM group_members WHERE group_id=$1", chat.id
        )
        member_ids = [r["user_id"] for r in rows]

    if not member_ids:
        # Agar guruh a'zolari DB da bo'lmasa, barcha foydalanuvchilardan olamiz
        top = await user_db.get_top_users(10, by="total_caught")
    else:
        top = await user_db.get_group_top(member_ids, 10)

    if not top:
        await update.message.reply_text("📊 Guruhda hali reyting yo'q.")
        return

    lines = [f"🏆 <b>{chat.title} — TOP 10</b>\n━━━━━━━━━━━━━━━━━━━━"]
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = u.get("full_name") or u.get("username") or str(u["user_id"])
        lines.append(f"{medal} <b>{name}</b>: {u['total_caught']} ta")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════
# /topgroups — eng yaxshi guruhlar
# ═══════════════════════════════════════
async def cmd_topgroups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT gm.group_id, g.group_name, COUNT(DISTINCT gm.user_id) as members, "
            "COALESCE(SUM(u.total_caught),0) as total "
            "FROM group_members gm "
            "LEFT JOIN allowed_groups g ON g.group_id=gm.group_id "
            "LEFT JOIN users u ON u.user_id=gm.user_id "
            "GROUP BY gm.group_id, g.group_name "
            "ORDER BY total DESC LIMIT 10"
        )

    if not rows:
        await update.message.reply_text("📊 Guruhlar reytingi bo'sh.")
        return

    lines = ["🌍 <b>ENG YAXSHI GURUHLAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = row["group_name"] or f"Guruh {row['group_id']}"
        lines.append(f"{medal} <b>{name}</b>\n   👥 {row['members']} a'zo | 🎴 {row['total']} waifu")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════
# /owners — wayfu qayerda borligini ko'rish
# ═══════════════════════════════════════
async def cmd_owners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return

    if not context.args:
        await update.message.reply_text(
            "👑 <b>WAYFU EGALARI</b>\n"
            "Ishlatish: /owners [waifu ID]\n"
            "Misol: /owners CM-123456\n\n"
            "💡 Waifu ID ni /search orqali toping.",
            parse_mode="HTML"
        )
        return

    waifu_id = context.args[0]
    waifu = await waifu_db.get_waifu_by_id(waifu_id)
    if not waifu:
        await update.message.reply_text("❌ Bunday waifu topilmadi.")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT c.user_id, c.id as col_id, c.caught_at, "
            "u.full_name, u.username "
            "FROM collections c JOIN users u ON c.user_id=u.user_id "
            "WHERE c.waifu_id=$1 ORDER BY c.caught_at LIMIT 15",
            waifu_id
        )

    emoji = get_rarity_emoji(waifu["rarity"])
    lines = [
        f"👑 <b>WAYFU EGALARI</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"{emoji} <b>{waifu['name']}</b> | {waifu['rarity']}",
        f"🎌 {waifu['anime']}",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"👥 Egalar soni: <b>{len(rows)}</b> ta",
        f"━━━━━━━━━━━━━━━━━━━━",
    ]
    if rows:
        for r in rows[:10]:
            name = r["full_name"] or r["username"] or str(r["user_id"])
            lines.append(f"• <b>{name}</b> — <code>#{r['col_id']}</code>")
    else:
        lines.append("Bu waifuni hech kim tutmagan!")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════
# /changetime — spawn vaqtini o'zgartirish
# ═══════════════════════════════════════
async def cmd_changetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Bu buyruq faqat guruhda ishlaydi!")
        return

    # Guruh admin tekshiruvi
    try:
        member = await chat.get_member(user.id)
        is_admin = member.status in ("administrator", "creator")
    except Exception:
        is_admin = False

    from database import logs as log_db
    is_bot_admin = await log_db.is_admin(user.id)

    if not is_admin and not is_bot_admin:
        await update.message.reply_text("❌ Bu buyruq faqat guruh adminlari uchun!")
        return

    if not context.args:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT spawn_interval FROM group_settings WHERE group_id=$1", chat.id)
        current = row["spawn_interval"] if row else 100
        await update.message.reply_text(
            f"⏰ <b>SPAWN VAQTINI O'ZGARTIRISH</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Hozirgi: har <b>{current}</b> xabarda 1 spawn\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Ishlatish: /changetime [son]\n"
            f"Misol: /changetime 50\n"
            f"Minimal: 20, Maksimal: 500",
            parse_mode="HTML"
        )
        return

    try:
        interval = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Raqam kiriting!")
        return

    if interval < 20:
        interval = 20
    elif interval > 500:
        interval = 500

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO group_settings (group_id, spawn_interval) VALUES ($1,$2) "
            "ON CONFLICT (group_id) DO UPDATE SET spawn_interval=$2, updated_at=NOW()",
            chat.id, interval
        )

    await update.message.reply_text(
        f"✅ Spawn intervali o'zgartirildi!\n"
        f"⏰ Endi har <b>{interval}</b> xabarda 1 ta waifu paydo bo'ladi.",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
# /resetfav — sevimli tiklash
# ═══════════════════════════════════════
async def cmd_resetfav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
        return
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    pool = await get_pool()
    async with pool.acquire() as conn:
        changed = await conn.fetchval(
            "SELECT COUNT(*) FROM collections WHERE user_id=$1 AND is_favorite=1", user.id
        )
        await conn.execute(
            "UPDATE collections SET is_favorite=0 WHERE user_id=$1", user.id
        )

    await update.message.reply_text(
        f"🔄 <b>Sevimli tiklandi!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <b>{changed}</b> ta sevimli belgisi o'chirildi.\n\n"
        f"💡 Yangi sevimli belgilash: /favorite [ID]",
        parse_mode="HTML"
    )
