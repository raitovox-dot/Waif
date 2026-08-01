# Railway Deploy Sozlamalari 🚀

## 1-qadam: PostgreSQL qo'shish

Railway dashboard → **+ New** → **Database** → **PostgreSQL** tanlang.
Railway `DATABASE_URL` ni avtomatik to'ldiradi.

---

## 2-qadam: Environment Variables

Railway dashboard → sizning service → **Variables** bo'limi:

| O'zgaruvchi       | Majburiy | Tavsif                                      |
|-------------------|----------|---------------------------------------------|
| `BOT_TOKEN`       | ✅ HA    | BotFather dan olingan token                 |
| `DATABASE_URL`    | ✅ HA    | PostgreSQL (Railway avtomatik qo'shadi)     |
| `GOD_ADMIN_ID`    | ✅ HA    | Sizning Telegram user ID (raqam)            |
| `GITHUB_TOKEN`    | ✅ HA    | GitHub classic token (backup uchun)         |
| `GITHUB_REPO`     | ✅ HA    | `raitovox-dot/Waif`                         |
| `GITHUB_BRANCH`   | ❌ Yo'q  | `main` (default)                            |
| `BOT_GROUP_ID`    | ❌ Yo'q  | Asosiy guruh ID (masalan: `-1001234567890`) |
| `BOT_CHANNEL_ID`  | ❌ Yo'q  | Kanal ID                                    |
| `BOT_USERNAME`    | ❌ Yo'q  | Bot usernamei (@ siz, masalan: `waifubot`)  |
| `WEBHOOK_URL`     | ❌ Yo'q  | Agar webhook ishlatmoqchi bo'lsangiz        |

---

## 3-qadam: Deploy

Variables to'ldirilgandan so'ng Railway avtomatik qayta deploy qiladi.

---

## GitHub Backup tizimi 📦

Bot **har 6 soatda** ma'lumotlarni GitHub reposiga saqlaydi:
```
raitovox-dot/Waif → data/backup/
  ├── waifus.json       ← Barcha waifular
  ├── users.json        ← Foydalanuvchilar
  ├── collections.json  ← Kolleksiyalar
  ├── admins.json       ← Adminlar
  └── meta.json         ← Oxirgi backup vaqti
```

**Agar Railway o'chirilsa:**
- Ma'lumotlar `data/backup/` papkasida saqlanib qoladi
- Yangi deploy paytida bot avtomatik tiklaydi
- Hech qanday qo'shimcha amal kerak emas

---

## Muammolar

### Bot crash bo'lmoqda?
Railway → service → **Logs** ni oching.

Eng ko'p uchraydigan xatolar:

| Xato                                      | Yechim                              |
|-------------------------------------------|-------------------------------------|
| `BOT_TOKEN not found`                     | `BOT_TOKEN` variable qo'shing       |
| `DATABASE_URL environment variable is not set` | PostgreSQL plugin qo'shing    |
| `asyncpg.exceptions.ConnectionDoesNotExistError` | `DATABASE_URL` ni tekshiring |
| `ModuleNotFoundError`                     | Deploy qayta boshlang               |

### GitHub backup ishlamayapti?
- `GITHUB_TOKEN` ni tekshiring — `repo` huquqi bo'lishi kerak
- `GITHUB_REPO` ni tekshiring: `raitovox-dot/Waif` (egachi/repo formatda)
