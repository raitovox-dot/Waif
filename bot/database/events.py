"""
Event tizimi:
- Admin nomli va turli eventlar yaratadi
- Har event uchun alohida waifular qo'shiladi
- Shart: event yoqilganda, har N xabarda botning asosiy guruhida random event waifu chiqadi
- Eventlar doim turadi, faqat admin yoqadi/o'chiradi
- Bir vaqtda bir eventgina aktiv bo'lishi mumkin
"""
import asyncpg
from .db import get_pool


# ─── Events ───

async def create_event(name: str, event_type: str, description: str,
                       trigger_every: int, created_by: int) -> int | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                "INSERT INTO events (name, event_type, description, trigger_every, created_by) "
                "VALUES ($1,$2,$3,$4,$5) RETURNING id",
                name, event_type, description, trigger_every, created_by
            )
            return row['id']
        except Exception as e:
            print("create_event error:", e)
            return None


async def get_all_events():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM events ORDER BY created_at DESC")
        return [dict(r) for r in rows]


async def get_event_by_id(event_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM events WHERE id=$1", event_id)
        return dict(row) if row else None


async def get_active_event():
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT e.*, "
            "(SELECT COUNT(*) FROM event_waifus ew WHERE ew.event_id=e.id) as waifu_count "
            "FROM events e WHERE e.is_active=1 ORDER BY e.id DESC LIMIT 1"
        )
        return dict(row) if row else None


async def activate_event(event_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # avval hammasini o'chirib
        await conn.execute("UPDATE events SET is_active=0")
        await conn.execute("UPDATE events SET is_active=1 WHERE id=$1", event_id)


async def deactivate_event(event_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE events SET is_active=0 WHERE id=$1", event_id)


async def delete_event(event_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM events WHERE id=$1", event_id)


async def update_event(event_id: int, **fields):
    allowed = {"name", "event_type", "description", "trigger_every"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        sets = ", ".join(f"{k}=${i+2}" for i, k in enumerate(updates.keys()))
        vals = list(updates.values())
        await conn.execute(f"UPDATE events SET {sets} WHERE id=$1", event_id, *vals)


# ─── Event Waifus ───

async def add_event_waifu(event_id: int, file_id: str, name: str, anime: str,
                           rarity: str, price: int, added_by: int) -> int | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                "INSERT INTO event_waifus (event_id, waifu_id, file_id, name, anime, rarity, price, added_by) "
                "VALUES ($1, 'ev_tmp', $2, $3, $4, $5, $6, $7) RETURNING id",
                event_id, file_id, name, anime, rarity, price, added_by
            )
            new_id = row['id']
            waifu_id = f"EV-{event_id}-{new_id}"
            await conn.execute(
                "UPDATE event_waifus SET waifu_id=$1 WHERE id=$2", waifu_id, new_id
            )
            return new_id
        except Exception as e:
            print("add_event_waifu error:", e)
            return None


async def get_event_waifus(event_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM event_waifus WHERE event_id=$1 ORDER BY id", event_id
        )
        return [dict(r) for r in rows]


async def get_event_waifu_by_id(ew_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM event_waifus WHERE id=$1", ew_id)
        return dict(row) if row else None


async def remove_event_waifu(ew_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM event_waifus WHERE id=$1", ew_id)


async def get_random_event_waifu(event_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM event_waifus WHERE event_id=$1 ORDER BY RANDOM() LIMIT 1",
            event_id
        )
        return dict(row) if row else None


# ─── Event message counter (guruh uchun) ───

async def get_event_message_count(group_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        val = await conn.fetchval(
            "SELECT COALESCE(value,'0')::INTEGER FROM bot_settings WHERE key=$1",
            f"evt_msg_cnt_{group_id}"
        )
        return val or 0


async def increment_event_message_count(group_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        key = f"evt_msg_cnt_{group_id}"
        row = await conn.fetchrow("SELECT value FROM bot_settings WHERE key=$1", key)
        current = int(row['value']) if row else 0
        new_val = current + 1
        await conn.execute(
            "INSERT INTO bot_settings (key, value, updated_at) VALUES ($1,$2,NOW()) "
            "ON CONFLICT (key) DO UPDATE SET value=$2, updated_at=NOW()",
            key, str(new_val)
        )
        return new_val


async def reset_event_message_count(group_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        key = f"evt_msg_cnt_{group_id}"
        await conn.execute(
            "INSERT INTO bot_settings (key, value, updated_at) VALUES ($1,'0',NOW()) "
            "ON CONFLICT (key) DO UPDATE SET value='0', updated_at=NOW()",
            key
        )


# ─── Divine counter ───

async def get_divine_counter(group_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        val = await conn.fetchval(
            "SELECT exclusive_count FROM divine_counter WHERE group_id=$1", group_id
        )
        return val or 0


async def increment_divine_counter(group_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO divine_counter (group_id, exclusive_count) VALUES ($1, 1) "
            "ON CONFLICT (group_id) DO UPDATE SET exclusive_count = divine_counter.exclusive_count + 1",
            group_id
        )
        val = await conn.fetchval(
            "SELECT exclusive_count FROM divine_counter WHERE group_id=$1", group_id
        )
        return val or 0


async def reset_divine_counter(group_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE divine_counter SET exclusive_count=0, last_reset=NOW() WHERE group_id=$1",
            group_id
        )
