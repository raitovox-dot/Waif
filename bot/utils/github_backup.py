"""
GitHub Backup & Restore tizimi
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bot ma'lumotlarini har 6 soatda GitHub reposiga JSON formatda saqlaydi.
Agar Railway o'chirilsa ham data/backup/ papkasida saqlanib qoladi.
Keyingi deploy paytida bot avtomatik tiklaydi.
"""

import os
import json
import base64
import logging
import asyncio
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── Muhit o'zgaruvchilari ──────────────────────────────────────
GITHUB_TOKEN   = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO    = os.environ.get('GITHUB_REPO', 'raitovox-dot/Waif')
GITHUB_BRANCH  = os.environ.get('GITHUB_BRANCH', 'main')
BACKUP_DIR     = 'data/backup'
GITHUB_API     = 'https://api.github.com'

# Sahifa hajmi (juda katta tablelar uchun)
PAGE_SIZE = 50_000

# Tartib bilan backup — bog'liqliklar hisobga olingan
BACKUP_ORDER = [
    'waifu_groups',
    'waifus',
    'users',
    'admins',
    'allowed_groups',
    'required_channels',
    'bot_settings',
    'redeem_codes',
    'user_titles',
    'events',
    'event_waifus',
    'collections',
    'daily_rewards',
    'user_preferences',
    'groups',
]


def _headers() -> dict:
    return {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }


def _serialize_row(row: dict) -> dict:
    """asyncpg Record → JSON-serializable dict."""
    out = {}
    for k, v in row.items():
        if v is None:
            out[k] = None
        elif hasattr(v, 'isoformat'):      # datetime, date, time
            out[k] = v.isoformat()
        elif isinstance(v, (bytes, bytearray)):
            out[k] = v.hex()
        else:
            out[k] = v
    return out


# ── GitHub API yordamchi funksiyalar ──────────────────────────

async def _gh_get_sha(path: str) -> Optional[str]:
    """Faylning SHA ni olish (mavjud bo'lmasa None)."""
    try:
        import httpx
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, headers=_headers(),
                            params={'ref': GITHUB_BRANCH})
            if r.status_code == 200:
                return r.json().get('sha')
    except Exception as e:
        logger.debug(f"gh_get_sha({path}): {e}")
    return None


async def _gh_put(path: str, content_str: str, sha: Optional[str] = None):
    """Fayl yaratish yoki yangilash."""
    import httpx
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
    encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
    payload: dict = {
        'message': f'backup: {path} [{datetime.utcnow().strftime("%Y-%m-%d %H:%M")} UTC]',
        'content': encoded,
        'branch': GITHUB_BRANCH,
    }
    if sha:
        payload['sha'] = sha

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.put(url, headers=_headers(), json=payload)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"GitHub API {r.status_code}: {r.text[:300]}")


async def _gh_get_content(path: str) -> Optional[str]:
    """Faylni yuklab olish."""
    try:
        import httpx
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(url, headers=_headers(),
                            params={'ref': GITHUB_BRANCH})
            if r.status_code == 200:
                raw = r.json().get('content', '')
                return base64.b64decode(raw).decode('utf-8')
    except Exception as e:
        logger.debug(f"gh_get_content({path}): {e}")
    return None


# ── Asosiy backup funksiyasi ───────────────────────────────────

async def backup_to_github():
    """
    Barcha muhim tablelarni GitHub reposiga JSON sifatida saqlaydi.
    Har 6 soatda avtomatik chaqiriladi.
    """
    if not GITHUB_TOKEN:
        logger.warning("⚠️  GITHUB_TOKEN yo'q — backup o'tkazib yuborildi")
        return

    from database.db import get_pool
    try:
        pool = await get_pool()
    except Exception as e:
        logger.error(f"Backup: pool xatosi: {e}")
        return

    logger.info("🔄 GitHub backup boshlandi...")
    backed_up = 0
    errors = []

    for table in BACKUP_ORDER:
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    f'SELECT * FROM "{table}" LIMIT {PAGE_SIZE}'
                )
            if not rows:
                continue

            data = [_serialize_row(dict(r)) for r in rows]
            content = json.dumps(data, ensure_ascii=False, indent=2)
            path = f"{BACKUP_DIR}/{table}.json"

            sha = await _gh_get_sha(path)
            await _gh_put(path, content, sha)
            backed_up += 1
            logger.info(f"  ✅ {table}: {len(data):,} qator")

            await asyncio.sleep(0.8)   # Rate limit

        except Exception as e:
            errors.append(table)
            logger.warning(f"  ⚠️  {table} backup xatosi: {e}")

    # Metadata faylini yozish
    try:
        meta = {
            'last_backup': datetime.utcnow().isoformat() + 'Z',
            'backed_up_tables': backed_up,
            'failed_tables': errors,
            'repo': GITHUB_REPO,
            'branch': GITHUB_BRANCH,
        }
        meta_path = f"{BACKUP_DIR}/meta.json"
        meta_sha = await _gh_get_sha(meta_path)
        await _gh_put(meta_path, json.dumps(meta, indent=2, ensure_ascii=False), meta_sha)
    except Exception as e:
        logger.warning(f"Metadata yozishda xato: {e}")

    if errors:
        logger.warning(f"✅ Backup tugadi: {backed_up}/{len(BACKUP_ORDER)} — xatolar: {errors}")
    else:
        logger.info(f"✅ GitHub backup tugadi: {backed_up}/{len(BACKUP_ORDER)} table")


# ── Restore funksiyasi ─────────────────────────────────────────

async def restore_from_github() -> bool:
    """
    DB bo'sh bo'lsa GitHub backupdan tiklaydi.
    Qaytadi: True — tiklandi, False — kerak emas yoki backup yo'q.
    """
    if not GITHUB_TOKEN:
        logger.info("GITHUB_TOKEN yo'q — restore o'tkazildi")
        return False

    from database.db import get_pool
    try:
        pool = await get_pool()
    except Exception as e:
        logger.error(f"Restore: pool xatosi: {e}")
        return False

    # Waifus bo'sh bo'lmasa tiklash shart emas
    try:
        async with pool.acquire() as conn:
            count = await conn.fetchval('SELECT COUNT(*) FROM waifus')
        if count and count > 0:
            logger.info(f"DB tayyor: {count:,} waifu mavjud — restore kerak emas")
            return False
    except Exception as e:
        logger.warning(f"Waifus count xatosi: {e}")

    logger.info("📦 DB bo'sh — GitHub backupdan tiklanmoqda...")

    meta_raw = await _gh_get_content(f"{BACKUP_DIR}/meta.json")
    if not meta_raw:
        logger.info("GitHub backupda ma'lumot topilmadi — yangi deploy")
        return False

    meta = json.loads(meta_raw)
    logger.info(f"  Backup sanasi: {meta.get('last_backup', '?')}")

    restored = 0
    for table in BACKUP_ORDER:
        try:
            raw = await _gh_get_content(f"{BACKUP_DIR}/{table}.json")
            if not raw:
                continue

            rows = json.loads(raw)
            if not rows:
                continue

            cols = list(rows[0].keys())
            col_str  = ', '.join(f'"{c}"' for c in cols)
            placeholders = ', '.join(f'${i+1}' for i in range(len(cols)))
            sql = (
                f'INSERT INTO "{table}" ({col_str}) '
                f'VALUES ({placeholders}) ON CONFLICT DO NOTHING'
            )

            inserted = 0
            async with pool.acquire() as conn:
                for row in rows:
                    vals = [row.get(c) for c in cols]
                    try:
                        await conn.execute(sql, *vals)
                        inserted += 1
                    except Exception:
                        pass

            logger.info(f"  ✅ {table}: {inserted:,}/{len(rows):,} qator tiklandi")
            restored += 1
            await asyncio.sleep(0.2)

        except Exception as e:
            logger.warning(f"  ⚠️  {table} restore xatosi: {e}")

    logger.info(f"✅ Restore tugadi: {restored} table")
    return restored > 0
