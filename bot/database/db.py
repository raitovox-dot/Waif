"""
DB modul: PostgreSQL (asyncpg) yoki SQLite (aiosqlite) — avtomatik tanlanadi.
DATABASE_URL set bo'lsa → PostgreSQL
DATABASE_URL yo'q bo'lsa  → SQLite fallback (bot hamma holatda ishlaydi)
"""
import os
import re
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)
_pool = None

DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
_SQLITE_MODE = not bool(DATABASE_URL)

if _SQLITE_MODE:
    _SQLITE_PATH = os.path.join(os.path.dirname(__file__), '..', 'waifu_bot.db')
    logger.warning("⚠️  DATABASE_URL yo'q — SQLite fallback: %s", _SQLITE_PATH)


# ══════════════════════════════════════════════════════════════
#  SQLite moslashuv qatlami
# ══════════════════════════════════════════════════════════════

def _pg_to_sqlite(query: str) -> str:
    """PostgreSQL so'rov sintaksisini SQLite ga moslash."""
    # $1, $2, … → ?
    query = re.sub(r'\$\d+', '?', query)
    # NOW() → datetime('now')
    query = re.sub(r'\bNOW\(\)', "datetime('now')", query, flags=re.IGNORECASE)
    # ILIKE → LIKE  (SQLite LIKE ASCII uchun katta-kichik harfga sezgir emas)
    query = re.sub(r'\bILIKE\b', 'LIKE', query, flags=re.IGNORECASE)
    return query


def _adapt_ddl_for_sqlite(sql: str) -> str:
    """PostgreSQL DDL ni SQLite uchun moslash."""
    sql = re.sub(r'\bSERIAL\b', 'INTEGER', sql)
    sql = re.sub(r'\bBIGINT\b', 'INTEGER', sql)
    sql = re.sub(r'TIMESTAMP\s+DEFAULT\s+NOW\(\)', "TEXT DEFAULT (datetime('now'))", sql)
    sql = re.sub(r'\bTIMESTAMP\b', 'TEXT', sql)
    return sql


class _CompatConn:
    """aiosqlite uchun asyncpg.Connection interfeysi."""

    def __init__(self, conn):
        self._c = conn

    async def execute(self, query: str, *args):
        q = _pg_to_sqlite(query)
        await self._c.execute(q, args or ())
        await self._c.commit()

    async def fetch(self, query: str, *args) -> list:
        q = _pg_to_sqlite(query)
        async with self._c.execute(q, args or ()) as cur:
            rows = await cur.fetchall()
            if not rows or not cur.description:
                return []
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in rows]

    async def fetchrow(self, query: str, *args):
        results = await self.fetch(query, *args)
        return results[0] if results else None

    async def fetchval(self, query: str, *args):
        row = await self.fetchrow(query, *args)
        return next(iter(row.values())) if row else None

    async def executescript(self, script: str):
        """Ko'p qatorli DDL uchun (schema yaratish)."""
        await self._c.executescript(script)


class _SQLitePool:
    """asyncpg.Pool interfeysi, SQLite ustida."""

    def __init__(self, db_path: str):
        self._path = db_path

    @asynccontextmanager
    async def acquire(self):
        import aiosqlite
        async with aiosqlite.connect(self._path) as conn:
            yield _CompatConn(conn)


# ══════════════════════════════════════════════════════════════
#  Schema (PostgreSQL sintaksisida — SQLite uchun avtomatik moslashadi)
# ══════════════════════════════════════════════════════════════

_POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    coins BIGINT DEFAULT 0,
    total_caught INTEGER DEFAULT 0,
    trade_count INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    ban_reason TEXT,
    flood_until BIGINT DEFAULT 0,
    warn_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS waifu_groups (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_by BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS waifus (
    id SERIAL PRIMARY KEY,
    waifu_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    anime TEXT NOT NULL,
    rarity TEXT NOT NULL,
    file_id TEXT NOT NULL,
    price BIGINT DEFAULT 0,
    group_id INTEGER,
    added_by BIGINT,
    added_at TIMESTAMP DEFAULT NOW(),
    is_active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS collections (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    waifu_id TEXT NOT NULL,
    caught_at TIMESTAMP DEFAULT NOW(),
    is_favorite INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    initiator_id BIGINT NOT NULL,
    receiver_id BIGINT NOT NULL,
    initiator_waifu TEXT NOT NULL,
    receiver_waifu TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS gifts (
    id SERIAL PRIMARY KEY,
    sender_id BIGINT NOT NULL,
    receiver_id BIGINT NOT NULL,
    waifu_id TEXT NOT NULL,
    collection_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS market (
    id SERIAL PRIMARY KEY,
    seller_id BIGINT NOT NULL,
    collection_id INTEGER NOT NULL,
    waifu_id TEXT NOT NULL,
    price BIGINT NOT NULL,
    status TEXT DEFAULT 'active',
    listed_at TIMESTAMP DEFAULT NOW(),
    sold_at TIMESTAMP,
    buyer_id BIGINT
);
CREATE TABLE IF NOT EXISTS admins (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    added_by BIGINT,
    added_at TIMESTAMP DEFAULT NOW(),
    role TEXT DEFAULT 'admin'
);
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    log_type TEXT NOT NULL,
    user_id BIGINT,
    details TEXT,
    group_id BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS required_channels (
    id SERIAL PRIMARY KEY,
    channel_id TEXT NOT NULL UNIQUE,
    channel_name TEXT,
    type TEXT DEFAULT 'channel',
    added_by BIGINT,
    added_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS allowed_groups (
    group_id BIGINT PRIMARY KEY,
    group_name TEXT,
    added_by BIGINT,
    added_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS group_members (
    group_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    PRIMARY KEY (group_id, user_id)
);
CREATE TABLE IF NOT EXISTS group_settings (
    group_id BIGINT PRIMARY KEY,
    spawn_interval INTEGER DEFAULT 100,
    is_active INTEGER DEFAULT 1,
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    event_type TEXT DEFAULT 'spawn',
    description TEXT,
    trigger_every INTEGER DEFAULT 50,
    is_active INTEGER DEFAULT 0,
    created_by BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS event_waifus (
    id SERIAL PRIMARY KEY,
    event_id INTEGER,
    waifu_id TEXT,
    file_id TEXT NOT NULL,
    name TEXT NOT NULL,
    anime TEXT NOT NULL,
    rarity TEXT NOT NULL,
    price BIGINT DEFAULT 0,
    added_by BIGINT,
    added_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS spawn_state (
    group_id BIGINT PRIMARY KEY,
    waifu_id TEXT,
    spawned_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_event INTEGER DEFAULT 0,
    event_id INTEGER
);
CREATE TABLE IF NOT EXISTS daily_rewards (
    user_id BIGINT PRIMARY KEY,
    last_daily TIMESTAMP,
    streak INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS user_titles (
    user_id BIGINT PRIMARY KEY,
    title TEXT NOT NULL,
    given_by BIGINT,
    given_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS daily_shop (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    shop_date TEXT NOT NULL,
    slot INTEGER NOT NULL,
    waifu_id TEXT NOT NULL,
    price BIGINT NOT NULL,
    is_sold INTEGER DEFAULT 0,
    UNIQUE(user_id, shop_date, slot)
);
CREATE TABLE IF NOT EXISTS rarity_cards (
    user_id BIGINT NOT NULL,
    rarity TEXT NOT NULL,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, rarity)
);
CREATE TABLE IF NOT EXISTS bot_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS redeem_codes (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    reward_coins BIGINT DEFAULT 0,
    reward_waifu_rarity TEXT,
    max_uses INTEGER DEFAULT 1,
    used_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_by BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS redeem_history (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL,
    user_id BIGINT NOT NULL,
    redeemed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(code, user_id)
);
CREATE TABLE IF NOT EXISTS bonus_claimed (
    user_id BIGINT PRIMARY KEY,
    claimed_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS lucky_cooldown (
    user_id BIGINT PRIMARY KEY,
    last_lucky TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id BIGINT PRIMARY KEY,
    harem_view TEXT DEFAULT 'list',
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS contest (
    id SERIAL PRIMARY KEY,
    group_id BIGINT,
    title TEXT NOT NULL,
    description TEXT,
    prize_coins BIGINT DEFAULT 0,
    prize_waifu_rarity TEXT,
    end_time TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    created_by BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS contest_entries (
    id SERIAL PRIMARY KEY,
    contest_id INTEGER,
    user_id BIGINT NOT NULL,
    score INTEGER DEFAULT 0,
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(contest_id, user_id)
);
CREATE TABLE IF NOT EXISTS groups (
    group_id BIGINT PRIMARY KEY,
    group_name TEXT,
    is_approved INTEGER DEFAULT 1,
    approved_by BIGINT,
    approved_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    spawn_threshold INTEGER DEFAULT 100,
    skip_member_check INTEGER DEFAULT 0,
    added_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS divine_counter (
    group_id BIGINT PRIMARY KEY,
    exclusive_count INTEGER DEFAULT 0,
    last_reset TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_collections_user ON collections(user_id);
CREATE INDEX IF NOT EXISTS idx_collections_waifu ON collections(waifu_id);
CREATE INDEX IF NOT EXISTS idx_market_status ON market(status);
CREATE INDEX IF NOT EXISTS idx_logs_type ON logs(log_type);
CREATE INDEX IF NOT EXISTS idx_waifus_group ON waifus(group_id);
CREATE INDEX IF NOT EXISTS idx_event_waifus_event ON event_waifus(event_id);
"""

# PostgreSQL-specific migrations (SQLite da skip)
_PG_ONLY_MIGRATIONS = {
    "ALTER TABLE required_channels ALTER COLUMN channel_id TYPE TEXT USING channel_id::TEXT",
}

_MIGRATIONS = [
    "ALTER TABLE events ADD COLUMN IF NOT EXISTS trigger_every INTEGER DEFAULT 50",
    "ALTER TABLE event_waifus ADD COLUMN IF NOT EXISTS waifu_id TEXT",
    "ALTER TABLE required_channels ALTER COLUMN channel_id TYPE TEXT USING channel_id::TEXT",
    "ALTER TABLE required_channels ADD COLUMN IF NOT EXISTS type TEXT DEFAULT 'channel'",
    "ALTER TABLE logs ADD COLUMN IF NOT EXISTS group_id BIGINT",
]


# ══════════════════════════════════════════════════════════════
#  Asosiy funksiyalar
# ══════════════════════════════════════════════════════════════

async def get_pool():
    if _pool is None:
        raise RuntimeError('DB pool initialized emas. init_db() ni chaqiring.')
    return _pool


async def init_db():
    global _pool

    if _SQLITE_MODE:
        # ── SQLite mode ──
        logger.info("💾 SQLite DB ishga tushirilmoqda: %s", _SQLITE_PATH)
        _pool = _SQLitePool(_SQLITE_PATH)
        sqlite_schema = _adapt_ddl_for_sqlite(_POSTGRES_SCHEMA)
        async with _pool.acquire() as conn:
            await conn.executescript(sqlite_schema)
        logger.info("✅ SQLite DB tayyor")

        # SQLite migratsiyalari
        async with _pool.acquire() as conn:
            for migration in _MIGRATIONS:
                if migration in _PG_ONLY_MIGRATIONS:
                    continue
                try:
                    await conn.execute(migration)
                except Exception as e:
                    logger.debug(f"SQLite migration skip: {e}")

    else:
        # ── PostgreSQL mode ──
        import asyncpg
        logger.info("🐘 PostgreSQL ulanilmoqda...")
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
        async with _pool.acquire() as conn:
            await conn.execute(_POSTGRES_SCHEMA)
        logger.info("✅ PostgreSQL DB tayyor")

        # PostgreSQL migratsiyalari
        async with _pool.acquire() as conn:
            for migration in _MIGRATIONS:
                try:
                    await conn.execute(migration)
                except Exception as e:
                    logger.debug(f"Migration skip: {e}")


async def get_setting(key: str, default: str = None) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT value FROM bot_settings WHERE key=$1", key)
        return row['value'] if row else default


async def set_setting(key: str, value: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO bot_settings (key, value) VALUES ($1, $2) "
            "ON CONFLICT (key) DO UPDATE SET value=$2, updated_at=NOW()",
            key, value
        )
