from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database.models import UserRole, UserStatus
from keyboards.keyboards import user_main_menu, admin_main_menu, super_admin_menu

router = Router()


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Ma'lumot")
async def help_handler(message: Message, db_user=None):
    if not db_user or db_user.status != UserStatus.ACTIVE:
        await message.answer(
            "ℹ️ Qurilish va elektr montaj hisobot boti\n\n"
            "Ro'yxatdan o'tish uchun /start bosing."
        )
        return

    if db_user.role == UserRole.USER:
        text = (
            "ℹ️ Bot haqida ma'lumot\n\n"
            "📝 Hisobot yuborish — kunlik ish hisoboti\n"
            "📊 Statistika — o'z faoliyatingizni ko'ring\n"
            "📋 Arizalar — xatolikni tuzatish so'rovi\n\n"
            "⚠️ Kuniga faqat 1 ta hisobot yuboriladi\n"
            "⚠️ Hisobotni o'zgartirib bo'lmaydi (faqat admin)"
        )
    else:
        text = (
            "ℹ️ Admin panel ma'lumoti\n\n"
            "📋 Hisobotlar — barcha xodimlar hisobotlari\n"
            "📨 Arizalar — xodimlardan kelgan so'rovlar\n"
            "👥 Foydalanuvchilar — xodimlarni boshqarish\n"
            "📊 Statistika — umumiy ko'rsatkichlar\n"
            "🗂 Materiallar — materiallar katalogi\n"
            "👑 Adminlar — admin boshqaruvi (Super Admin)"
        )

    await message.answer(text)


@router.message(Command("menu"))
async def menu_handler(message: Message, db_user=None):
    if not db_user or db_user.status != UserStatus.ACTIVE:
        return

    if db_user.role == UserRole.SUPER_ADMIN:
        await message.answer("👑 Super Admin menyu:", reply_markup=super_admin_menu())
    elif db_user.role == UserRole.ADMIN:
        await message.answer("🛠 Admin menyu:", reply_markup=admin_main_menu())
    else:
        await message.answer("👋 Asosiy menyu:", reply_markup=user_main_menu())


@router.message(F.text == "⚙️ Admin boshqaruv")
async def admin_settings(message: Message, db_user=None):
    """Redirect to admin panel info"""
    from database.models import UserRole, UserStatus
    if not db_user or db_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        return
    await message.answer(
        "⚙️ Admin boshqaruv\n\n"
        "Quyidagi bo'limlar mavjud:\n"
        "• 📋 Hisobotlar — xodimlar hisobotlari\n"
        "• 📨 Arizalar — xodimlar so'rovlari\n"
        "• 👥 Foydalanuvchilar — xodimlarni boshqarish\n"
        "• 📊 Statistika va export\n"
        "• 🗂 Materiallar katalogi"
    )
