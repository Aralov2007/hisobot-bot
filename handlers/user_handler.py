from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import AsyncSessionLocal
from database.crud import (
    has_report_today, create_report, add_report_material,
    get_all_materials, get_reports_by_user, get_weekly_reports,
    get_monthly_reports, get_material_stats, log_activity,
    create_edit_request, get_material_by_id, get_all_admins
)
from database.models import UserStatus, UserRole
from keyboards.keyboards import (
    work_type_keyboard, materials_page_keyboard, quantity_confirm_keyboard,
    report_confirm_keyboard, photo_skip_keyboard, user_main_menu, stats_keyboard
)
from utils.formatters import format_report, format_materials_stats
import os, logging
from config import MEDIA_DIR

logger = logging.getLogger(__name__)
router = Router()

os.makedirs(MEDIA_DIR, exist_ok=True)


class ReportStates(StatesGroup):
    work_type = State()
    work_type_custom = State()
    materials = State()
    material_quantity = State()
    note = State()
    photo = State()
    confirm = State()


class EditRequestStates(StatesGroup):
    select_report = State()
    write_reason = State()


def check_active_user(db_user):
    if not db_user:
        return False
    return db_user.status == UserStatus.ACTIVE and db_user.role == UserRole.USER


# ===== REPORT SUBMISSION =====

@router.message(F.text == "📝 Hisobot yuborish")
async def start_report(message: Message, state: FSMContext, db_user=None):
    if not check_active_user(db_user):
        await message.answer("❌ Sizda bu imkoniyat yo'q.")
        return

    async with AsyncSessionLocal() as session:
        if await has_report_today(session, db_user.id):
            await message.answer(
                "⚠️ Siz bugun allaqachon hisobot yuborgansiz!\n"
                "Har kuni faqat 1 ta hisobot yuboriladi.\n\n"
                "Agar xatolik bo'lsa, 📋 Arizalar bo'limiga murojaat qiling."
            )
            return

    await state.clear()
    await message.answer(
        "📝 Bugungi hisobot\n\n"
        "Ish turini tanlang:",
        reply_markup=work_type_keyboard()
    )
    await state.set_state(ReportStates.work_type)
    await state.update_data(materials=[])


@router.callback_query(ReportStates.work_type, F.data.startswith("work_type:"))
async def process_work_type(callback: CallbackQuery, state: FSMContext):
    work_type = callback.data.split(":", 1)[1]

    if work_type == "custom":
        await callback.message.edit_text("✍️ Ish turini yozing:")
        await state.set_state(ReportStates.work_type_custom)
        return

    await state.update_data(work_type=work_type)
    await show_materials_menu(callback.message, state, edit=True)


@router.message(ReportStates.work_type_custom)
async def process_work_type_custom(message: Message, state: FSMContext):
    if len(message.text.strip()) < 3:
        await message.answer("❌ Ish turi kamida 3 ta belgi bo'lishi kerak.")
        return
    await state.update_data(work_type=message.text.strip())
    await show_materials_menu(message, state)


async def show_materials_menu(message: Message, state: FSMContext, edit=False):
    data = await state.get_data()
    materials_list = data.get("materials", [])

    async with AsyncSessionLocal() as session:
        materials = await get_all_materials(session)

    added_text = ""
    if materials_list:
        added_text = "\n\n✅ Qo'shilgan materiallar:\n"
        for m in materials_list:
            added_text += f"  • {m['name']}: {m['quantity']} {m['unit']}\n"

    text = f"📦 Materiallar tanlang:{added_text}\n\nBarcha materiallarni qo'shib bo'lgach, '✅ Tayyor' tugmasini bosing."

    kb = materials_page_keyboard(materials, page=data.get("mat_page", 0))

    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

    await state.set_state(ReportStates.materials)


@router.callback_query(ReportStates.materials, F.data.startswith("mat_page:"))
async def paginate_materials(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    await state.update_data(mat_page=page)
    await show_materials_menu(callback.message, state, edit=True)


@router.callback_query(ReportStates.materials, F.data.startswith("mat_select:"))
async def select_material(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    mat_id = int(parts[1])
    unit = parts[2]

    async with AsyncSessionLocal() as session:
        mat = await get_material_by_id(session, mat_id)

    await state.update_data(current_mat_id=mat_id, current_mat_name=mat.name, current_mat_unit=unit)
    await callback.message.edit_text(
        f"📦 Material: {mat.name}\n\nMiqdorni tanlang yoki kiriting:",
        reply_markup=quantity_confirm_keyboard(mat.name, unit)
    )
    await state.set_state(ReportStates.material_quantity)


@router.callback_query(ReportStates.materials, F.data == "mat_custom")
async def custom_material(callback: CallbackQuery, state: FSMContext):
    await state.update_data(current_mat_id=None, current_mat_name=None)
    await callback.message.edit_text(
        "✍️ Material nomini kiriting (masalan: Bolt M8 - 15 dona):"
    )
    await state.set_state(ReportStates.material_quantity)


@router.callback_query(ReportStates.material_quantity, F.data.startswith("qty:"))
async def process_qty_callback(callback: CallbackQuery, state: FSMContext):
    qty_str = callback.data.split(":")[1]

    if qty_str == "custom":
        await callback.message.edit_text("✍️ Miqdorni kiriting (raqam):")
        return

    qty = float(qty_str)
    await finalize_material(callback.message, state, qty, edit=True)


@router.message(ReportStates.material_quantity)
async def process_qty_text(message: Message, state: FSMContext):
    data = await state.get_data()
    text = message.text.strip()

    # Custom material format: "Material nomi - miqdor birlik"
    if data.get("current_mat_name") is None:
        # Parse custom material
        parts = text.rsplit(" - ", 1) if " - " in text else [text, "1"]
        mat_name = parts[0].strip()
        qty_part = parts[1].strip() if len(parts) > 1 else "1"
        qty_words = qty_part.split()
        try:
            qty = float(qty_words[0])
        except ValueError:
            qty = 1.0
        unit = qty_words[1] if len(qty_words) > 1 else "dona"

        await state.update_data(current_mat_name=mat_name, current_mat_unit=unit)
        await finalize_material(message, state, qty)
        return

    try:
        qty = float(text.replace(",", "."))
        if qty <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri miqdor. Raqam kiriting:")
        return

    await finalize_material(message, state, qty)


async def finalize_material(message, state, qty, edit=False):
    data = await state.get_data()
    materials = data.get("materials", [])

    mat_entry = {
        "mat_id": data.get("current_mat_id"),
        "name": data.get("current_mat_name", "Noma'lum"),
        "quantity": qty,
        "unit": data.get("current_mat_unit", "dona")
    }
    materials.append(mat_entry)
    await state.update_data(materials=materials, current_mat_id=None, current_mat_name=None)
    await show_materials_menu(message, state, edit=edit)


@router.callback_query(ReportStates.materials, F.data == "mat_done")
async def materials_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("materials"):
        await callback.answer("⚠️ Kamida 1 ta material qo'shing!", show_alert=True)
        return

    await callback.message.edit_text(
        "💬 Qo'shimcha izoh yozasizmi? (ixtiyoriy)\n\n"
        "Yozmasangiz, /skip yozing yoki 'O'tkazish' tugmasini bosing."
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="⏩ O'tkazish", callback_data="note:skip")
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await state.set_state(ReportStates.note)


@router.callback_query(ReportStates.note, F.data == "note:skip")
async def skip_note(callback: CallbackQuery, state: FSMContext):
    await state.update_data(note=None)
    await ask_photo(callback.message, state, edit=True)


@router.message(ReportStates.note)
async def process_note(message: Message, state: FSMContext):
    if message.text == "/skip":
        await state.update_data(note=None)
    else:
        await state.update_data(note=message.text.strip())
    await ask_photo(message, state)


async def ask_photo(message, state, edit=False):
    text = "📸 Ish jarayonidan rasm yuklang (ixtiyoriy):"
    kb = photo_skip_keyboard()
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)
    await state.set_state(ReportStates.photo)


@router.callback_query(ReportStates.photo, F.data == "photo:skip")
async def skip_photo(callback: CallbackQuery, state: FSMContext):
    await state.update_data(photo_path=None)
    await show_confirm(callback.message, state, edit=True)


@router.message(ReportStates.photo, F.content_type == ContentType.PHOTO)
async def process_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file_path = f"{MEDIA_DIR}/{message.from_user.id}_{photo.file_id}.jpg"
    await message.bot.download(photo, destination=file_path)
    await state.update_data(photo_path=file_path)
    await show_confirm(message, state)


@router.message(ReportStates.photo)
async def photo_wrong(message: Message):
    await message.answer("❌ Rasm yuboring yoki '⏩ O'tkazish' tugmasini bosing.")


async def show_confirm(message, state, edit=False):
    data = await state.get_data()
    text = "📋 Hisobot tasdiqlash\n\n"
    text += f"📌 Ish turi: {data['work_type']}\n"
    text += f"📦 Materiallar:\n"
    for m in data["materials"]:
        text += f"  • {m['name']}: {m['quantity']} {m['unit']}\n"
    if data.get("note"):
        text += f"💬 Izoh: {data['note']}\n"
    if data.get("photo_path"):
        text += "📸 Rasm: ✅\n"
    text += "\nYuborilamizmi?"

    kb = report_confirm_keyboard()
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)
    await state.set_state(ReportStates.confirm)


@router.callback_query(ReportStates.confirm, F.data == "report:confirm")
async def confirm_report(callback: CallbackQuery, state: FSMContext, db_user=None):
    data = await state.get_data()

    async with AsyncSessionLocal() as session:
        report = await create_report(
            session,
            user_id=db_user.id,
            work_type=data["work_type"],
            note=data.get("note"),
            photo_path=None
        )

        for m in data["materials"]:
            await add_report_material(
                session,
                report_id=report.id,
                material_id=m.get("mat_id"),
                custom_name=m["name"] if not m.get("mat_id") else None,
                quantity=m["quantity"],
                unit=m["unit"]
            )

        await session.commit()
        await log_activity(session, db_user.id, "report_submitted", {"report_id": report.id})

        # Notify admins
# Notify admins (rasm bilan)
        admins = await get_all_admins(session)
        from config import BOT_TOKEN
        from aiogram import Bot
        from aiogram.types import FSInputFile

        bot = Bot(token=BOT_TOKEN)

        caption = (
            f"📝 Yangi hisobot!\n\n"
            f"👤 {db_user.full_name}\n"
            f"📌 {data['work_type']}\n"
            f"📅 Bugun\n"
            f"📦 {len(data['materials'])} ta material"
)

        for admin in admins:
            try:
                if data.get("photo_path"):
                    photo = FSInputFile(data["photo_path"])
                    await bot.send_photo(
                        chat_id=admin.telegram_id,
                        photo=photo,
                        caption=caption
                    )
                else:
                    await bot.send_message(
                        chat_id=admin.telegram_id,
                        text=caption
                    )
            except Exception as e:
                print(f"Adminga yuborishda xato: {e}")

        await bot.session.close()


@router.callback_query(ReportStates.confirm, F.data == "report:cancel")
async def cancel_report(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Hisobot bekor qilindi.")


# ===== STATISTICS =====

@router.message(F.text == "📊 Mening statistikam")
async def user_stats(message: Message, db_user=None):
    if not check_active_user(db_user):
        return
    await message.answer("📊 Statistika bo'limi:", reply_markup=stats_keyboard())


@router.callback_query(F.data.startswith("stats:"))
async def handle_stats(callback: CallbackQuery, db_user=None):
    action = callback.data.split(":")[1]

    if action == "back":
        await callback.message.edit_text("📊 Statistika bo'limi:", reply_markup=stats_keyboard())
        return

    async with AsyncSessionLocal() as session:
        if action == "recent":
            reports = await get_reports_by_user(session, db_user.id, limit=5)
            if not reports:
                await callback.message.edit_text("📭 Hali hisobot yuborilmagan.", reply_markup=stats_keyboard())
                return
            text = "📋 Oxirgi 5 ta hisobot:\n\n"
            for r in reports:
                text += format_report(r) + "\n" + "─" * 30 + "\n"

        elif action == "weekly":
            reports = await get_weekly_reports(session, db_user.id)
            if not reports:
                await callback.message.edit_text("📭 Bu hafta hisobot yo'q.", reply_markup=stats_keyboard())
                return
            text = f"📆 Haftalik hisobotlar ({len(reports)} ta):\n\n"
            for r in reports:
                text += format_report(r) + "\n" + "─" * 30 + "\n"

        elif action == "monthly":
            reports = await get_monthly_reports(session, user_id=db_user.id)
            if not reports:
                await callback.message.edit_text("📭 Bu oy hisobot yo'q.", reply_markup=stats_keyboard())
                return
            text = f"🗓 Oylik hisobotlar ({len(reports)} ta):\n\n"
            for r in reports:
                text += format_report(r) + "\n" + "─" * 30 + "\n"

        elif action == "materials":
            stats = await get_material_stats(session, user_id=db_user.id)
            text = format_materials_stats(stats)

    # Split long messages
    if len(text) > 4000:
        text = text[:4000] + "\n...(qisqartirildi)"
    await callback.message.edit_text(text, reply_markup=stats_keyboard())


# ===== EDIT REQUESTS =====

@router.message(F.text == "📋 Arizalar")
async def my_requests(message: Message, state: FSMContext, db_user=None):
    if not check_active_user(db_user):
        return

    async with AsyncSessionLocal() as session:
        reports = await get_reports_by_user(session, db_user.id, limit=10)

    if not reports:
        await message.answer("📭 Sizda hali hisobot yo'q.")
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for r in reports:
        date_str = r.report_date.strftime("%d.%m.%Y")
        builder.button(
            text=f"📄 {date_str} - {r.work_type[:20]}",
            callback_data=f"req_report:{r.id}"
        )
    builder.adjust(1)

    await message.answer(
        "📋 Qaysi hisobotda xatolik bor?\nTanlang:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(EditRequestStates.select_report)


@router.callback_query(EditRequestStates.select_report, F.data.startswith("req_report:"))
async def select_report_for_request(callback: CallbackQuery, state: FSMContext):
    report_id = int(callback.data.split(":")[1])
    await state.update_data(req_report_id=report_id)
    await callback.message.edit_text(
        "✍️ Xatolik sababini yozing.\nAdmin ko'rib chiqadi va tuzatadi:"
    )
    await state.set_state(EditRequestStates.write_reason)


@router.message(EditRequestStates.write_reason)
async def submit_edit_request(message: Message, state: FSMContext, db_user=None):
    data = await state.get_data()
    reason = message.text.strip()

    if len(reason) < 10:
        await message.answer("❌ Sabab kamida 10 ta belgi bo'lishi kerak.")
        return

    async with AsyncSessionLocal() as session:
        req = await create_edit_request(session, db_user.id, data["req_report_id"], reason)
        await log_activity(session, db_user.id, "edit_request_created", {"request_id": req.id})

        admins = await get_all_admins(session)
        from config import BOT_TOKEN
        from aiogram import Bot
        bot = Bot(token=BOT_TOKEN)
        for admin in admins:
            try:
                await bot.send_message(
                    admin.telegram_id,
                    f"📨 Yangi ariza!\n\n"
                    f"👤 {db_user.full_name}\n"
                    f"📄 Hisobot #{data['req_report_id']}\n"
                    f"💬 {reason}"
                )
            except:
                pass
        await bot.session.close()

    await state.clear()
    await message.answer(
        "✅ Arizangiz adminga yuborildi!\n"
        "Admin ko'rib chiqgach xabar olasiz."
    )
