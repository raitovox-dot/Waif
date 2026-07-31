# 🎴 Waifu Catch Bot

Telegram guruh uchun to'liq waifu yig'ish boti.

## 🌟 Yangi xususiyatlar

### ⭐ Yangi Rarity tizimi
| Daraja | Foiz | Emoji | Coin mukofot |
|--------|------|-------|-------------|
| Common | 80% | ⚪ | 10 |
| Rare | 10% | 🟢 | 30 |
| Super Rare | 5% | 🔵 | 80 |
| Epic | 3% | 🟣 | 200 |
| Mythick | 1% | 🟠 | 500 |
| Legendary | 0.9% | 🟡 | 1,500 |
| Premium | 0.099% | 💎 | 5,000 |
| Exclusive | 0.001% | 👑 | 15,000 |
| **Divine** | **Maxsus** | **✨** | **50,000** |

> **Divine** — har bir guruhda 10 ta Exclusive waifu tutilganda avtomatik paydo bo'ladi!

### 🛡 Admin Panel (`/panel`)
To'liq interaktiv panel 4 ta bo'lim bilan:

**🎴 Waifu boshqaruvi:**
- Waifu qo'shish (rasm, ism, anime, narx, guruh)
- Ro'yxat ko'rish (sahifa bo'yicha)
- ID bo'yicha topish va tahrirlash
- Barcha maydonlarni (ism, anime, rarity, narx, rasm, guruh) o'zgartirish
- Waifu guruhlari yaratish va boshqarish

**⚡ Event boshqaruvi:**
- Event yaratish (nom, tur, tavsif, trigger chegarasi)
- Har event uchun alohida waifular qo'shish
- Eventni yoqish/o'chirish (bir vaqtda faqat bittasi aktiv)
- Eventlar doim turadi — faqat admin yoqadi/o'chiradi
- Event waifular faqat botning asosiy guruhida chiqadi

**👥 Foydalanuvchi boshqaruvi:**
- Ban/Unban
- Coin berish
- Waifu berish
- Unvon berish

**⚙️ Tizim:**
- Broadcast
- Statistika
- Spawn sozlash
- Kanal qo'shish/o'chirish
- Admin qo'shish/o'chirish

### 📂 Waifu Guruhlari
- Guruh yaratish va nomlash
- Waifularni guruhlarga biriktirish
- Guruh bo'yicha ko'rish

### ⚡ Event tizimi
- Admin ixtiyoriy nomli eventlar yaratadi
- Har event o'z waifulariga ega
- Trigger: har N xabarda (admin belgilaydi) bot asosiy guruhida tasodifiy event waifu chiqadi
- Eventlar o'chib ketmaydi — faqat admin boshqaradi

## 🔧 O'rnatish

```bash
# 1. .env fayl yarating
cp .env.example .env
# .env ni to'ldiring

# 2. Kutubxonalarni o'rnating
pip install -r requirements.txt

# 3. Botni ishga tushiring
python main.py
```

## 🌍 Muhit o'zgaruvchilari

| O'zgaruvchi | Tavsif |
|-------------|--------|
| `BOT_TOKEN` | Telegram bot tokeni |
| `DATABASE_URL` | PostgreSQL URL |
| `GOD_ADMIN_ID` | Asosiy admin user ID |
| `BOT_GROUP_ID` | Botning asosiy guruhi (event uchun) |
| `BOT_CHANNEL_ID` | Botning kanali |
| `BOT_USERNAME` | Bot usernamei |

## 📋 Komandalar

### Guruh komandalari
- `/waifu [ism]` — paydo bo'lgan waifuni tutish
- `/collection` — kolleksiyangiz
- `/profil` — profil
- `/daily` — kunlik mukofot
- `/top` — reyting
- `/trade` — savdo
- `/gift` — sovg'a

### Admin komandalari
- `/panel` — to'liq admin panel
- `/admins` — adminlar ro'yxati
