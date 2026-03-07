from aiogram import Router, F
from aiogram.types import Message, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
from database.db import AsyncSessionLocal
from database.crud import get_user_by_telegram_id, create_user, get_all_admins, log_activity
from database.models import UserRole, UserStatus
from keyboards.keyboards import contact_keyboard, user_main_menu, admin_main_menu, super_admin_menu
from config import SUPER_ADMIN_IDS
import logging

logger = logging.getLogger(__name__)
router = Router()


class RegisterStates(StatesGroup):
    waiting_name = State()
    waiting_phone = State()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, db_user=None):
    await state.clear()

    if db_user:
        if db_user.status == UserStatus.PENDING:
            await message.answer(
                "⏳ Sizning so'rovingiz admin tomonidan ko'rib chiqilmoqda.\n"
                "Iltimos, kuting. Tasdiqlangach xabar olasiz."
            )
            return
        elif db_user.status == UserStatus.BLOCKED:
            await message.answer("🚫 Sizning hisobingiz bloklangan. Admin bilan bog'laning.")
            return

        # Show appropriate menu
        if db_user.role == UserRole.SUPER_ADMIN:
            await message.answer(
                f"👑 Xush kelibsiz, {db_user.full_name}!\nSuper Admin paneli:",
                reply_markup=super_admin_menu()
            )
        elif db_user.role == UserRole.ADMIN:
            await message.answer(
                f"🛠 Xush kelibsiz, {db_user.full_name}!\nAdmin paneli:",
                reply_markup=admin_main_menu()
            )
        else:
            await message.answer(
                f"👋 Xush kelibsiz, {db_user.full_name}!\nAsosiy menyu:",
                reply_markup=user_main_menu()
            )
        return

    # Check if super admin
    if message.from_user.id in SUPER_ADMIN_IDS:
        async with AsyncSessionLocal() as session:
            user = await create_user(
                session,
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name or "Super Admin",
                username=message.from_user.username
            )
            from sqlalchemy import update
            from database.models import User
            await session.execute(
                update(User).where(User.id == user.id).values(
                    role=UserRole.SUPER_ADMIN,
                    status=UserStatus.ACTIVE
                )
            )
            await session.commit()
        await message.answer(
            "👑 Super Admin sifatida tizimga kirdingiz!",
            reply_markup=super_admin_menu()
        )
        return

    # New user registration
    await message.answer(
        "👋 Qurilish Bot'ga xush kelibsiz!\n\n"
        "📋 Ro'yxatdan o'tish uchun to'liq ismingizni kiriting:\n"
        "(Masalan: Aliyev Jasur Baxtiyorovich)"
    )
    await state.set_state(RegisterStates.waiting_name)


@router.message(RegisterStates.waiting_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 5:
        await message.answer("❌ Ism kamida 5 ta belgi bo'lishi kerak. Qayta kiriting:")
        return

    await state.update_data(full_name=name)
    await message.answer(
        f"✅ Ismingiz: {name}\n\n"
        "📱 Endi telefon raqamingizni yuboring:",
        reply_markup=contact_keyboard()
    )
    await state.set_state(RegisterStates.waiting_phone)


@router.message(RegisterStates.waiting_phone, F.content_type == ContentType.CONTACT)
async def process_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = message.contact.phone_number

    async with AsyncSessionLocal() as session:
        user = await create_user(
            session,
            telegram_id=message.from_user.id,
            full_name=data["full_name"],
            phone=phone,
            username=message.from_user.username
        )
        await log_activity(session, user.id, "user_registered", {"phone": phone})

        # Notify all admins
        admins = await get_all_admins(session)
        from aiogram import Bot
        from config import BOT_TOKEN
        bot = Bot(token=BOT_TOKEN)

        from keyboards.keyboards import pending_user_keyboard
        for admin in admins:
            try:
                await bot.send_message(
                    admin.telegram_id,
                    f"🆕 Yangi foydalanuvchi ro'yxatdan o'tdi!\n\n"
                    f"👤 Ism: {user.full_name}\n"
                    f"📱 Tel: {phone}\n"
                    f"🆔 Username: @{message.from_user.username or 'yoq'}\n\n"
                    "Tasdiqlaysizmi?",
                    reply_markup=pending_user_keyboard(user.id)
                )
            except Exception as e:
                logger.error(f"Could not notify admin {admin.telegram_id}: {e}")
        await bot.session.close()

    await state.clear()
    from keyboards.keyboards import remove_keyboard
    await message.answer(
        "✅ Ro'yxatdan o'tdingiz!\n\n"
        "⏳ Admin tasdiqlaguncha kuting. Tasdiqlangach xabar olasiz.",
        reply_markup=remove_keyboard()
    )


@router.message(RegisterStates.waiting_phone)
async def process_phone_text(message: Message):
    await message.answer(
        "❌ Iltimos, tugmani bosib telefon raqamingizni yuboring.",
        reply_markup=contact_keyboard()
    )
