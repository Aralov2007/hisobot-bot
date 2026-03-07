# 🏗️ Qurilish va Elektr Montaj Hisobot Boti

Qurilish va elektr montaj sohasida ishlovchi xodimlar uchun kunlik materiallar hisobini yuritish Telegram boti.

---

## 📁 Loyiha tuzilmasi

```
construction_bot/
├── bot.py                    # Asosiy ishga tushirish fayli
├── config.py                 # Sozlamalar
├── requirements.txt          # Python kutubxonalar
├── Dockerfile                # Docker image
├── docker-compose.yml        # Docker Compose
├── .env.example              # .env namunasi
│
├── database/
│   ├── models.py             # SQLAlchemy modellari
│   ├── db.py                 # Ma'lumotlar bazasi ulanish
│   └── crud.py               # CRUD operatsiyalar
│
├── handlers/
│   ├── auth_handler.py       # Ro'yxatdan o'tish
│   ├── user_handler.py       # Xodim funksiyalari
│   ├── admin_handler.py      # Admin funksiyalari
│   └── common_handler.py     # Umumiy komandalar
│
├── keyboards/
│   └── keyboards.py          # Barcha klaviaturalar
│
├── middlewares/
│   └── auth_middleware.py    # Autentifikatsiya middleware
│
└── utils/
    ├── formatters.py         # Matn formatlash
    ├── export.py             # Excel/PDF export
    └── scheduler.py          # Kunlik eslatmalar
```

---

## ⚙️ O'rnatish va ishga tushirish

### 1. Talablar
- Python 3.11+
- PostgreSQL 15+
- Redis 7+ (ixtiyoriy)

### 2. Telegram Bot yaratish
1. [@BotFather](https://t.me/BotFather) ga boring
2. `/newbot` komandasi yuboring
3. Bot nomini va username'ni kiriting
4. Olingan **TOKEN** ni `.env` fayliga saqlang

### 3. O'rnatish

```bash
# Loyihani klonlash
git clone <repo_url>
cd construction_bot

# Virtual muhit
python -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate  # Windows

# Kutubxonalar o'rnatish
pip install -r requirements.txt

# .env faylini sozlash
cp .env.example .env
nano .env  # BOT_TOKEN va boshqalarni to'ldiring
```

### 4. Ma'lumotlar bazasini sozlash

```bash
# PostgreSQL da baza yaratish
psql -U postgres
CREATE DATABASE construction_bot;
CREATE USER botuser WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE construction_bot TO botuser;
\q
```

### 5. Ishga tushirish

```bash
python bot.py
```

### 6. Docker bilan ishga tushirish

```bash
cp .env.example .env
# .env faylida BOT_TOKEN va SUPER_ADMIN_IDS ni to'ldiring

docker-compose up -d
```

---

## 👥 Foydalanuvchi rollari

### 👷 Xodim (USER)
- Kunlik hisobot yuborish
- O'z statistikasini ko'rish
- Xatolik bo'lsa ariza yuborish

### 🛠️ Admin
- Barcha hisobotlarni ko'rish va boshqarish
- Xodimlarni tasdiqlash/bloklash
- Arizalarni ko'rib chiqish
- Statistika va export (Excel/PDF)
- Materiallar katalogini boshqarish

### 👑 Super Admin
- Admin funksiyalarining barchasi
- Boshqa adminlarni qo'shish/o'chirish
- Admin huquqlarini belgilash

---

## 🔄 Ish jarayoni

```
Yangi foydalanuvchi
    ↓
/start → Ism kiriting → Tel raqam
    ↓
Admin tasdiqlaydi → Xodim faollashadi
    ↓
Hisobot yuborish:
  Ish turi → Materiallar → Izoh → Rasm → Tasdiqlash
    ↓
Admin ko'radi → Tasdiqlaydi / Rad etadi
    ↓
Xodimga xabar ketadi
```

---

## 📊 Ma'lumotlar bazasi

| Jadval | Tavsif |
|--------|--------|
| `users` | Foydalanuvchilar |
| `reports` | Kunlik hisobotlar |
| `report_materials` | Hisobotdagi materiallar |
| `materials` | Materiallar katalogi |
| `edit_requests` | Tahrirlash arizalari |
| `activity_logs` | Faoliyat loglari |

---

## 📥 Export formatlari

- **Excel (.xlsx)**: 2 varaq — hisobotlar va material statistikasi
- **PDF**: Formatlangan jadvallar bilan oylik hisobot

---

## ⏰ Kunlik eslatma

Har kuni `REMINDER_TIME` (standart: 17:00) da hisobot yubormaganlar xabardor qilinadi.

---

## 🔒 Xavfsizlik

- Har bir xodim faqat o'z ma'lumotlarini ko'radi
- Admin tasdiqlamasdan xodim faol emas
- Barcha amallar `activity_logs` da saqlanadi
- Super Admin iyerarxiyasi

---

## 📞 Muammo bo'lsa

1. `bot.log` faylini tekshiring
2. `.env` sozlamalarini tekshiring
3. Ma'lumotlar bazasi ulanishini tekshiring
