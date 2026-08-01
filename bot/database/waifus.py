import asyncpg
from .db import get_pool
from utils.helpers import pick_random_rarity


async def add_waifu(name: str, anime: str, rarity: str, file_id: str,
                    added_by: int, price: int = 0, group_id: int = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                "INSERT INTO waifus (waifu_id, name, anime, rarity, file_id, added_by, price, group_id) "
                "VALUES ('__tmp__', $1, $2, $3, $4, $5, $6, $7) RETURNING id",
                name, anime, rarity, file_id, added_by, price, group_id
            )
            new_id = row['id']
            waifu_id = str(new_id)
            await conn.execute(
                "UPDATE waifus SET waifu_id=$1 WHERE id=$2", waifu_id, new_id
            )
            return True, waifu_id
        except Exception as e:
            print("add_waifu error:", e)
            return False, ""


async def get_waifu(waifu_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT w.*, g.name as group_name FROM waifus w "
            "LEFT JOIN waifu_groups g ON w.group_id=g.id "
            "WHERE w.waifu_id=$1 AND w.is_active=1", waifu_id
        )
        return dict(row) if row else None


async def get_waifu_any(waifu_id: str):
    """is_active tekshirmasdan topadi (admin uchun)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT w.*, g.name as group_name FROM waifus w "
            "LEFT JOIN waifu_groups g ON w.group_id=g.id "
            "WHERE w.waifu_id=$1", waifu_id
        )
        return dict(row) if row else None


async def get_waifu_by_db_id(db_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT w.*, g.name as group_name FROM waifus w "
            "LEFT JOIN waifu_groups g ON w.group_id=g.id "
            "WHERE w.id=$1 AND w.is_active=1", db_id
        )
        return dict(row) if row else None


async def edit_waifu(waifu_id: str, **fields):
    """Waifuning istalgan maydonini yangilash"""
    allowed = {"name", "anime", "rarity", "file_id", "price", "group_id"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    pool = await get_pool()
    async with pool.acquire() as conn:
        sets = ", ".join(f"{k}=${i+2}" for i, k in enumerate(updates.keys()))
        vals = list(updates.values())
        await conn.execute(
            f"UPDATE waifus SET {sets} WHERE waifu_id=$1", waifu_id, *vals
        )
        return True


async def get_random_waifu(rarity: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if rarity:
            row = await conn.fetchrow(
                "SELECT w.*, g.name as group_name FROM waifus w "
                "LEFT JOIN waifu_groups g ON w.group_id=g.id "
                "WHERE w.rarity=$1 AND w.is_active=1 ORDER BY RANDOM() LIMIT 1", rarity
            )
        else:
            row = await conn.fetchrow(
                "SELECT w.*, g.name as group_name FROM waifus w "
                "LEFT JOIN waifu_groups g ON w.group_id=g.id "
                "WHERE w.is_active=1 ORDER BY RANDOM() LIMIT 1"
            )
        return dict(row) if row else None


async def get_random_waifu_by_rarity_weight():
    rarity = pick_random_rarity()
    waifu = await get_random_waifu(rarity)
    if not waifu:
        waifu = await get_random_waifu()
    return waifu


async def remove_waifu(waifu_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE waifus SET is_active=0 WHERE waifu_id=$1", waifu_id)


async def remove_waifu_by_db_id(db_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE waifus SET is_active=0 WHERE id=$1", db_id)


async def get_all_waifus_paginated(limit: int = 8, offset: int = 0, group_id: int = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if group_id is not None:
            rows = await conn.fetch(
                "SELECT w.*, g.name as group_name FROM waifus w "
                "LEFT JOIN waifu_groups g ON w.group_id=g.id "
                "WHERE w.is_active=1 AND w.group_id=$3 ORDER BY w.id ASC LIMIT $1 OFFSET $2",
                limit, offset, group_id
            )
        else:
            rows = await conn.fetch(
                "SELECT w.*, g.name as group_name FROM waifus w "
                "LEFT JOIN waifu_groups g ON w.group_id=g.id "
                "WHERE w.is_active=1 ORDER BY w.id ASC LIMIT $1 OFFSET $2",
                limit, offset
            )
        return [dict(r) for r in rows]


async def get_waifus_by_admin(added_by: int, limit: int = 8, offset: int = 0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT w.*, g.name as group_name FROM waifus w "
            "LEFT JOIN waifu_groups g ON w.group_id=g.id "
            "WHERE w.is_active=1 AND w.added_by=$1 ORDER BY w.id ASC LIMIT $2 OFFSET $3",
            added_by, limit, offset
        )
        return [dict(r) for r in rows]


async def count_waifus_by_admin(added_by: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM waifus WHERE is_active=1 AND added_by=$1", added_by
        ) or 0


async def count_all_active() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM waifus WHERE is_active=1") or 0


async def search_waifus(query: str, limit: int = 10):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT w.*, g.name as group_name FROM waifus w "
            "LEFT JOIN waifu_groups g ON w.group_id=g.id "
            "WHERE w.is_active=1 AND (w.name ILIKE $1 OR w.anime ILIKE $1) LIMIT $2",
            f"%{query}%", limit
        )
        return [dict(r) for r in rows]


async def get_waifus_by_anime(anime: str, limit: int = 20):
    """Anime nomi bo'yicha barcha waifularni qaytaradi"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT w.*, g.name as group_name FROM waifus w "
            "LEFT JOIN waifu_groups g ON w.group_id=g.id "
            "WHERE w.is_active=1 AND w.anime ILIKE $1 ORDER BY w.rarity, w.name LIMIT $2",
            f"%{anime}%", limit
        )
        return [dict(r) for r in rows]


async def count_waifus_by_rarity() -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT rarity, COUNT(*) as cnt FROM waifus WHERE is_active=1 GROUP BY rarity"
        )
        return {r['rarity']: r['cnt'] for r in rows}


# ─── Waifu Groups ───

async def create_group(name: str, description: str, created_by: int) -> int | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                "INSERT INTO waifu_groups (name, description, created_by) VALUES ($1,$2,$3) RETURNING id",
                name, description, created_by
            )
            return row['id']
        except Exception as e:
            print("create_group error:", e)
            return None


async def get_all_groups_list():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM waifu_groups ORDER BY name")
        return [dict(r) for r in rows]


async def get_group_by_id(group_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM waifu_groups WHERE id=$1", group_id)
        return dict(row) if row else None


async def get_group_by_name(name: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM waifu_groups WHERE name ILIKE $1", name
        )
        return dict(row) if row else None


async def delete_group(group_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # waifularni guruhsiz qilish
        await conn.execute("UPDATE waifus SET group_id=NULL WHERE group_id=$1", group_id)
        await conn.execute("DELETE FROM waifu_groups WHERE id=$1", group_id)


async def count_waifus_in_group(group_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM waifus WHERE is_active=1 AND group_id=$1", group_id
        ) or 0
