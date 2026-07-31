import random
import os
from datetime import datetime

# ──────────────────────────────────────────────────────────
#  RARITY CONFIG (rasmdan ko'ra)
#  Common 80%, Rare 10%, Super Rare 5%, Epic 3%, Mythick 1%
#  Legendary 0.9%, Premium 0.099%, Exclusive 0.001%
#  Divine — har 10 ta Exclusive tutilganda chiqadi (maxsus shart)
# ──────────────────────────────────────────────────────────
RARITY_CONFIG = {
    "Common":     {"weight": 80000, "emoji": "⚪", "coin_reward": 10,    "color": "white",   "percent": "80%"},
    "Rare":       {"weight": 10000, "emoji": "🟢", "coin_reward": 30,    "color": "green",   "percent": "10%"},
    "Super Rare": {"weight": 5000,  "emoji": "🔵", "coin_reward": 80,    "color": "blue",    "percent": "5%"},
    "Epic":       {"weight": 3000,  "emoji": "🟣", "coin_reward": 200,   "color": "purple",  "percent": "3%"},
    "Mythick":    {"weight": 1000,  "emoji": "🟠", "coin_reward": 500,   "color": "orange",  "percent": "1%"},
    "Legendary":  {"weight": 900,   "emoji": "🟡", "coin_reward": 1500,  "color": "gold",    "percent": "0.9%"},
    "Premium":    {"weight": 99,    "emoji": "💎", "coin_reward": 5000,  "color": "cyan",    "percent": "0.099%"},
    "Exclusive":  {"weight": 1,     "emoji": "👑", "coin_reward": 15000, "color": "rainbow", "percent": "0.001%"},
    "Divine":     {"weight": 0,     "emoji": "✨", "coin_reward": 50000, "color": "divine",  "percent": "special"},
}

RARITY_ORDER = [
    "Common", "Rare", "Super Rare", "Epic",
    "Mythick", "Legendary", "Premium", "Exclusive", "Divine"
]

# Normal spawn uchun (Divine chiqmaydi — u maxsus shart bilan)
SPAWNABLE_RARITIES = [r for r in RARITY_ORDER if r != "Divine"]


def get_rarity_emoji(rarity: str) -> str:
    return RARITY_CONFIG.get(rarity, {}).get("emoji", "❓")


def get_coin_reward(rarity: str) -> int:
    return RARITY_CONFIG.get(rarity, {}).get("coin_reward", 10)


def get_rarity_percent(rarity: str) -> str:
    return RARITY_CONFIG.get(rarity, {}).get("percent", "?")


def pick_random_rarity() -> str:
    rarities = SPAWNABLE_RARITIES
    weights = [RARITY_CONFIG[r]["weight"] for r in rarities]
    return random.choices(rarities, weights=weights, k=1)[0]


def format_profile(user: dict, collection_count: int, rank: int, title: str = None) -> str:
    full_name = user.get('full_name') or "Noma'lum"
    title_line = f"🏅 Unvon: <b>{title}</b>\n" if title else ""
    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>PROFIL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"👤 Ism: <b>{full_name}</b>\n"
        f"{title_line}"
        f"💰 Coin: <b>{user['coins']:,}</b>\n"
        f"🎴 Kolleksiya: <b>{collection_count}</b> ta\n"
        f"🏆 Topilgan: <b>{user['total_caught']}</b> ta\n"
        f"🔄 Trade: <b>{user['trade_count']}</b> ta\n"
        f"📊 Reyting: <b>#{rank}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


def format_waifu_card(waifu: dict, collection_id: int = None) -> str:
    emoji = get_rarity_emoji(waifu['rarity'])
    price = waifu.get('price', 0) or 0
    group_name = waifu.get('group_name') or waifu.get('group_id') or ""
    lines = [
        f"━━━━━━━━━━━━━━━━━━━━",
        f"{emoji} <b>{waifu['rarity'].upper()}</b> {emoji}",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📛 Ism: <b>{waifu['name']}</b>",
        f"🎌 Anime: <b>{waifu['anime']}</b>",
        f"🆔 ID: <code>#{waifu['waifu_id']}</code>",
    ]
    if price:
        lines.append(f"💰 Narx: <b>{price:,}</b> coin")
    if group_name:
        lines.append(f"📂 Guruh: <b>{group_name}</b>")
    if collection_id:
        lines.append(f"🗂 Kolleksiya ID: <code>{collection_id}</code>")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def generate_waifu_id(rarity: str) -> str:
    prefix_map = {
        "Common": "CM", "Rare": "RR", "Super Rare": "SR",
        "Epic": "EP", "Mythick": "MK", "Legendary": "LG",
        "Premium": "PR", "Exclusive": "EX", "Divine": "DV"
    }
    prefix = prefix_map.get(rarity, "WF")
    number = random.randint(100000, 999999)
    return f"{prefix}-{number}"


def is_god_admin(user_id: int) -> bool:
    god_id = os.environ.get("GOD_ADMIN_ID", "")
    try:
        return int(god_id) == user_id
    except Exception:
        return False


def get_bot_group_id() -> int | None:
    gid = os.environ.get("BOT_GROUP_ID", "")
    try:
        return int(gid)
    except Exception:
        return None


def get_bot_channel_id() -> int | None:
    cid = os.environ.get("BOT_CHANNEL_ID", "")
    try:
        return int(cid)
    except Exception:
        return None
