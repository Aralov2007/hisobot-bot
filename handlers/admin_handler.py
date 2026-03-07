from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import AsyncSessionLocal
from database.crud import (
    get_all_reports, get_report_by_id, update_report_status, get_all_users,
    update_user_status, get_open_requests, resolve_request, log_activity,
    get_monthly_reports, get_material_stats, set_user_role, get_all_admins,
    get_user_by_telegram_id, create_material, get_all_materials
)
from database.models import (
    UserRole, UserStatus, ReportStatus, RequestStatus,
    AdminPermission, User
)
from keyboards.keyboards import (
    admin_reports_list_keyboard, admin_report_actions, users_list_keyboard,
    user_manage_keyboard, request_actions_keyboard, export_keyboard,
    admin_list_keyboard, admin_permissions_keyboard, admin_main_menu, super_admin_menu
)
from utils.formatters import format_report, format_materials_stats
from utils.export import export_to_excel, export_to_pdf
import logging

logger = logging.getLogger(__name__)
router = Router()


def is_admin(db_user):
    if not db_user:
        return False
    return db_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and db_user.status == UserStatus.ACTIVE


def is_super_admin(db_user):
    if not db_user:
        return False
    return db_user.role == UserRole.SUPER_ADMIN and db_user.status == UserStatus.ACTIVE


class AdminEditStates(StatesGroup):
    edit_work_type = State()
    edit_note = State()
    reject_reason = State()
    add_material_name = State()
    add_material_unit = State()
    add_material_cat = State()
    add_admin_id = State()


# ===== REPORTS =====

@router.message(F.text == "📋 Hisobotlar")
async def admin_reports(message: Message, db_user=None):
    if not is_admin(db_user):
        return

    async with AsyncSessionLocal() as session:
        reports = await get_all_reports(session, limit=50)

    if not reports:
        await message.answer("📭 Hozircha hisobotlar yo'q.")
        return

    await message.answer(
        f"📋 Hisobotlar ({len(reports)} ta):\n\nBitta hisobotni tanlang:",
        reply_markup=admin_reports_list_keyboard(reports)
    )


@router.callback_query(F.data.startswith("view_report:"))
async def view_report(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    report_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        report = await get_report_by_id(session, report_id)

    if not report:
        await callback.answer("❌ Hisobot topilmadi", show_alert=True)
        return

    text = format_report(report, show_user=True, detailed=True)
    await callback.message.edit_text(text, reply_markup=admin_report_actions(report_id))


@router.callback_query(F.data == "admin_report:list")
async def back_to_reports(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    async with AsyncSessionLocal() as session:
        reports = await get_all_reports(session, limit=50)

    await callback.message.edit_text(
        f"📋 Hisobotlar ({len(reports)} ta):",
        reply_markup=admin_reports_list_keyboard(reports)
    )


@router.callback_query(F.data.startswith("reports_page:"))
async def paginate_reports(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    page = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        reports = await get_all_reports(session, limit=50)

    await callback.message.edit_reply_markup(
        reply_markup=admin_reports_list_keyboard(reports, page=page)
    )


@router.callback_query(F.data.startswith("admin_report:approve:"))
async def approve_report(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    report_id = int(callback.data.split(":")[2])
    async with AsyncSessionLocal() as session:
        report = await get_report_by_id(session, report_id)
        await update_report_status(session, report_id, ReportStatus.APPROVED)
        await log_activity(session, db_user.id, "report_approved", {"report_id": report_id})

        # Notify user
        if report and report.user:
            try:
                await callback.bot.send_message(
                    report.user.telegram_id,
                    f"✅ Hisobotingiz tasdiqlandi!\n"
                    f"📅 {report.report_date.strftime('%d.%m.%Y')}\n"
                    f"📌 {report.work_type}"
                )
            except Exception as e:
                logger.error(f"Could not notify user: {e}")

    await callback.message.edit_text(
        f"✅ Hisobot #{report_id} tasdiqlandi!",
        reply_markup=None
    )


@router.callback_query(F.data.startswith("admin_report:reject:"))
async def reject_report_start(callback: CallbackQuery, state: FSMContext, db_user=None):
    if not is_admin(db_user):
        return

    report_id = int(callback.data.split(":")[2])
    await state.update_data(reject_report_id=report_id)
    await callback.message.edit_text("✍️ Rad etish sababini yozing:")
    await state.set_state(AdminEditStates.reject_reason)


@router.message(AdminEditStates.reject_reason)
async def process_reject_reason(message: Message, state: FSMContext, db_user=None):
    data = await state.get_data()
    report_id = data["reject_report_id"]
    reason = message.text.strip()

    async with AsyncSessionLocal() as session:
        report = await get_report_by_id(session, report_id)
        await update_report_status(session, report_id, ReportStatus.REJECTED, admin_comment=reason)
        await log_activity(session, db_user.id, "report_rejected", {"report_id": report_id, "reason": reason})

        if report and report.user:
            try:
                await message.bot.send_message(
                    report.user.telegram_id,
                    f"❌ Hisobotingiz rad etildi.\n"
                    f"📅 {report.report_date.strftime('%d.%m.%Y')}\n"
                    f"💬 Sabab: {reason}"
                )
            except:
                pass

    await state.clear()
    await message.answer(f"❌ Hisobot #{report_id} rad etildi.")


@router.callback_query(F.data.startswith("admin_report:edit:"))
async def edit_report_start(callback: CallbackQuery, state: FSMContext, db_user=None):
    if not is_admin(db_user):
        return

    report_id = int(callback.data.split(":")[2])
    await state.update_data(edit_report_id=report_id)
    await callback.message.edit_text(
        "✏️ Yangi ish turini kiriting (yoki /skip bosing):"
    )
    await state.set_state(AdminEditStates.edit_work_type)


@router.message(AdminEditStates.edit_work_type)
async def edit_work_type(message: Message, state: FSMContext):
    if message.text != "/skip":
        await state.update_data(new_work_type=message.text.strip())
    await message.answer("✏️ Yangi izoh kiriting (yoki /skip bosing):")
    await state.set_state(AdminEditStates.edit_note)


@router.message(AdminEditStates.edit_note)
async def edit_note(message: Message, state: FSMContext, db_user=None):
    data = await state.get_data()
    report_id = data["edit_report_id"]

    async with AsyncSessionLocal() as session:
        from sqlalchemy import update
        from database.models import Report
        values = {}
        if data.get("new_work_type"):
            values["work_type"] = data["new_work_type"]
        if message.text != "/skip":
            values["note"] = message.text.strip()
        if values:
            await session.execute(update(Report).where(Report.id == report_id).values(**values))
            await session.commit()
        await log_activity(session, db_user.id, "report_edited", {"report_id": report_id})

    await state.clear()
    await message.answer(f"✅ Hisobot #{report_id} tahrirlandi.")


# ===== USERS =====

@router.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(message: Message, db_user=None):
    if not is_admin(db_user):
        return

    async with AsyncSessionLocal() as session:
        users = await get_all_users(session)

    if not users:
        await message.answer("📭 Hech qanday foydalanuvchi yo'q.")
        return

    # Show pending first
    pending = [u for u in users if u.status == UserStatus.PENDING]
    active = [u for u in users if u.status == UserStatus.ACTIVE and u.role == UserRole.USER]

    text = f"👥 Jami: {len(users)} ta\n🟡 Kutmoqda: {len(pending)} ta\n🟢 Faol: {len(active)} ta\n\nTanlang:"
    await message.answer(text, reply_markup=users_list_keyboard(users[:20]))


@router.callback_query(F.data == "users:list")
async def back_to_users(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    async with AsyncSessionLocal() as session:
        users = await get_all_users(session)

    await callback.message.edit_text(
        f"👥 Foydalanuvchilar ({len(users)} ta):",
        reply_markup=users_list_keyboard(users[:20])
    )


@router.callback_query(F.data.startswith("view_user:"))
async def view_user(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    user_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    if not user:
        await callback.answer("Foydalanuvchi topilmadi", show_alert=True)
        return

    role_text = {"user": "Ishchi", "admin": "Admin", "super_admin": "Super Admin"}.get(user.role.value, user.role.value)
    status_text = {"active": "🟢 Faol", "pending": "🟡 Kutmoqda", "blocked": "🔴 Bloklangan"}.get(user.status.value, user.status.value)

    text = (
        f"👤 Foydalanuvchi ma'lumoti\n\n"
        f"📛 Ism: {user.full_name}\n"
        f"📱 Tel: {user.phone or 'yoq'}\n"
        f"🆔 Username: @{user.username or 'yoq'}\n"
        f"👔 Rol: {role_text}\n"
        f"📊 Status: {status_text}\n"
        f"📅 Ro'yxatdan: {user.created_at.strftime('%d.%m.%Y')}"
    )

    await callback.message.edit_text(text, reply_markup=user_manage_keyboard(user_id, user.status))


@router.callback_query(F.data.startswith("user_approve:"))
async def approve_user(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    user_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        await update_user_status(session, user_id, UserStatus.ACTIVE)
        await log_activity(session, db_user.id, "user_approved", {"user_id": user_id})

        if user:
            try:
                await callback.bot.send_message(
                    user.telegram_id,
                    "✅ Hisobingiz tasdiqlandi! Bot'dan foydalanishingiz mumkin.\n\n"
                    "/start bosing.",
                )
            except:
                pass

    await callback.message.edit_text(f"✅ Foydalanuvchi faollashtirildi!")


@router.callback_query(F.data.startswith("user_reject:"))
async def reject_user(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    user_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        await update_user_status(session, user_id, UserStatus.BLOCKED)
    await callback.message.edit_text("❌ Foydalanuvchi rad etildi.")


@router.callback_query(F.data.startswith("manage_user:"))
async def manage_user(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    parts = callback.data.split(":")
    action = parts[1]
    user_id = int(parts[2])

    async with AsyncSessionLocal() as session:
        if action == "activate":
            await update_user_status(session, user_id, UserStatus.ACTIVE)
            await callback.answer("✅ Faollashtirildi")
        elif action == "block":
            await update_user_status(session, user_id, UserStatus.BLOCKED)
            await callback.answer("🚫 Bloklandi")

    await callback.message.edit_text("✅ Amalga oshirildi.", reply_markup=None)


# ===== EDIT REQUESTS =====

@router.message(F.text == "📨 Arizalar")
async def admin_requests(message: Message, db_user=None):
    if not is_admin(db_user):
        return

    async with AsyncSessionLocal() as session:
        requests = await get_open_requests(session)

    if not requests:
        await message.answer("✅ Yangi arizalar yo'q.")
        return

    for req in requests[:10]:
        text = (
            f"📨 Ariza #{req.id}\n\n"
            f"👤 {req.user.full_name}\n"
            f"📄 Hisobot #{req.report_id}\n"
            f"💬 Sabab: {req.reason}\n"
            f"📅 {req.created_at.strftime('%d.%m.%Y %H:%M')}"
        )
        await message.answer(text, reply_markup=request_actions_keyboard(req.id, req.report_id))


@router.callback_query(F.data.startswith("req:resolve:"))
async def resolve_req(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    req_id = int(callback.data.split(":")[2])
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from database.models import EditRequest
        result = await session.execute(select(EditRequest).where(EditRequest.id == req_id))
        req = result.scalar_one_or_none()
        await resolve_request(session, req_id, "Admin tomonidan hal qilindi")
        await log_activity(session, db_user.id, "request_resolved", {"request_id": req_id})

        if req and req.user:
            try:
                await callback.bot.send_message(
                    req.user.telegram_id,
                    f"✅ Arizangiz #{req_id} hal qilindi!\nAdmin ko'rib chiqdi."
                )
            except:
                pass

    await callback.message.edit_text("✅ Ariza hal qilindi.", reply_markup=None)


@router.callback_query(F.data.startswith("req:close:"))
async def close_req(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    req_id = int(callback.data.split(":")[2])
    async with AsyncSessionLocal() as session:
        from sqlalchemy import update
        from database.models import EditRequest, RequestStatus
        await session.execute(
            update(EditRequest).where(EditRequest.id == req_id).values(status=RequestStatus.CLOSED)
        )
        await session.commit()

    await callback.message.edit_text("🗑 Ariza yopildi.", reply_markup=None)


# ===== STATISTICS & EXPORT =====

@router.message(F.text == "📊 Statistika")
async def admin_stats(message: Message, db_user=None):
    if not is_admin(db_user):
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Oylik hisobotlar", callback_data="admin_stats:monthly")
    builder.button(text="📦 Material statistikasi", callback_data="admin_stats:materials")
    builder.button(text="📥 Export qilish", callback_data="admin_stats:export")
    builder.adjust(2, 1)
    await message.answer("📊 Statistika:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("admin_stats:"))
async def handle_admin_stats(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    action = callback.data.split(":")[1]

    if action == "monthly":
        async with AsyncSessionLocal() as session:
            reports = await get_monthly_reports(session)
        text = f"🗓 Joriy oy hisobotlari: {len(reports)} ta\n\n"
        for r in reports[:15]:
            text += f"• {r.user.full_name[:15]} | {r.report_date.strftime('%d.%m')} | {r.work_type[:15]}\n"
        await callback.message.edit_text(text)

    elif action == "materials":
        async with AsyncSessionLocal() as session:
            stats = await get_material_stats(session)
        text = format_materials_stats(stats, title="📦 Oylik material statistikasi")
        await callback.message.edit_text(text)

    elif action == "export":
        await callback.message.edit_text(
            "📥 Eksport formatini tanlang:",
            reply_markup=export_keyboard()
        )


@router.callback_query(F.data.startswith("export:"))
async def handle_export(callback: CallbackQuery, db_user=None):
    if not is_admin(db_user):
        return

    format_type = callback.data.split(":")[1]
    await callback.answer("⏳ Tayyorlanmoqda...")

    async with AsyncSessionLocal() as session:
        reports = await get_monthly_reports(session)
        stats = await get_material_stats(session)

    if format_type == "excel":
        file_path = await export_to_excel(reports, stats)
        doc = FSInputFile(file_path)
        await callback.message.answer_document(doc, caption="📊 Oylik hisobot (Excel)")

    elif format_type == "pdf":
        file_path = await export_to_pdf(reports, stats)
        doc = FSInputFile(file_path)
        await callback.message.answer_document(doc, caption="📄 Oylik hisobot (PDF)")


# ===== MATERIALS CATALOG =====

@router.message(F.text == "🗂 Materiallar")
async def admin_materials(message: Message, db_user=None):
    if not is_admin(db_user):
        return

    async with AsyncSessionLocal() as session:
        materials = await get_all_materials(session)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yangi material qo'shish", callback_data="material:add")
    builder.adjust(1)

    # Group by category
    categories = {}
    for m in materials:
        cat = m.category or "Boshqa"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(m)

    text = f"🗂 Materiallar katalogi ({len(materials)} ta):\n\n"
    for cat, mats in categories.items():
        text += f"📁 {cat}:\n"
        for m in mats[:5]:
            text += f"  • {m.name} ({m.unit})\n"
        if len(mats) > 5:
            text += f"  ... va yana {len(mats)-5} ta\n"
        text += "\n"

    await message.answer(text[:3000], reply_markup=builder.as_markup())


@router.callback_query(F.data == "material:add")
async def add_material_start(callback: CallbackQuery, state: FSMContext, db_user=None):
    if not is_admin(db_user):
        return
    await callback.message.edit_text("✍️ Yangi material nomini kiriting:")
    await state.set_state(AdminEditStates.add_material_name)


@router.message(AdminEditStates.add_material_name)
async def add_material_name(message: Message, state: FSMContext):
    await state.update_data(mat_name=message.text.strip())
    await message.answer("📏 Birligini kiriting (dona, metr, kg, litr va h.k.):")
    await state.set_state(AdminEditStates.add_material_unit)


@router.message(AdminEditStates.add_material_unit)
async def add_material_unit(message: Message, state: FSMContext):
    await state.update_data(mat_unit=message.text.strip())
    await message.answer("📁 Kategoriyasini kiriting (yoki /skip):")
    await state.set_state(AdminEditStates.add_material_cat)


@router.message(AdminEditStates.add_material_cat)
async def add_material_cat(message: Message, state: FSMContext):
    data = await state.get_data()
    cat = "Boshqa" if message.text == "/skip" else message.text.strip()

    async with AsyncSessionLocal() as session:
        mat = await create_material(session, data["mat_name"], data["mat_unit"], cat)

    await state.clear()
    await message.answer(f"✅ Material qo'shildi: {mat.name} ({mat.unit})")


# ===== ADMIN MANAGEMENT (SUPER ADMIN ONLY) =====

@router.message(F.text == "👑 Adminlar")
async def admin_management(message: Message, db_user=None):
    if not is_super_admin(db_user):
        await message.answer("⛔ Faqat Super Admin uchun.")
        return

    async with AsyncSessionLocal() as session:
        admins = await get_all_admins(session)

    await message.answer(
        f"👑 Adminlar boshqaruvi ({len(admins)} ta):",
        reply_markup=admin_list_keyboard(admins)
    )


@router.callback_query(F.data == "admins:list")
async def back_to_admins(callback: CallbackQuery, db_user=None):
    if not is_super_admin(db_user):
        return

    async with AsyncSessionLocal() as session:
        admins = await get_all_admins(session)

    await callback.message.edit_text(
        f"👑 Adminlar ({len(admins)} ta):",
        reply_markup=admin_list_keyboard(admins)
    )


@router.callback_query(F.data.startswith("admin_manage:"))
async def manage_admin(callback: CallbackQuery, db_user=None):
    if not is_super_admin(db_user):
        return

    admin_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == admin_id))
        admin = result.scalar_one_or_none()

    if not admin:
        await callback.answer("Topilmadi", show_alert=True)
        return

    perm = admin.admin_permission.value if admin.admin_permission else "yo'q"
    text = (
        f"🛠 Admin: {admin.full_name}\n"
        f"📊 Rol: {admin.role.value}\n"
        f"🔐 Huquq: {perm}\n"
        f"📱 Tel: {admin.phone or 'yoq'}"
    )
    await callback.message.edit_text(text, reply_markup=admin_permissions_keyboard(admin_id))


@router.callback_query(F.data.startswith("set_admin_perm:"))
async def set_admin_perm(callback: CallbackQuery, db_user=None):
    if not is_super_admin(db_user):
        return

    parts = callback.data.split(":")
    user_id = int(parts[1])
    perm_str = parts[2]

    perm = AdminPermission.FULL if perm_str == "full" else AdminPermission.LIMITED

    async with AsyncSessionLocal() as session:
        await set_user_role(session, user_id, UserRole.ADMIN, permission=perm)
        await log_activity(session, db_user.id, "admin_permission_set",
                          {"target_user_id": user_id, "permission": perm_str})

    await callback.answer(f"✅ Huquq o'rnatildi: {perm_str}")
    await callback.message.edit_text("✅ Admin huquqlari yangilandi.", reply_markup=None)


@router.callback_query(F.data.startswith("remove_admin:"))
async def remove_admin(callback: CallbackQuery, db_user=None):
    if not is_super_admin(db_user):
        return

    user_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        await set_user_role(session, user_id, UserRole.USER, permission=None)
        await log_activity(session, db_user.id, "admin_removed", {"target_user_id": user_id})

    await callback.answer("✅ Admin huquqlari olib tashlandi")
    await callback.message.edit_text("✅ Adminlikdan olib tashlandi.", reply_markup=None)


@router.callback_query(F.data == "admin_add:new")
async def add_admin_start(callback: CallbackQuery, state: FSMContext, db_user=None):
    if not is_super_admin(db_user):
        return

    await callback.message.edit_text(
        "📱 Yangi adminning Telegram ID raqamini yuboring\n"
        "(Foydalanuvchi avval bot'dan ro'yxatdan o'tgan bo'lishi kerak):"
    )
    await state.set_state(AdminEditStates.add_admin_id)


@router.message(AdminEditStates.add_admin_id)
async def process_add_admin_id(message: Message, state: FSMContext, db_user=None):
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID. Faqat raqam kiriting.")
        return

    async with AsyncSessionLocal() as session:
        target_user = await get_user_by_telegram_id(session, telegram_id)
        if not target_user:
            await message.answer("❌ Bu ID'li foydalanuvchi topilmadi. Avval ro'yxatdan o'tishi kerak.")
            await state.clear()
            return

        await set_user_role(session, target_user.id, UserRole.ADMIN, AdminPermission.FULL)
        await log_activity(session, db_user.id, "admin_added", {"target_telegram_id": telegram_id})

        try:
            await message.bot.send_message(
                telegram_id,
                "🛠 Siz admin qilib tayinlandingiz!\n/start bosing.",
            )
        except:
            pass

    await state.clear()
    await message.answer(f"✅ {target_user.full_name} admin qilib tayinlandi!")
